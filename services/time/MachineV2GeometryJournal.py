"""MACHINE V2: durable, owner-private geometry-operation journal.

A narrow storage seam for the disposable floating pilot only. This module has
NO Sway runner, no CLI, no authorization, no retry/undo and no background task.
A saved window key and a transient con_id are identifiers, not proof of
historical Brave window identity or an authenticated operator decision.

Any prepared, dispatching or uncertain operation stays a manual-review hold
after process death. A completed checkpoint/window pair cannot be replayed
with the same journal: a new authorized generation requires a future design.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid
from urllib.parse import quote

DB_NAME = "v2-geometry-operations.db"
SCHEMA_VERSION = 1
MAX_ROWS = 128
MAX_SUMMARY_BYTES = 4096
ACTIVE = frozenset(("prepared", "dispatching", "uncertain_requires_review"))
TERMINAL = frozenset(("verified_fixture_placement",))
PHASES = ACTIVE | TERMINAL
FIELDS = frozenset((
    "checkpoint_id", "window_key", "app_id", "live_con_id",
    "before_rect", "target_rect",
))
RECT_FIELDS = frozenset(("x", "y", "width", "height"))


class GeometryJournalError(ValueError):
    pass


def refuse():
    raise GeometryJournalError("GEOMETRY JOURNAL REFUSED")


def suggested_path():
    """Suggested private ledger location, separate from the M1 move journal."""
    data = os.environ.get("XDG_DATA_HOME", "").strip()
    base = Path(data).expanduser() if data else Path.home() / ".local/share"
    return base / "post-apollo" / "machine" / DB_NAME


def _uuid(value, *, version=None):
    if not isinstance(value, str):
        refuse()
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        refuse()
    if str(parsed) != value or (version is not None and parsed.version != version):
        refuse()
    return value


def _rect(value):
    if not isinstance(value, dict) or set(value) != RECT_FIELDS:
        refuse()
    result = {}
    for k in ("x", "y", "width", "height"):
        n = value[k]
        if (type(n) is not int or n > 100000
                or n < (-100000 if k in ("x", "y") else 1)):
            refuse()
        result[k] = n
    return result


def _summary(value):
    if not isinstance(value, dict) or set(value) != FIELDS:
        refuse()
    cid = _uuid(value["checkpoint_id"], version=4)
    key = _uuid(value["window_key"])
    con_id = value["live_con_id"]
    app = value["app_id"]
    if (type(con_id) is not int or not 0 < con_id <= 9007199254740991
            or not isinstance(app, str) or not 1 <= len(app) <= 128
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in app)):
        refuse()
    before, target = _rect(value["before_rect"]), _rect(value["target_rect"])
    if before == target:
        refuse()
    result = {
        "checkpoint_id": cid, "window_key": key, "app_id": app,
        "live_con_id": con_id, "before_rect": before, "target_rect": target,
    }
    if len(json.dumps(result, separators=(",", ":"), ensure_ascii=False).encode()) > MAX_SUMMARY_BYTES:
        refuse()
    return result


def _timestamp():
    return datetime.now(timezone.utc).isoformat()


def _safe_directory(path, *, create):
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or not path.is_dir():
        refuse()
    info = path.stat()
    if (info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        refuse()


def _safe_file(path):
    if path.is_symlink():
        refuse()
    if not path.exists():
        return False
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077 or info.st_nlink != 1):
        refuse()
    return True


def _create_file(path):
    if _safe_file(path):
        return
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        _safe_file(path)
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    # Persist the directory entry before the first SQLite transaction.
    dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


class GeometryJournal:
    """Explicit-path journal, with read-only inspection and deny-by-default IO."""

    def __init__(self, path):
        if not isinstance(path, (str, Path)):
            refuse()
        self.path = Path(path).expanduser()
        if (not self.path.is_absolute() or self.path.name != DB_NAME
                or self.path.parent.name != "machine"
                or self.path.parent.parent.name != "post-apollo"):
            refuse()

    def _connect(self, writable):
        """Return None for absent read-only journal without creating anything."""
        if not writable and not self.path.exists() and not self.path.is_symlink():
            return None
        connection = None
        try:
            _safe_directory(self.path.parent, create=writable)
            if writable:
                _create_file(self.path)
            elif not _safe_file(self.path):
                return None
            connection = (sqlite3.connect(str(self.path), timeout=5.0)
                          if writable else sqlite3.connect(
                              "file:" + quote(str(self.path), safe="/") + "?mode=ro",
                              timeout=5.0, uri=True))
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in ((0, SCHEMA_VERSION) if writable else (SCHEMA_VERSION,)):
                refuse()
            if writable:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
                try:
                    connection.execute("""CREATE TABLE IF NOT EXISTS operations (
                        id TEXT PRIMARY KEY,
                        checkpoint_id TEXT NOT NULL,
                        window_key TEXT NOT NULL,
                        phase TEXT NOT NULL,
                        summary_json TEXT NOT NULL,
                        created_utc TEXT NOT NULL,
                        updated_utc TEXT NOT NULL,
                        CHECK (phase IN (
                          'prepared','dispatching','uncertain_requires_review',
                          'verified_fixture_placement')),
                        UNIQUE (checkpoint_id, window_key)
                    )""")
                    connection.execute("""CREATE TABLE IF NOT EXISTS transitions (
                        seq INTEGER PRIMARY KEY AUTOINCREMENT,
                        operation_id TEXT NOT NULL,
                        phase TEXT NOT NULL,
                        at_utc TEXT NOT NULL,
                        FOREIGN KEY(operation_id) REFERENCES operations(id)
                    )""")
                    connection.execute("PRAGMA user_version=1")
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
            else:
                connection.execute("PRAGMA query_only=ON")
            return connection
        except (OSError, sqlite3.Error, ValueError, TypeError, GeometryJournalError):
            if connection is not None:
                connection.close()
            refuse()

    def begin(self, summary):
        clean = _summary(summary)
        payload = json.dumps(clean, separators=(",", ":"), ensure_ascii=False)
        operation_id = str(uuid.uuid4())
        stamp = _timestamp()
        con = self._connect(True)
        try:
            con.execute("BEGIN IMMEDIATE")
            busy = con.execute(
                "SELECT COUNT(*) FROM operations WHERE phase IN (?,?,?)",
                tuple(sorted(ACTIVE))).fetchone()[0]
            prior = con.execute("""SELECT COUNT(*) FROM operations
                WHERE checkpoint_id=? AND window_key=?""",
                (clean["checkpoint_id"], clean["window_key"])).fetchone()[0]
            if busy or prior:
                refuse()
            con.execute("""INSERT INTO operations
                (id,checkpoint_id,window_key,phase,summary_json,created_utc,updated_utc)
                VALUES (?,?,?,'prepared',?,?,?)""",
                (operation_id,clean["checkpoint_id"],clean["window_key"],
                 payload,stamp,stamp))
            con.execute("""INSERT INTO transitions (operation_id,phase,at_utc)
                VALUES (?,'prepared',?)""", (operation_id,stamp))
            con.commit()
            return operation_id
        except (sqlite3.Error, ValueError, GeometryJournalError):
            con.rollback()
            refuse()
        finally:
            con.close()

    def _advance(self, operation_id, before, after):
        _uuid(operation_id, version=4)
        stamp = _timestamp()
        con = self._connect(True)
        try:
            con.execute("BEGIN IMMEDIATE")
            outcome = con.execute("""UPDATE operations
                SET phase=?,updated_utc=? WHERE id=? AND phase=?""",
                (after,stamp,operation_id,before))
            if outcome.rowcount != 1:
                refuse()
            con.execute("""INSERT INTO transitions (operation_id,phase,at_utc)
                VALUES (?,?,?)""", (operation_id,after,stamp))
            con.commit()
        except (sqlite3.Error, ValueError, GeometryJournalError):
            con.rollback()
            refuse()
        finally:
            con.close()

    def dispatching(self, operation_id):
        # A durable DISPATCHING receipt must exist before either Sway command.
        self._advance(operation_id, "prepared", "dispatching")

    def finish(self, operation_id, status):
        if status not in TERMINAL | frozenset(("uncertain_requires_review",)):
            refuse()
        self._advance(operation_id, "dispatching", status)

    @staticmethod
    def _view(row):
        clean = _summary(json.loads(row["summary_json"]))
        if (row["checkpoint_id"] != clean["checkpoint_id"]
                or row["window_key"] != clean["window_key"]
                or row["phase"] not in PHASES):
            refuse()
        return {
            "id": _uuid(row["id"], version=4),
            "phase": row["phase"], "summary": clean,
            "created_utc": row["created_utc"], "updated_utc": row["updated_utc"],
            "manual_review_required": row["phase"] in ACTIVE,
            "production_restore_allowed": False,
            "persistent_identity_verified": False,
            "automatic_retry_allowed": False,
            "automatic_undo_allowed": False,
        }

    def get(self, operation_id):
        _uuid(operation_id, version=4)
        con = self._connect(False)
        if con is None:
            return None
        try:
            record = con.execute("SELECT * FROM operations WHERE id=?",
                                 (operation_id,)).fetchone()
            return None if record is None else self._view(record)
        except (sqlite3.Error, TypeError, ValueError, GeometryJournalError):
            refuse()
        finally:
            con.close()

    def pending(self):
        """Opening after restart never performs a compositor command or retry."""
        con = self._connect(False)
        if con is None:
            return []
        try:
            rows = con.execute("""SELECT * FROM operations WHERE phase IN (?,?,?)
                ORDER BY created_utc DESC,id DESC LIMIT ?""",
                (*sorted(ACTIVE), MAX_ROWS)).fetchall()
            return [self._view(row) for row in rows]
        except (sqlite3.Error, TypeError, ValueError, GeometryJournalError):
            refuse()
        finally:
            con.close()
