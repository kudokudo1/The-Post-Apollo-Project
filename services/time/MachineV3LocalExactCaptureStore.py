"""TimeW Scope A: optional LOCAL-ONLY exact fractional capture store.

Separate, dormant v3 SQLite file for ordinary, caller-supplied observations.
Nothing here can select a SwayPX surface, mint C5 SPENT, issue a command,
authenticate an observation, or settle a Restore. Existing V1/V2 stores
and their integer-only journal are deliberately untouched.

This local file is user-controlled data, NOT a protected consent ledger.
No automatic migration, import-time writes, CLI, QML hook, or native runner.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sqlite3
import stat
import uuid
from urllib.parse import quote

from MachineV2ExactLogicalGeometry import (
    ExactGeometryRefused, ExactLogicalRect, PHASE_CURRENT, VALUE_VERSION,
    read_value,
)

DB_NAME = "v3-exact-local-captures.db"
SCHEMA_VERSION = 3  # Local data schema, NEVER a signed/native wire revision.
TABLE = "exact_captures"
MAX_RECORDS = 512
HEX = re.compile(r"[0-9a-f]{16}\Z", re.ASCII)
COLUMNS = (
    "id", "checkpoint_id", "window_key", "app_id", "output_id",
    "workspace_id", "value_version", "phase", "x_bits", "y_bits",
    "width_bits", "height_bits", "saved_at_utc",
)


class LocalCaptureRefused(ValueError):
    pass


def _refuse():
    raise LocalCaptureRefused("TIMEW LOCAL FRACTIONAL CAPTURE REFUSED")


def suggested_path():
    """Pure path suggestion; never creates a file or directory."""
    data = os.environ.get("XDG_DATA_HOME", "").strip()
    base = Path(data).expanduser() if data else Path.home() / ".local/share"
    return base / "post-apollo" / "machine" / DB_NAME


def _id(value, *, version=None):
    if type(value) is not str:
        _refuse()
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        _refuse()
    if str(parsed) != value or (version is not None and parsed.version != version):
        _refuse()
    return value


def _text(value):
    if (type(value) is not str or not 1 <= len(value) <= 128
            or any(not 32 <= ord(c) <= 126 for c in value)):
        _refuse()
    return value


def _capture_value(value):
    if type(value) is not ExactLogicalRect:
        _refuse()
    try:
        read_value(value)
    except ExactGeometryRefused:
        _refuse()
    if value.version != VALUE_VERSION or value.phase != PHASE_CURRENT:
        _refuse()
    return tuple(format(bits, "016x") for bits in (
        value.x_bits, value.y_bits, value.width_bits, value.height_bits))


def _safe_dir(path, *, create):
    if create:
        try:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError:
            _refuse()
    try:
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) & 0o077):
            _refuse()
    except OSError:
        _refuse()


def _safe_file(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        _refuse()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077 or info.st_nlink != 1):
        _refuse()
    return True


def _ensure_file(path):
    if _safe_file(path):
        return
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        if not _safe_file(path):
            _refuse()
        return
    except OSError:
        _refuse()
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _table_schema(conn):
    rows = conn.execute("PRAGMA table_info(exact_captures)").fetchall()
    if tuple(row["name"] for row in rows) != COLUMNS:
        _refuse()
    names = conn.execute(
        "SELECT name, type FROM sqlite_master WHERE name=?",
        (TABLE,)
    ).fetchall()
    if len(names) != 1 or names[0]["type"] != "table":
        _refuse()


def _as_entry(row):
    if tuple(row.keys()) != COLUMNS:
        _refuse()
    identifier = _id(row["id"], version=4)
    checkpoint = _id(row["checkpoint_id"], version=4)
    window = _id(row["window_key"])
    app = _text(row["app_id"])
    output = _text(row["output_id"])
    workspace = _text(row["workspace_id"])
    if (type(row["value_version"]) is not int
            or row["value_version"] != VALUE_VERSION
            or type(row["phase"]) is not int
            or row["phase"] != PHASE_CURRENT):
        _refuse()
    bits = []
    for name in ("x_bits", "y_bits", "width_bits", "height_bits"):
        item = row[name]
        if type(item) is not str or HEX.fullmatch(item) is None:
            _refuse()
        bits.append(int(item, 16))
    value = ExactLogicalRect(VALUE_VERSION, PHASE_CURRENT, *bits)
    try:
        read_value(value)
    except ExactGeometryRefused:
        _refuse()
    stamp = row["saved_at_utc"]
    if type(stamp) is not str or not stamp.endswith("+00:00"):
        _refuse()
    try:
        parsed = datetime.fromisoformat(stamp)
    except ValueError:
        _refuse()
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        _refuse()
    return {
        "id": identifier, "checkpoint_id": checkpoint,
        "window_key": window, "app_id": app,
        "output_id": output, "workspace_id": workspace,
        "value": value, "saved_at_utc": stamp,
        "local_capture_only": True, "source_authenticated": False,
        "operator_selection_verified": False,
        "production_restore_allowed": False, "c5_spent_verified": False,
        "terminal_receipt_verified": False, "automatic_retry_allowed": False,
        "automatic_undo_allowed": False, "safe_actions": [],
    }


class LocalExactCaptureStore:
    """An explicit-path local data store. No trusted authority is returned."""

    def __init__(self, path):
        if type(path) not in (str, Path):
            _refuse()
        self.path = Path(path).expanduser()
        if (not self.path.is_absolute() or self.path.name != DB_NAME
                or self.path.parent.name != "machine"
                or self.path.parent.parent.name != "post-apollo"):
            _refuse()

    def _connect(self, writable):
        if not writable and not self.path.exists() and not self.path.is_symlink():
            return None
        conn = None
        try:
            _safe_dir(self.path.parent.parent, create=writable)
            _safe_dir(self.path.parent, create=writable)
            if writable:
                _ensure_file(self.path)
            elif not _safe_file(self.path):
                return None
            conn = (sqlite3.connect(str(self.path), timeout=5.0)
                    if writable else sqlite3.connect(
                        "file:" + quote(str(self.path), safe="/") + "?mode=ro",
                        timeout=5.0, uri=True))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA trusted_schema=OFF")
            conn.execute("PRAGMA synchronous=FULL")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version not in ((0, SCHEMA_VERSION) if writable else (SCHEMA_VERSION,)):
                _refuse()
            if writable:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    conn.execute("""CREATE TABLE IF NOT EXISTS exact_captures (
                        id TEXT PRIMARY KEY,
                        checkpoint_id TEXT NOT NULL,
                        window_key TEXT NOT NULL,
                        app_id TEXT NOT NULL,
                        output_id TEXT NOT NULL,
                        workspace_id TEXT NOT NULL,
                        value_version INTEGER NOT NULL CHECK(value_version=1),
                        phase INTEGER NOT NULL CHECK(phase=2),
                        x_bits TEXT NOT NULL,
                        y_bits TEXT NOT NULL,
                        width_bits TEXT NOT NULL,
                        height_bits TEXT NOT NULL,
                        saved_at_utc TEXT NOT NULL,
                        UNIQUE(checkpoint_id,window_key)
                    )""")
                    conn.execute("PRAGMA user_version=3")
                    _table_schema(conn)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
            else:
                _table_schema(conn)
                conn.execute("PRAGMA query_only=ON")
            return conn
        except (sqlite3.Error, OSError, TypeError, ValueError, LocalCaptureRefused):
            if conn is not None:
                conn.close()
            _refuse()

    def save(self, *, checkpoint_id, window_key, app_id, output_id,
             workspace_id, value):
        """Explicit caller-supplied CURRENT snapshot; NO capture or Restore."""
        checkpoint = _id(checkpoint_id, version=4)
        window = _id(window_key)
        app = _text(app_id)
        output = _text(output_id)
        workspace = _text(workspace_id)
        bits = _capture_value(value)
        capture_id = str(uuid.uuid4())
        stamp = datetime.now(timezone.utc).isoformat()
        conn = self._connect(True)
        try:
            conn.execute("BEGIN IMMEDIATE")
            count = conn.execute("SELECT COUNT(*) FROM exact_captures").fetchone()[0]
            if count >= MAX_RECORDS:
                _refuse()
            conn.execute("""INSERT INTO exact_captures
                (id,checkpoint_id,window_key,app_id,output_id,workspace_id,
                 value_version,phase,x_bits,y_bits,width_bits,height_bits,saved_at_utc)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (capture_id, checkpoint, window, app, output, workspace,
                 VALUE_VERSION, PHASE_CURRENT, *bits, stamp))
            conn.commit()
            return capture_id
        except (sqlite3.Error, LocalCaptureRefused):
            conn.rollback()
            _refuse()
        finally:
            conn.close()

    def get(self, capture_id):
        identifier = _id(capture_id, version=4)
        conn = self._connect(False)
        if conn is None:
            return None
        try:
            row = conn.execute(
                "SELECT * FROM exact_captures WHERE id=?", (identifier,)
            ).fetchone()
            return None if row is None else _as_entry(row)
        except (sqlite3.Error, TypeError, ValueError, LocalCaptureRefused):
            _refuse()
        finally:
            conn.close()

    def for_checkpoint(self, checkpoint_id):
        checkpoint = _id(checkpoint_id, version=4)
        conn = self._connect(False)
        if conn is None:
            return []
        try:
            rows = conn.execute(
                """SELECT * FROM exact_captures WHERE checkpoint_id=?
                ORDER BY saved_at_utc ASC,id ASC LIMIT ?""",
                (checkpoint, MAX_RECORDS + 1)
            ).fetchall()
            if len(rows) > MAX_RECORDS:
                _refuse()
            return [_as_entry(row) for row in rows]
        except (sqlite3.Error, TypeError, ValueError, LocalCaptureRefused):
            _refuse()
        finally:
            conn.close()
