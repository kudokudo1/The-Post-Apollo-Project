#!/usr/bin/env python3
"""Clock native cutover: durable *synthetic* old-writer stop/final-sync protocol.

This is a complete fail-closed rehearsal of a native-owned transition. It
does NOT install a Quickshell launcher, stop a live process, authenticate
an installed Clock release or grant production alarm/ring authority.

The launcher is intentionally part of this simulation: a random GUI
process that bypasses the launcher is not fenced by SQLite or flock.
"""
from __future__ import annotations

import fcntl
import importlib.util
import os
from pathlib import Path
import sqlite3
import stat
import sys


def _load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().with_name(filename))
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock component unavailable")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)
    return obj


Peer = _load("AlarmPeerIdentity.py", "clock_native_cutover_peer")
Final = _load("AlarmFinalV2SourceWitness.py", "clock_native_cutover_final")

FIXTURE_NAME = "clock-native-cutover-fixture"
STATES = frozenset(("FREE", "LAUNCH_RESERVED", "HOLD_PENDING",
                    "OLD_WRITER_EXITED", "FINAL_FILE_SYNCED",
                    "FIXTURE_NATIVE_SELECTED"))
NO_AUTHORITY = {
    "ok": False,
    "productionAuthority": False,
    "qmlChannelAuthenticated": False,
    "installedRestartFence": False,
    "nativeOwnsAlarmFile": False,
    "canTransferOwnership": False,
    "canRing": False,
    "canNotify": False,
}


class Refused(ValueError):
    """Bounded non-sensitive failure. Never contains process or alarm data."""


def _secure(path, *, directory):
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise Refused("CUTOVER_PATH_UNAVAILABLE") from exc
    if (info.st_uid != os.getuid()
            or (not stat.S_ISDIR(info.st_mode) if directory
                else not stat.S_ISREG(info.st_mode))
            or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)):
        raise Refused("CUTOVER_PATH_UNSAFE")
    return info


def _safe_root(root):
    if not isinstance(root, (str, Path)):
        raise Refused("DISPOSABLE_CUTOVER_ROOT_REQUIRED")
    path = Path(root)
    if (not path.is_absolute()
            or str(path) != os.path.normpath(str(path))
            or path.name != FIXTURE_NAME):
        raise Refused("DISPOSABLE_CUTOVER_ROOT_REQUIRED")
    _secure(path.parent, directory=True)
    _secure(path, directory=True)
    return path


def _private_file(path):
    try:
        fd = os.open(path, os.O_RDWR | os.O_CLOEXEC |
                     getattr(os, "O_NOFOLLOW", 0) | os.O_CREAT,
                     0o600)
    except OSError as exc:
        raise Refused("CUTOVER_PATH_UNAVAILABLE") from exc
    try:
        _secure(path, directory=False)
        return fd
    except BaseException:
        os.close(fd)
        raise


class CutoverLedger:
    """An actual SQLite disk journal and process-shared flock launch gate.

    State is monotonic within one fixture. A crashed or interrupted attempt
    remains blocked across process restart. No implicit reset or rollback.
    """

    def __init__(self, root):
        self.root = _safe_root(root)
        self.lockfd = _private_file(self.root / "cutover.lock")
        self.conn = None
        try:
            self.db_path = self.root / "cutover.sqlite3"
            created = not self.db_path.exists()
            # Create only if absent, without following symlink replacement.
            dbfd = _private_file(self.db_path)
            os.close(dbfd)
            if created:
                dirfd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY |
                                os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0))
                try:
                    os.fsync(dirfd)
                finally:
                    os.close(dirfd)
            self.conn = sqlite3.connect(
                f"file:{self.db_path}?mode=rw", uri=True,
                isolation_level=None, timeout=0.0)
            self.conn.execute("PRAGMA journal_mode=DELETE")
            self.conn.execute("PRAGMA synchronous=FULL")
            self.conn.execute("PRAGMA trusted_schema=OFF")
            self.conn.execute("CREATE TABLE IF NOT EXISTS cutover("
                              "id INTEGER PRIMARY KEY CHECK(id=1),"
                              "phase TEXT NOT NULL,"
                              "writer_pid INTEGER NOT NULL,"
                              "writer_ticks INTEGER NOT NULL)")
            self.conn.execute("INSERT OR IGNORE INTO cutover "
                              "(id,phase,writer_pid,writer_ticks)"
                              "VALUES(1,'FREE',0,0)")
            self._read()
        except (sqlite3.Error, OSError, Refused) as exc:
            self.close()
            raise Refused("CUTOVER_JOURNAL_UNSAFE") from exc

    def _read(self):
        _safe_root(self.root)
        _secure(self.db_path, directory=False)
        try:
            rows = self.conn.execute(
                "SELECT phase,writer_pid,writer_ticks FROM cutover"
            ).fetchall()
        except sqlite3.Error as exc:
            raise Refused("CUTOVER_JOURNAL_UNSAFE") from exc
        if (len(rows) != 1 or rows[0][0] not in STATES
                or type(rows[0][1]) is not int or rows[0][1] < 0
                or type(rows[0][2]) is not int or rows[0][2] < 0):
            raise Refused("CUTOVER_JOURNAL_UNSAFE")
        return rows[0]

    def _lock(self):
        try:
            fcntl.flock(self.lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            raise Refused("CUTOVER_GATE_BUSY") from exc

    def _transition(self, old, next_phase, pid=None, ticks=None):
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            phase, stored_pid, stored_ticks = self._read()
            if phase != old:
                raise Refused("CUTOVER_TRANSITION_REFUSED")
            next_pid = stored_pid if pid is None else pid
            next_ticks = stored_ticks if ticks is None else ticks
            self.conn.execute(
                "UPDATE cutover SET phase=?,writer_pid=?,writer_ticks=? "
                "WHERE id=1", (next_phase, next_pid, next_ticks))
            self.conn.execute("COMMIT")
        except BaseException:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise

    def reserve_old_writer_launch(self):
        """Atomic launcher gate: a reservation is durable BEFORE spawn.

        A failing or crashed launch is not silently retried. Operator
        recovery is required to clear a failed fixture reservation.
        """
        self._lock()
        try:
            if self._read() != ("FREE", 0, 0):
                raise Refused("OLD_WRITER_LAUNCH_FENCED")
            self._transition("FREE", "LAUNCH_RESERVED")
        finally:
            fcntl.flock(self.lockfd, fcntl.LOCK_UN)

    def attach_writer_identity(self, pid, ticks):
        if (type(pid) is not int or pid <= 1
                or type(ticks) is not int or ticks <= 0):
            raise Refused("OLD_WRITER_PIN_REQUIRED")
        self._lock()
        try:
            phase, stored_pid, _ = self._read()
            if phase != "LAUNCH_RESERVED" or stored_pid:
                raise Refused("OLD_WRITER_PIN_ALREADY_ATTACHED")
            self._transition("LAUNCH_RESERVED", "LAUNCH_RESERVED",
                             pid=pid, ticks=ticks)
        finally:
            fcntl.flock(self.lockfd, fcntl.LOCK_UN)

    def read_only_state(self):
        return self._read()[0]

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
        if getattr(self, "lockfd", None) is not None:
            os.close(self.lockfd)
            self.lockfd = None


class ClockOfflineCutover:
    """Controller owns launch lock and holds exact old-writer pidfd.

    Does not signal, stop, terminate or restart any process. Requires old
    writer to exit by an independently controlled shutdown procedure.
    """

    def __init__(self, *, root, old_socket, old_pid, old_ticks,
                 old_executable, final_path, final_digest, final_uid,
                 synthetic_only=False):
        if synthetic_only is not True:
            raise Refused("PRODUCTION_CUTOVER_NOT_INSTALLED")
        self.ledger = CutoverLedger(root)
        self.peer = None
        self.old_socket = old_socket
        self.started = False
        try:
            phase, pid, ticks = self.ledger._read()
            if (phase != "LAUNCH_RESERVED"
                    or pid != old_pid or ticks != old_ticks):
                raise Refused("OLD_WRITER_LAUNCH_RECEIPT_REQUIRED")
            self.peer = Peer.capture(old_socket, old_executable)
            if ((self.peer["pid"], self.peer["ticks"])
                    != (old_pid, old_ticks)):
                raise Refused("OLD_WRITER_KERNEL_PIN_MISMATCH")
            self.final = Final.ClockFinalV2SourceWitness(
                source_path=final_path, pinned_sha256=final_digest,
                expected_uid=final_uid, synthetic_only=True)
            self.ledger._lock()
        except (Peer.Refused, Final.Refused, OSError) as exc:
            self.close()
            raise Refused("OLD_WRITER_OR_FINAL_SOURCE_UNVERIFIED") from exc
        except BaseException:
            self.close()
            raise

    def request_shutdown(self):
        """Persist HOLD first, *then* external owner may stop writer."""
        if self.started:
            raise Refused("OLD_WRITER_SHUTDOWN_ALREADY_REQUESTED")
        if self.ledger.read_only_state() != "LAUNCH_RESERVED":
            raise Refused("OLD_WRITER_SHUTDOWN_STATE_INVALID")
        try:
            Peer.verify(self.old_socket, self.peer, self.peer["exe"])
        except Peer.Refused as exc:
            raise Refused("OLD_WRITER_PROCESS_CHANGED") from exc
        self.ledger._transition("LAUNCH_RESERVED", "HOLD_PENDING")
        self.started = True
        return self.inspect()

    def witness_exit(self):
        if self.ledger.read_only_state() != "HOLD_PENDING":
            raise Refused("CUTOVER_EXIT_PHASE_INVALID")
        if not Peer._exited(self.peer["pidfd"]):
            raise Refused("OLD_WRITER_STILL_RUNNING")
        self.ledger._transition("HOLD_PENDING", "OLD_WRITER_EXITED")
        return self.inspect()

    def witness_final_sync(self):
        if self.ledger.read_only_state() != "OLD_WRITER_EXITED":
            raise Refused("OLD_WRITER_EXIT_REQUIRED")
        if not Peer._exited(self.peer["pidfd"]):
            raise Refused("OLD_WRITER_REAPPEARED")
        try:
            evidence = self.final.observe()
        except (Final.Refused, OSError) as exc:
            raise Refused("FINAL_SOURCE_NOT_SYNCHRONIZED") from exc
        if not evidence["fileSyncObserved"] or not evidence[
                "parentDirectorySyncObserved"]:
            raise Refused("FINAL_SOURCE_NOT_SYNCHRONIZED")
        if not Peer._exited(self.peer["pidfd"]):
            raise Refused("OLD_WRITER_REAPPEARED")
        self.ledger._transition("OLD_WRITER_EXITED", "FINAL_FILE_SYNCED")
        return self.inspect()

    def select_fixture_native(self):
        if self.ledger.read_only_state() != "FINAL_FILE_SYNCED":
            raise Refused("FINAL_SYNC_REQUIRED_FOR_TEST_NATIVE")
        if not Peer._exited(self.peer["pidfd"]):
            raise Refused("OLD_WRITER_REAPPEARED")
        # Reopen and remeasure after the previous sync: a changed source
        # must invalidate even a synthetic selection.
        try:
            self.final.observe()
        except (Final.Refused, OSError) as exc:
            raise Refused("FINAL_SOURCE_CHANGED_AFTER_SYNC") from exc
        self.ledger._transition("FINAL_FILE_SYNCED",
                                "FIXTURE_NATIVE_SELECTED")
        return self.inspect()

    def inspect(self):
        phase = self.ledger.read_only_state()
        return {
            "phase": phase,
            "syntheticLaunchGateClosed": phase != "FREE",
            "oldWriterKernelExitObserved": phase in (
                "OLD_WRITER_EXITED", "FINAL_FILE_SYNCED",
                "FIXTURE_NATIVE_SELECTED"),
            "finalFileSyncObserved": phase in (
                "FINAL_FILE_SYNCED", "FIXTURE_NATIVE_SELECTED"),
            "syntheticNativeSelected": phase == "FIXTURE_NATIVE_SELECTED",
            "fixtureOnly": True,
            **NO_AUTHORITY,
        }

    def close(self):
        if self.peer is not None:
            Peer.close(self.peer)
            self.peer = None
        if getattr(self, "ledger", None) is not None:
            self.ledger.close()
