#!/usr/bin/env python3
"""V2k fixture-only durable nonce replay ledger, never a production gateway.

No CLI, no live source or ArchiveStore integration. Root must be explicitly
provided as a private 0700 test directory by the caller. Never call from UI.
"""
from contextlib import closing
import os
from pathlib import Path
import re
import sqlite3
import stat

NAME = "trashpp-v2k-test-nonces.sqlite3"
IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
NONCE = re.compile(r"^[0-9a-f]{32}$")
SHA = re.compile(r"^[0-9a-f]{64}$")


class ReplayLedgerError(Exception):
    """Stable error code; no paths, records or exception details."""


def _check(condition, code):
    if not condition:
        raise ReplayLedgerError(code)


def _file(path, missing=False):
    try:
        entry = path.lstat()
    except FileNotFoundError:
        _check(missing, "CAPTURE_LEDGER_MISSING")
        return False
    except OSError as exc:
        raise ReplayLedgerError("CAPTURE_LEDGER_UNAVAILABLE") from exc
    _check(stat.S_ISREG(entry.st_mode) and entry.st_uid == os.geteuid()
           and entry.st_nlink == 1 and entry.st_mode & 0o077 == 0,
           "CAPTURE_LEDGER_UNSAFE")
    return True


class TestReplayLedger:
    def __init__(self, private_root):
        _check(type(private_root) in (str, Path),
               "CAPTURE_LEDGER_ROOT_INVALID")
        root = Path(private_root)
        _check(root.is_absolute() and ".." not in root.parts
               and len(str(root)) <= 4096,
               "CAPTURE_LEDGER_ROOT_INVALID")
        try:
            info = root.lstat()
        except OSError as exc:
            raise ReplayLedgerError("CAPTURE_LEDGER_ROOT_UNAVAILABLE") from exc
        _check(stat.S_ISDIR(info.st_mode)
               and info.st_uid == os.geteuid()
               and info.st_mode & 0o077 == 0,
               "CAPTURE_LEDGER_ROOT_UNSAFE")
        self.root = root
        self.path = root / NAME
        exists = _file(self.path, missing=True)
        if not exists:
            try:
                fd = os.open(self.path,
                             os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | getattr(os, "O_NOFOLLOW", 0), 0o600)
                os.close(fd)
            except FileExistsError:
                _file(self.path)
            except OSError as exc:
                raise ReplayLedgerError("CAPTURE_LEDGER_CREATE_FAILED") from exc
        self._init()

    def _connect(self):
        _file(self.path)
        for suffix in ("-wal", "-shm"):
            try:
                (self.root / (NAME + suffix)).lstat()
            except FileNotFoundError:
                continue
            raise ReplayLedgerError("CAPTURE_LEDGER_UNEXPECTED_SIDECAR")
        try:
            db = sqlite3.connect(str(self.path), timeout=5)
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA busy_timeout=5000")
            return db
        except sqlite3.DatabaseError as exc:
            raise ReplayLedgerError("CAPTURE_LEDGER_UNAVAILABLE") from exc

    def _init(self):
        with closing(self._connect()) as db:
            try:
                with db:
                    db.execute("""CREATE TABLE IF NOT EXISTS consumed (
                        owner_id TEXT NOT NULL,
                        key_id TEXT NOT NULL,
                        nonce TEXT NOT NULL,
                        proof_sha256 TEXT NOT NULL,
                        PRIMARY KEY(owner_id,key_id,nonce),
                        UNIQUE(proof_sha256)
                    )""")
            except sqlite3.DatabaseError as exc:
                raise ReplayLedgerError("CAPTURE_LEDGER_INIT_FAILED") from exc

    def consume(self, owner, key_id, nonce, digest):
        _check(type(owner) is str and IDENTIFIER.fullmatch(owner)
               and type(key_id) is str and IDENTIFIER.fullmatch(key_id)
               and type(nonce) is str and NONCE.fullmatch(nonce)
               and type(digest) is str and SHA.fullmatch(digest),
               "CAPTURE_REPLAY_RECORD_INVALID")
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                db.execute("""INSERT INTO consumed
                    (owner_id,key_id,nonce,proof_sha256) VALUES(?,?,?,?)""",
                    (owner, key_id, nonce, digest))
                db.commit()
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise ReplayLedgerError("CAPTURE_NONCE_ALREADY_CONSUMED") from exc
            except sqlite3.DatabaseError as exc:
                db.rollback()
                raise ReplayLedgerError("CAPTURE_LEDGER_WRITE_FAILED") from exc
            except BaseException:
                db.rollback()
                raise
        return {"state": "TEST_NONCE_CONSUMED", "productionAllowed": False}

    def count(self):
        with closing(self._connect()) as db:
            return db.execute("SELECT count(*) FROM consumed").fetchone()[0]
