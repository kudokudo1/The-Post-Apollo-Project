#!/usr/bin/env python3
"""Clock BG1-B2B11: durable same-process session floor for native CI supervisor.

The real AF_UNIX B2B10 supervisor uses this only in explicitly marked,
disposable Linux tests. It protects a *cooperative test-session* epoch and
requires the original kernel pidfd to report exit before a successor's
strictly greater epoch can be observed. Production Clock sessions cannot
enroll, receive permissions, stop Quickshell or ring through this ledger.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import sqlite3
import stat
import uuid


def _load_peer():
    target = Path(__file__).resolve().with_name("AlarmPeerIdentity.py")
    spec = importlib.util.spec_from_file_location("clock_b2b11_peer", target)
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock kernel peer identity unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Peer = _load_peer()
LEDGER_NAME = "supervisor-session-v1.sqlite3"
RUNTIME_SUBDIR = "post-apollo-clock"
TEST_RUNTIME = "bg1-clock-supervisor-fixture"
MAX_EPOCH = 2147483647
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
SCOPE = "synthetic-clock-ui-bridge"
NO_AUTHORITY = {
    "roleAuthenticated": False,
    "writerStopped": False,
    "releaseAcknowledged": False,
    "oldWriterRestartPrevented": False,
    "ownsRealAlarmFile": False,
    "canTransferOwnership": False,
    "canRing": False,
    "canNotify": False,
}


class Refused(ValueError):
    """Fixed public refusal code, no alarm titles, notes, paths or keys."""


def _private_dir(path):
    try:
        meta = os.lstat(path)
    except OSError as exc:
        raise Refused("SESSION_DIRECTORY_UNAVAILABLE") from exc
    if (not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid()
            or stat.S_IMODE(meta.st_mode) != 0o700):
        raise Refused("UNSAFE_SESSION_DIRECTORY")


def _boot_id():
    try:
        original = Path("/proc/sys/kernel/random/boot_id").read_text(
            encoding="ascii").strip()
        normalized = str(uuid.UUID(original))
    except (OSError, ValueError, UnicodeError) as exc:
        raise Refused("KERNEL_BOOT_ID_UNVERIFIED") from exc
    if original != normalized:
        raise Refused("KERNEL_BOOT_ID_UNVERIFIED")
    return normalized


def _secure_db(path):
    if path.is_symlink():
        raise Refused("SESSION_LEDGER_SYMLINK")
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                     os.O_CLOEXEC | getattr(os, "O_NONBLOCK", 0), 0o600)
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
                    or st.st_uid != os.getuid()
                    or stat.S_IMODE(st.st_mode) != 0o600):
                raise Refused("UNSAFE_SESSION_LEDGER")
        finally:
            os.close(fd)
        db = sqlite3.connect(path, isolation_level=None, timeout=4)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=4000")
        db.execute("""CREATE TABLE IF NOT EXISTS clock_sessions (
            scope TEXT PRIMARY KEY,
            boot_id TEXT NOT NULL,
            epoch INTEGER NOT NULL CHECK(epoch >= 1),
            pid INTEGER NOT NULL CHECK(pid > 1),
            ticks INTEGER NOT NULL CHECK(ticks > 0),
            release_root_sha256 TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN
                ('SIGNED_PROCESS_OBSERVED','PIDFD_EXIT_OBSERVED'))
        )""")
        return db
    except (OSError, sqlite3.Error) as exc:
        raise Refused("SESSION_LEDGER_UNAVAILABLE") from exc


def _validate(pid, ticks, epoch, root):
    if (type(pid) is not int or pid <= 1
            or type(ticks) is not int or ticks <= 0
            or type(epoch) is not int or not 1 <= epoch <= MAX_EPOCH
            or type(root) is not str or not HEX.fullmatch(root)):
        raise Refused("INVALID_INDEPENDENT_SESSION_PINS")


class ClockSessionLedger:
    """One durable slot for a verified signed disposable Clock session."""

    def __init__(self, directory, *, synthetic_only=False):
        path = Path(directory)
        if (synthetic_only is not True
                or not path.is_absolute()
                or path.name != RUNTIME_SUBDIR
                or path.parent.name != TEST_RUNTIME
                or str(path) != os.path.normpath(str(path))):
            raise Refused("DISPOSABLE_SESSION_LEDGER_ONLY")
        _private_dir(path.parent)
        _private_dir(path)
        self.directory = path
        self.path = path / LEDGER_NAME
        self.boot_id = _boot_id()

    def _db(self):
        _private_dir(self.directory.parent)
        _private_dir(self.directory)
        return _secure_db(self.path)

    def _read(self, db):
        row = db.execute(
            "SELECT boot_id,epoch,pid,ticks,release_root_sha256,state "
            "FROM clock_sessions WHERE scope=?", (SCOPE,)).fetchone()
        if row is not None and (
                type(row[0]) is not str or type(row[1]) is not int
                or type(row[2]) is not int or type(row[3]) is not int
                or type(row[4]) is not str or type(row[5]) is not str
                or not 1 <= row[1] <= MAX_EPOCH or row[2] <= 1
                or row[3] <= 0 or not HEX.fullmatch(row[4])
                or row[5] not in (
                    "SIGNED_PROCESS_OBSERVED", "PIDFD_EXIT_OBSERVED")):
            raise Refused("INVALID_STORED_SESSION")
        return row

    def observe_signed_process(self, *, pid, ticks, epoch,
                               release_root_sha256):
        """Caller *already* verified same-peer B2B9 signed origin.

        This does not decide who is authorized. Only B2B10's synthetic
        kernel-peer verification may call it in the native test harness.
        """
        _validate(pid, ticks, epoch, release_root_sha256)
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = self._read(db)
            if row is not None:
                boot, old_epoch, old_pid, old_ticks, old_root, state = row
                if boot != self.boot_id:
                    raise Refused("PREVIOUS_BOOT_SESSION_REQUIRES_RECOVERY")
                if state == "SIGNED_PROCESS_OBSERVED":
                    if (old_epoch, old_pid, old_ticks, old_root) != (
                            epoch, pid, ticks, release_root_sha256):
                        raise Refused("PRIOR_SIGNED_PROCESS_STILL_ENROLLED")
                    db.execute("COMMIT")
                    return self.inspect()
                if epoch <= old_epoch:
                    raise Refused("RETIRED_SYNTHETIC_SESSION_EPOCH")
                if (pid, ticks) == (old_pid, old_ticks):
                    raise Refused("RETIRED_PROCESS_REENROLLMENT")
                db.execute(
                    "UPDATE clock_sessions SET epoch=?,pid=?,ticks=?,"
                    "release_root_sha256=?,state='SIGNED_PROCESS_OBSERVED' "
                    "WHERE scope=? AND state='PIDFD_EXIT_OBSERVED'",
                    (epoch, pid, ticks, release_root_sha256, SCOPE))
            else:
                db.execute(
                    "INSERT INTO clock_sessions VALUES(?,?,?,?,?,?,?)",
                    (SCOPE, self.boot_id, epoch, pid, ticks,
                     release_root_sha256, "SIGNED_PROCESS_OBSERVED"))
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return self.inspect()

    def observe_exited_pidfd(self, *, pid, ticks, epoch, pidfd):
        if (type(pidfd) is not int or pidfd < 0
                or type(pid) is not int or pid <= 1
                or type(ticks) is not int or ticks <= 0
                or type(epoch) is not int or not 1 <= epoch <= MAX_EPOCH):
            raise Refused("INVALID_PIDFD_EXIT_PINS")
        try:
            os.fstat(pidfd)
            exited = Peer._exited(pidfd)
        except (OSError, ValueError, Peer.Refused) as exc:
            raise Refused("ORIGINAL_KERNEL_PIDFD_UNVERIFIED") from exc
        if not exited:
            raise Refused("SIGNED_SESSION_PROCESS_STILL_RUNNING")
        db = self._db()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = self._read(db)
            if (row is None or row[0] != self.boot_id
                    or row[1:4] != (epoch, pid, ticks)
                    or row[5] != "SIGNED_PROCESS_OBSERVED"):
                raise Refused("NO_MATCHING_LIVE_SIGNED_SESSION")
            if not Peer._exited(pidfd):
                raise Refused("SIGNED_SESSION_PROCESS_STILL_RUNNING")
            updated = db.execute(
                "UPDATE clock_sessions SET state='PIDFD_EXIT_OBSERVED' "
                "WHERE scope=? AND state='SIGNED_PROCESS_OBSERVED'",
                (SCOPE,)).rowcount
            if updated != 1:
                raise Refused("SESSION_STATE_CHANGED")
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return self.inspect()

    def inspect(self):
        db = self._db()
        try:
            row = self._read(db)
        finally:
            db.close()
        return dict({
            "state": row[5] if row else "NONE",
            "observedEpoch": row[1] if row else 0,
            "sameBoot": bool(row and row[0] == self.boot_id),
            "fixtureOnly": True,
        }, **NO_AUTHORITY)
