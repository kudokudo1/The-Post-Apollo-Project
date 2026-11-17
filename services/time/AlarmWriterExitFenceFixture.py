#!/usr/bin/env python3
"""BG1-B2B8: durable OLD-process-exit evidence after signed fixture reply.

DISPOSABLE ONLY. A pidfd-observed process exit does not stop Quickshell
FileView callbacks or prohibit launching a *new* old writer. This module
never grants a real alarm writer lease or rings. Its local epoch fence applies
solely to cooperative synthetic test clients consulting this fixture ledger.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import stat


def _sibling(name):
    path = Path(__file__).resolve().with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("b2b8_" + name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Missing Clock module " + name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Chain = _sibling("AlarmRoleBoundReleasePreflight")
Peer = Chain.Receipt.Peer
Receipt = Chain.Receipt
MAX_EPOCH = 2147483647
LEDGER_NAME = "observed-old-writer-exit-v1.sqlite3"


class Refused(ValueError):
    """Stable refusal code, with no alarm private fields or file paths."""


def _digest(source):
    try:
        return Receipt._safe_read_source(source)
    except (Receipt.Refused, OSError, ValueError) as exc:
        raise Refused("ALARM_SOURCE_REVISION_UNVERIFIED") from exc


def _safe_database(path):
    if path.is_symlink():
        raise Refused("UNSAFE_EXIT_LEDGER")
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                     os.O_CLOEXEC, 0o600)
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode)
                    or st.st_uid != os.getuid()
                    or st.st_nlink != 1
                    or stat.S_IMODE(st.st_mode) != 0o600):
                raise Refused("UNSAFE_EXIT_LEDGER")
        finally:
            os.close(fd)
        db = sqlite3.connect(path, isolation_level=None, timeout=3)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=3000")
        db.execute("""CREATE TABLE IF NOT EXISTS exit_observations (
            scope TEXT PRIMARY KEY,
            old_epoch INTEGER NOT NULL,
            new_epoch INTEGER NOT NULL,
            pid INTEGER NOT NULL,
            ticks INTEGER NOT NULL,
            source_digest TEXT NOT NULL,
            challenge_digest TEXT NOT NULL,
            state TEXT NOT NULL CHECK(
                state IN ('PREPARED','SIGNED_REPLY_OBSERVED',
                          'PROCESS_EXIT_OBSERVED'))
        )""")
        return db
    except (OSError, sqlite3.Error) as exc:
        raise Refused("EXIT_LEDGER_UNAVAILABLE") from exc


class DurableExitObservationFixture:
    """Bind a B2B7 signed reply to a real pidfd exit and restart-safe fence.

    Every public result is observation-only. All old epochs must remain
    denied for cooperating fixture participants after an observed exit.
    """

    def __init__(self, chain, *, synthetic_only=False):
        if (synthetic_only is not True
                or type(chain) is not Chain.RoleBoundReleasePreflight
                or chain._origin._disposable is not True):
            raise Refused("DISPOSABLE_EXIT_OBSERVER_ONLY")
        release = chain._release
        root = release.root
        source = release.source
        if (root.name != "bg1-signed-release-fixture"
                or source.name != "time-alarms-v2.json"
                or source.parent.name != "synthetic-quickshell"
                or source.parent.parent != root.parent):
            raise Refused("DISPOSABLE_EXIT_PATH_REQUIRED")
        for directory in (root, source.parent):
            if directory.is_symlink():
                raise Refused("UNSAFE_EXIT_DIRECTORY")
            try:
                st = directory.stat()
            except OSError as exc:
                raise Refused("UNSAFE_EXIT_DIRECTORY") from exc
            if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
                    or stat.S_IMODE(st.st_mode) != 0o700):
                raise Refused("UNSAFE_EXIT_DIRECTORY")
        self.chain = chain
        self.root = root
        self.source = source
        self.path = root / LEDGER_NAME
        self.scope = Receipt._source_scope(source)
        self.pid = release.expected_pid
        self.ticks = release.expected_ticks

    def _db(self):
        return _safe_database(self.path)

    def _row(self, db):
        return db.execute(
            "SELECT old_epoch,new_epoch,pid,ticks,source_digest,"
            "challenge_digest,state FROM exit_observations WHERE scope=?",
            (self.scope,)).fetchone()

    def _same_witness(self, witness):
        if (not isinstance(witness, dict)
                or witness.get("pid") != self.pid
                or witness.get("ticks") != self.ticks
                or type(witness.get("pidfd")) is not int):
            raise Refused("WRITER_PROCESS_WITNESS_MISMATCH")
        try:
            os.fstat(witness["pidfd"])
        except (OSError, ValueError) as exc:
            raise Refused("WRITER_PIDFD_UNVERIFIED") from exc

    def prepare(self, connection, witness, *, expected_source_digest,
                old_epoch, new_epoch):
        self._same_witness(witness)
        if (type(old_epoch) is not int or type(new_epoch) is not int
                or not 1 <= old_epoch < new_epoch <= MAX_EPOCH):
            raise Refused("INVALID_OWNER_EPOCH_ADVANCE")
        if (type(expected_source_digest) is not str
                or len(expected_source_digest) != 64):
            raise Refused("INVALID_SOURCE_DIGEST")
        # Before any new challenge, a persisted old floor must be checked.
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            if self._row(db) is not None:
                raise Refused("EXISTING_EXIT_ATTEMPT_OR_RETIRED_EPOCH")
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

        if _digest(self.source) != expected_source_digest:
            raise Refused("ALARM_SOURCE_REVISION_UNVERIFIED")
        try:
            challenge = self.chain.issue_observation(
                connection, witness,
                expected_source_digest=expected_source_digest,
                old_epoch=old_epoch, new_epoch=new_epoch)
        except (Chain.Refused, ValueError, OSError) as exc:
            raise Refused("SIGNED_WRITER_CHALLENGE_REFUSED") from exc
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            if self._row(db) is not None:
                raise Refused("EXISTING_EXIT_ATTEMPT_OR_RETIRED_EPOCH")
            if _digest(self.source) != expected_source_digest:
                raise Refused("ALARM_SOURCE_REVISION_UNVERIFIED")
            self._same_witness(witness)
            db.execute(
                "INSERT INTO exit_observations VALUES(?,?,?,?,?,?,?,?)",
                (self.scope, old_epoch, new_epoch, self.pid, self.ticks,
                 expected_source_digest,
                 hashlib.sha256(challenge["challenge"].encode("ascii")).hexdigest(),
                 "PREPARED"))
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return dict(challenge, writerExited=False,
                    writerStopped=False, releaseAcknowledged=False,
                    canTransferOwnership=False, canRing=False, canNotify=False)

    def observe_signed_reply(self, connection, witness, *,
                             signed_reply, signature):
        self._same_witness(witness)
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = self._row(db)
            if row is None or row[-1] != "PREPARED":
                raise Refused("SIGNED_REPLY_ATTEMPT_NOT_PREPARED")
            if (row[2:4] != (self.pid, self.ticks)
                    or _digest(self.source) != row[4]):
                raise Refused("SIGNED_REPLY_WRITER_OR_SOURCE_CHANGED")
            try:
                observed = self.chain.observe_reply(
                    connection, witness,
                    signed_reply=signed_reply, signature=signature)
            except (Chain.Refused, ValueError, OSError) as exc:
                raise Refused("SIGNED_OLD_WRITER_REPLY_REFUSED") from exc
            if (observed.get("writerStopped") is not False
                    or observed.get("releaseAcknowledged") is not False):
                raise Refused("UNTRUSTED_RELEASE_ASSERTION")
            if _digest(self.source) != row[4]:
                raise Refused("SOURCE_CHANGED_AFTER_SIGNED_REPLY")
            self._same_witness(witness)
            updated = db.execute(
                "UPDATE exit_observations SET state='SIGNED_REPLY_OBSERVED' "
                "WHERE scope=? AND state='PREPARED'", (self.scope,)).rowcount
            if updated != 1:
                raise Refused("REPLY_STATE_CHANGED")
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return self.inspect()

    def observe_process_exit(self, witness):
        self._same_witness(witness)
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = self._row(db)
            if row is None or row[-1] != "SIGNED_REPLY_OBSERVED":
                raise Refused("SIGNED_REPLY_REQUIRED_BEFORE_EXIT")
            if row[2:4] != (self.pid, self.ticks):
                raise Refused("EXIT_PROCESS_WITNESS_MISMATCH")
            try:
                exited = Peer._exited(witness["pidfd"])
            except (Peer.Refused, OSError, ValueError) as exc:
                raise Refused("PIDFD_EXIT_EVIDENCE_UNAVAILABLE") from exc
            if not exited:
                raise Refused("OLD_WRITER_STILL_RUNNING")
            if _digest(self.source) != row[4]:
                raise Refused("ALARM_SOURCE_CHANGED_BEFORE_EXIT")
            db.execute(
                "UPDATE exit_observations SET state='PROCESS_EXIT_OBSERVED' "
                "WHERE scope=? AND state='SIGNED_REPLY_OBSERVED'",(self.scope,))
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return self.inspect()

    def refuse_old_epoch(self, epoch):
        if type(epoch) is not int or not 1 <= epoch <= MAX_EPOCH:
            raise Refused("INVALID_EPOCH_QUERY")
        db = self._db()
        try:
            row = self._row(db)
            if row is None:
                raise Refused("NO_DURABLE_WRITER_EXIT_RECORD")
            if row[-1] != "PROCESS_EXIT_OBSERVED":
                raise Refused("WRITER_EXIT_NOT_DURABLY_OBSERVED")
            if epoch <= row[0]:
                raise Refused("RETIRED_SYNTHETIC_WRITER_EPOCH")
            # A newer epoch is only a *candidate*. It cannot claim the
            # real V2 alarm file or ring from this ledger.
            return {"candidateEpoch": epoch, "fixtureOnly": True,
                    "canTransferOwnership": False, "canRing": False}
        finally:
            db.close()

    def inspect(self):
        db = self._db()
        try:
            row = self._row(db)
        finally:
            db.close()
        return {
            "state": row[-1] if row else "NONE",
            "writerExitObserved": bool(row and row[-1] == "PROCESS_EXIT_OBSERVED"),
            "retiredEpoch": row[0] if row and row[-1] == "PROCESS_EXIT_OBSERVED" else 0,
            "oldProcessPid": row[2] if row else 0,
            "fixtureOnly": True,
            "oldWriterRestartPrevented": False,
            "ownsRealAlarmFile": False,
            "releaseAcknowledged": False,
            "canTransferOwnership": False,
            "canRing": False,
            "canNotify": False,
        }
