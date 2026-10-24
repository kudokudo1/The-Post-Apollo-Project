#!/usr/bin/env python3
"""M10p disposable writer-admission authority fixture; NOT a production service.

Requires an explicitly supplied private directory and a file literally named
'handoff-test.db'. Provides an OS-level flock plus durable SQLite fencing state,
but DOES NOT open, modify, freeze or authorize the real ApolloHubTodoStore.
There is no CLI, default path, network operation, or SQLite TASKS writer.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
import uuid


class AdmissionError(RuntimeError):
    pass


def _id(value):
    return (type(value) is str and
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,95}", value) is not None)


def _private_directory(path):
    if not isinstance(path, Path) or not path.is_absolute() or path.name != "handoff-test.db":
        raise AdmissionError("EXPLICIT_TEST_DB_REQUIRED")
    parent = path.parent
    info = parent.lstat()
    if (not stat.S_ISDIR(info.st_mode) or parent.is_symlink()
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise AdmissionError("UNSAFE_TEST_DIRECTORY")
    return parent


def _safe_regular(path):
    meta = path.lstat()
    if (not stat.S_ISREG(meta.st_mode) or path.is_symlink()
            or meta.st_uid != os.geteuid()
            or stat.S_IMODE(meta.st_mode) & 0o077):
        raise AdmissionError("UNSAFE_TEST_FILE")


def _exclusive_file(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    os.close(fd)


class Authority:
    """One process owns the test fixture while holding an exclusive flock.

    A new Authority after a process exit ALWAYS persists RECOVERY_REVIEW
    before permitting any action; it never automatically re-enables JSON.
    Even in JSON_ACTIVE it grants only a simulated stage admission,
    not actual FileView or SQLite write authority.
    """

    def __init__(self, path: Path, writer_id: str, *, bootstrap=False):
        if not _id(writer_id):
            raise AdmissionError("INVALID_WRITER_ID")
        _private_directory(path)
        self._path = path
        self._writer_id = writer_id
        self._pid = os.getpid()
        self._closed = False
        self._connection = None
        self._lock_fd = None

        lock = path.parent / "handoff-test.lock"
        if lock.is_symlink():
            raise AdmissionError("UNSAFE_LOCK_LINK")
        try:
            try:
                _exclusive_file(lock)
            except FileExistsError:
                pass
            _safe_regular(lock)
            self._lock_fd = os.open(lock, os.O_RDONLY |
                                    getattr(os, "O_NOFOLLOW", 0))
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise AdmissionError("OTHER_PROCESS_OWNS_HANDOFF") from exc

            exists = path.exists()
            if path.is_symlink():
                raise AdmissionError("UNSAFE_DATABASE_LINK")
            if bootstrap and exists:
                raise AdmissionError("TEST_DB_ALREADY_EXISTS")
            if not bootstrap and not exists:
                raise AdmissionError("TEST_DB_MISSING")
            if not exists:
                _exclusive_file(path)
            _safe_regular(path)
            uri = "file:" + str(path) + "?mode=rw"
            self._connection = sqlite3.connect(uri, uri=True, isolation_level=None,
                                                timeout=0.2)
            con = self._connection
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA busy_timeout=200")
            if bootstrap:
                con.execute("PRAGMA journal_mode=WAL")
                con.execute("PRAGMA synchronous=FULL")
                con.execute("BEGIN IMMEDIATE")
                try:
                    con.execute("""CREATE TABLE authority (
                      id INTEGER PRIMARY KEY CHECK(id=1),
                      phase TEXT NOT NULL,
                      epoch INTEGER NOT NULL,
                      owner_id TEXT NOT NULL,
                      pending_stage TEXT,
                      source_hash TEXT,
                      reason TEXT NOT NULL)""")
                    con.execute("INSERT INTO authority VALUES (1,'JSON_ACTIVE',0,?,?,NULL,'')",
                                (writer_id, None))
                    con.execute("PRAGMA user_version=1")
                    con.commit()
                except BaseException:
                    if con.in_transaction:
                        con.rollback()
                    raise
            else:
                if con.execute("PRAGMA user_version").fetchone()[0] != 1:
                    raise AdmissionError("UNSUPPORTED_AUTHORITY_SCHEMA")
                con.execute("BEGIN IMMEDIATE")
                try:
                    row = con.execute("SELECT * FROM authority WHERE id=1").fetchone()
                    if row is None or row["epoch"] < 0 or row["epoch"] >= 999999999:
                        raise AdmissionError("CORRUPT_OR_EXHAUSTED_AUTHORITY")
                    # OS lock is lost at process exit. Even if a stale
                    # database row says JSON_ACTIVE, the *new* owner must
                    # re-inspect, never inherit that write permission.
                    con.execute("""UPDATE authority
                      SET phase='RECOVERY_REVIEW',epoch=epoch+1,
                      owner_id=?,reason='NEW_PROCESS_MUST_REVIEW'
                      WHERE id=1""", (writer_id,))
                    con.commit()
                except BaseException:
                    if con.in_transaction:
                        con.rollback()
                    raise
        except BaseException:
            self.close()
            raise

    def _guard(self):
        if self._closed or self._connection is None or self._lock_fd is None:
            raise AdmissionError("CLOSED_AUTHORITY")
        if os.getpid() != self._pid:
            raise AdmissionError("OWNER_PROCESS_CHANGED")
        # flock fd is process-scoped, but is NOT a capability accepted
        # through caller-supplied bools, owner names or QML state.
        return self._connection

    def snapshot(self):
        con = self._guard()
        row = con.execute("SELECT * FROM authority WHERE id=1").fetchone()
        if row is None or row["owner_id"] != self._writer_id:
            raise AdmissionError("AUTHORITY_STATE_CORRUPT")
        return {"phase":row["phase"],"epoch":row["epoch"],
                "pendingStage":row["pending_stage"],
                "sourceHash":row["source_hash"],"reason":row["reason"],
                "simulatedJsonStagePermitted": row["phase"]=="JSON_ACTIVE"
                    and row["pending_stage"] is None,
                "sqliteWriteAuthorized":False,"liveChangePerformed":False}

    def _transition(self, updater):
        con = self._guard()
        con.execute("BEGIN IMMEDIATE")
        try:
            row = con.execute("SELECT * FROM authority WHERE id=1").fetchone()
            if row is None or row["owner_id"] != self._writer_id:
                raise AdmissionError("STALE_OWNER")
            result=updater(con,row)
            con.commit()
            return result
        except BaseException:
            if con.in_transaction:
                con.rollback()
            raise

    def admit_stage(self, stage_id):
        """One hypothetical legacy FileView stage. Does NOT write task data."""
        if not _id(stage_id):
            raise AdmissionError("INVALID_STAGE_ID")
        def tx(con,row):
            if row["phase"]!="JSON_ACTIVE":
                raise AdmissionError("LEGACY_STAGE_FROZEN")
            if row["pending_stage"] is not None:
                raise AdmissionError("SAVE_IN_FLIGHT")
            con.execute("UPDATE authority SET pending_stage=? WHERE id=1",
                        (stage_id,))
            return {"admitted":True,"epoch":row["epoch"],
                    "sqliteWriteAuthorized":False}
        return self._transition(tx)

    def freeze(self,expected_epoch):
        def tx(con,row):
            if row["phase"]!="JSON_ACTIVE":
                raise AdmissionError("UNEXPECTED_PHASE")
            if type(expected_epoch) is not int or row["epoch"]!=expected_epoch:
                raise AdmissionError("STALE_EPOCH")
            con.execute("""UPDATE authority SET phase='FREEZE_REQUESTED',
                           epoch=epoch+1 WHERE id=1""")
            return {"phase":"FREEZE_REQUESTED","epoch":row["epoch"]+1,
                    "pendingStage":row["pending_stage"],
                    "sqliteWriteAuthorized":False}
        return self._transition(tx)

    def settle_stage(self,stage_id,*,saved):
        """Model of onSaved/onSaveFailed after the current in-flight stage."""
        if not _id(stage_id) or type(saved) is not bool:
            raise AdmissionError("INVALID_CALLBACK")
        def tx(con,row):
            if row["phase"] not in ("JSON_ACTIVE","FREEZE_REQUESTED"):
                raise AdmissionError("UNEXPECTED_PHASE")
            if row["pending_stage"]!=stage_id:
                raise AdmissionError("STALE_SAVE_CALLBACK")
            if saved:
                con.execute("UPDATE authority SET pending_stage=NULL WHERE id=1")
                return {"callback":"SAVED","phase":row["phase"],
                        "sqliteWriteAuthorized":False}
            con.execute("""UPDATE authority SET phase='RECOVERY_REVIEW',
                         epoch=epoch+1,reason='LEGACY_SAVE_FAILED' WHERE id=1""")
            return {"callback":"FAILED","phase":"RECOVERY_REVIEW",
                    "sqliteWriteAuthorized":False}
        return self._transition(tx)

    def record_quiescence(self,first_read:bytes,second_read:bytes):
        """Caller-supplied bytes; a simulation, NOT a live filesystem freeze."""
        if not (type(first_read) is bytes and type(second_read) is bytes
                and first_read and first_read==second_read):
            raise AdmissionError("SOURCE_READBACK_MISMATCH")
        digest=hashlib.sha256(first_read).hexdigest()
        def tx(con,row):
            if row["phase"]!="FREEZE_REQUESTED":
                raise AdmissionError("UNEXPECTED_PHASE")
            if row["pending_stage"] is not None:
                raise AdmissionError("SAVE_NOT_DRAINED")
            con.execute("""UPDATE authority SET phase='JSON_QUIESCED',
                         epoch=epoch+1,source_hash=? WHERE id=1""",(digest,))
            return {"phase":"JSON_QUIESCED","sourceHash":digest,
                    "sqliteWriteAuthorized":False}
        return self._transition(tx)

    def close(self):
        if self._closed:
            return
        self._closed=True
        if self._connection is not None:
            self._connection.close()
            self._connection=None
        if self._lock_fd is not None:
            fcntl.flock(self._lock_fd,fcntl.LOCK_UN)
            os.close(self._lock_fd)
            self._lock_fd=None

    def __enter__(self):
        return self

    def __exit__(self,exc_type,exc,tb):
        self.close()
