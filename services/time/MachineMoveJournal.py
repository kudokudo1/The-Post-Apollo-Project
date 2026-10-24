"""MACHINE M1l: durable, owner-only journal for isolated move-pilot tests.

There is no CLI, live Sway runner, Quickshell binding, or automatic recovery.
Callers must explicitly pass a journal path and runners. The *only* stored
fields are allowlisted before-state and state transitions, not window titles,
browser data, commands, arbitrary serialized desktop snapshots, or tokens.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid

SCHEMA_VERSION = 1
MAX_ROWS = 40
ACTIVE = frozenset(("prepared", "dispatching", "uncertain_requires_manual_review"))
TERMINAL = frozenset(("verified_moved", "refused_no_confirmed_move"))
OUTCOMES = TERMINAL | frozenset(("uncertain_requires_manual_review",))
FIELDS = frozenset(("con_id", "app_id", "workspace", "target_workspace"))


class JournalError(ValueError):
    pass


def suggested_path():
    """Proposed separate DB, adjacent to but never inside machine.db."""
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "post-apollo" / "machine" / "move-operations.db"


def _safe_directory(path, create):
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or not path.is_dir():
        raise JournalError("INVALID JOURNAL DIRECTORY")
    info = path.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise JournalError("UNSAFE JOURNAL DIRECTORY")


def _safe_file(path):
    if path.is_symlink():
        raise JournalError("JOURNAL LINK REFUSED")
    if not path.exists():
        return False
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise JournalError("UNSAFE JOURNAL DATABASE")
    return True


def _clean_before(before):
    if not isinstance(before, dict) or set(before) != FIELDS:
        raise JournalError("INVALID BEFORE STATE")
    con_id = before["con_id"]
    if type(con_id) is not int or con_id < 1 or con_id > 9007199254740991:
        raise JournalError("INVALID CONTAINER ID")
    fields = [before[k] for k in ("app_id", "workspace", "target_workspace")]
    for value in fields:
        if (not isinstance(value, str) or not 1 <= len(value) <= 128
                or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise JournalError("INVALID BEFORE STATE")
    if before["workspace"] == before["target_workspace"]:
        raise JournalError("NO-OP NOT JOURNALED")
    return {"con_id": con_id, "app_id": fields[0],
            "workspace": fields[1], "target_workspace": fields[2]}


def _now():
    return datetime.now(timezone.utc).isoformat()


class MoveJournal:
    """Explicit injected storage: constructor never creates a file."""

    def __init__(self, path):
        if not isinstance(path, (str, Path)):
            raise JournalError("EXPLICIT JOURNAL PATH REQUIRED")
        self.path = Path(path).expanduser()
        if not self.path.is_absolute() or self.path.name != "move-operations.db":
            raise JournalError("INVALID JOURNAL PATH")

    def _connect(self, writable):
        if not writable and not self.path.exists() and not self.path.is_symlink():
            return None
        _safe_directory(self.path.parent, writable)
        present = _safe_file(self.path)
        if writable and not present:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(self.path, flags, 0o600)
            except FileExistsError:
                _safe_file(self.path)
            else:
                os.close(fd)
        if writable:
            connection = sqlite3.connect(str(self.path), timeout=5.0)
        else:
            from urllib.parse import quote
            connection = sqlite3.connect(
                "file:" + quote(str(self.path), safe="/") + "?mode=ro",
                uri=True, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA_VERSION) or (not writable and version != SCHEMA_VERSION):
            connection.close()
            raise JournalError("UNSUPPORTED JOURNAL SCHEMA")
        if writable:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                connection.execute("""CREATE TABLE IF NOT EXISTS operations (
                  id TEXT PRIMARY KEY,
                  phase TEXT NOT NULL,
                  before_json TEXT NOT NULL,
                  created_utc TEXT NOT NULL,
                  updated_utc TEXT NOT NULL,
                  observed_workspace TEXT,
                  CHECK (phase IN (
                    'prepared','dispatching','verified_moved',
                    'refused_no_confirmed_move','uncertain_requires_manual_review'))
                )""")
                connection.execute("""CREATE TABLE IF NOT EXISTS transitions (
                  seq INTEGER PRIMARY KEY AUTOINCREMENT,
                  operation_id TEXT NOT NULL,
                  phase TEXT NOT NULL,
                  at_utc TEXT NOT NULL,
                  FOREIGN KEY(operation_id) REFERENCES operations(id)
                )""")
                connection.execute("PRAGMA user_version=1")
        return connection

    def begin(self, before):
        clean = _clean_before(before)
        payload = json.dumps(clean, ensure_ascii=False, separators=(",", ":"))
        operation_id = str(uuid.uuid4())
        timestamp = _now()
        conn = self._connect(True)
        try:
            conn.execute("BEGIN IMMEDIATE")
            # One operation at a time while any prior result needs recovery review.
            active = conn.execute(
                "SELECT COUNT(*) FROM operations WHERE phase IN (?,?,?)",
                tuple(sorted(ACTIVE))).fetchone()[0]
            if active:
                raise JournalError("PRIOR MOVE NEEDS REVIEW")
            conn.execute("""INSERT INTO operations
                (id, phase, before_json, created_utc, updated_utc, observed_workspace)
                VALUES (?, 'prepared', ?, ?, ?, NULL)""",
                (operation_id, payload, timestamp, timestamp))
            conn.execute("""INSERT INTO transitions (operation_id,phase,at_utc)
                            VALUES (?, 'prepared', ?)""", (operation_id, timestamp))
            conn.commit()
            return operation_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _advance(self, operation_id, old, new, observed=None):
        try:
            operation_id = str(uuid.UUID(operation_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise JournalError("INVALID OPERATION ID") from exc
        if (old, new) not in (("prepared", "dispatching"),) and (
                old != "dispatching" or new not in OUTCOMES):
            raise JournalError("INVALID PHASE TRANSITION")
        if observed is not None and (not isinstance(observed, str)
                or len(observed) > 128 or any(ord(c) < 32 or ord(c) == 127
                                               for c in observed)):
            raise JournalError("INVALID OBSERVATION")
        timestamp = _now()
        conn = self._connect(True)
        try:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute("""UPDATE operations
                SET phase=?, updated_utc=?, observed_workspace=?
                WHERE id=? AND phase=?""", (new, timestamp, observed, operation_id, old))
            if updated.rowcount != 1:
                raise JournalError("STALE OR DUPLICATE OPERATION")
            conn.execute("""INSERT INTO transitions(operation_id,phase,at_utc)
                            VALUES (?,?,?)""", (operation_id, new, timestamp))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def mark_dispatching(self, operation_id):
        # Durable before any command: a crash is ALWAYS manual review, no retry.
        self._advance(operation_id, "prepared", "dispatching")

    def finish(self, operation_id, status, observed=None):
        if status not in OUTCOMES:
            raise JournalError("INVALID COMPLETION")
        self._advance(operation_id, "dispatching", status, observed)

    def get(self, operation_id):
        try:
            operation_id = str(uuid.UUID(operation_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise JournalError("INVALID OPERATION ID") from exc
        conn = self._connect(False)
        if conn is None:
            return None
        try:
            row = conn.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
            return self._view(row) if row is not None else None
        finally:
            conn.close()

    def pending(self):
        """Opening after reboot does NOT retry or mutate uncertain operations."""
        conn = self._connect(False)
        if conn is None:
            return []
        try:
            rows = conn.execute("""SELECT * FROM operations WHERE phase IN (?,?,?)
                ORDER BY created_utc DESC, id DESC LIMIT ?""",
                (*sorted(ACTIVE), MAX_ROWS)).fetchall()
            return [self._view(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _view(row):
        before = _clean_before(json.loads(row["before_json"]))
        return {"id": row["id"], "phase": row["phase"],
                "before": before,
                "created_utc": row["created_utc"],
                "updated_utc": row["updated_utc"],
                "observed_workspace": row["observed_workspace"],
                "requires_manual_review": row["phase"] in ACTIVE,
                "automatic_retry_allowed": False}
