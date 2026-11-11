#!/usr/bin/env python3
"""Trash++ V2a: opt-in, owner-scoped immutable snapshot storage.

Not wired into the Trash widget. No CLI, source-file readers, source deletion,
Trash, Restore, Burn, migration, or protected-owner permissions.
SQLite keeps bytes and metadata in one durable transaction; the legacy V1
managed-copy JSON file is deliberately untouched.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
from uuid import uuid4

DB_NAME = "trashpp-archive-v2.sqlite3"
SCHEMA = "post-apollo.trash-archive.v2a"
# Only disposable, independently supplied copies may use this pilot API.
PILOT_OWNERS = frozenset(("demo-scrape", "weather-events"))
MAX_ITEM_BYTES = 8 * 1024 * 1024
DEFAULT_PAYLOAD_QUOTA = 512 * 1024 * 1024
MAX_PAGE_SIZE = 100
MAX_TIME_MS = 9999999999999
IDENTIFIER = re.compile(r"^[a-zA-Z0-9._:-]{1,128}$")
HEX_ID = re.compile(r"^[0-9a-f]{32}$")


class ArchiveError(Exception):
    """Safe error code, no user paths or private payloads."""


def _require(condition, error):
    if not condition:
        raise ArchiveError(error)


def _identity(value):
    _require(isinstance(value, str) and IDENTIFIER.fullmatch(value),
             "INVALID_RESOURCE_ID")
    return value


def _private_file(path, allow_missing=False):
    try:
        info = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return
        raise ArchiveError("ARCHIVE_FILE_MISSING")
    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
             and info.st_uid == os.geteuid()
             and info.st_mode & 0o077 == 0, "ARCHIVE_FILE_UNSAFE")


class ArchiveStore:
    """A private durable copy store. Owner-specific adapters must validate bytes.

    The library is not a permission boundary for future owner integrations:
    a source writer must independently authorize and verify its own revisions.
    """

    def __init__(self, directory, payload_quota=DEFAULT_PAYLOAD_QUOTA):
        _require(isinstance(directory, (str, Path)), "INVALID_ARCHIVE_ROOT")
        self.root = Path(directory)
        _require(self.root.is_absolute()
                 and len(str(self.root)) <= 4096
                 and isinstance(payload_quota, int)
                 and not isinstance(payload_quota, bool)
                 and MAX_ITEM_BYTES <= payload_quota <= 2**40,
                 "INVALID_ARCHIVE_CONFIG")
        self.payload_quota = payload_quota
        self.path = self.root / DB_NAME
        self._check_root()
        _private_file(self.path, allow_missing=True)
        _private_file(self.root / (DB_NAME + "-journal"), allow_missing=True)
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                             | getattr(os, "O_NOFOLLOW", 0), 0o600)
                os.close(fd)
            except FileExistsError:
                _private_file(self.path)
            except OSError as exc:
                raise ArchiveError("ARCHIVE_CREATE_FAILED") from exc
        self._init()

    def _check_root(self):
        try:
            info = self.root.lstat()
        except OSError as exc:
            raise ArchiveError("ARCHIVE_ROOT_UNAVAILABLE") from exc
        _require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                 and info.st_mode & 0o077 == 0, "ARCHIVE_ROOT_UNSAFE")

    def _connect(self):
        self._check_root()
        _private_file(self.path)
        _private_file(self.root / (DB_NAME + "-journal"), allow_missing=True)
        try:
            db = sqlite3.connect(str(self.path), timeout=10)
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA foreign_keys=ON")
            return db
        except sqlite3.DatabaseError as exc:
            raise ArchiveError("ARCHIVE_DATABASE_UNAVAILABLE") from exc

    def _init(self):
        with closing(self._connect()) as db:
            try:
                with db:
                    db.execute("""CREATE TABLE IF NOT EXISTS archive_meta (
                        id INTEGER PRIMARY KEY CHECK(id=1),
                        schema_id TEXT NOT NULL,
                        revision INTEGER NOT NULL CHECK(revision>=0),
                        payload_bytes INTEGER NOT NULL CHECK(payload_bytes>=0)
                    )""")
                    db.execute("""CREATE TABLE IF NOT EXISTS snapshots (
                        id TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        source_revision TEXT NOT NULL,
                        captured_ms INTEGER NOT NULL,
                        display_label TEXT NOT NULL,
                        sha256 TEXT NOT NULL,
                        payload BLOB NOT NULL,
                        UNIQUE(owner_id,resource_id,source_revision)
                    )""")
                    db.execute("""CREATE INDEX IF NOT EXISTS
                        idx_archive_page ON snapshots(captured_ms DESC,id DESC)""")
                    db.execute("""INSERT OR IGNORE INTO archive_meta
                        (id,schema_id,revision,payload_bytes)
                        VALUES(1,?,0,0)""", (SCHEMA,))
                    meta = db.execute(
                        "SELECT schema_id,payload_bytes FROM archive_meta WHERE id=1"
                    ).fetchone()
                    _require(meta is not None and meta[0] == SCHEMA,
                             "ARCHIVE_VERSION_UNSUPPORTED")
            except sqlite3.DatabaseError as exc:
                raise ArchiveError("ARCHIVE_SCHEMA_UNAVAILABLE") from exc

    def save(self, owner_id, resource_id, source_revision, payload,
             display_label="", captured_ms=None):
        """Store a validated, source-provided copy; never read the source file."""
        _require(owner_id in PILOT_OWNERS, "OWNER_NOT_AUTHORIZED")
        _identity(resource_id)
        _identity(source_revision)
        _require(type(payload) is bytes and 0 < len(payload) <= MAX_ITEM_BYTES,
                 "INVALID_SNAPSHOT_SIZE")
        _require(isinstance(display_label, str)
                 and len(display_label) <= 120
                 and all(c.isprintable() for c in display_label),
                 "INVALID_DISPLAY_LABEL")
        if captured_ms is None:
            captured_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        _require(type(captured_ms) is int and 1 <= captured_ms <= MAX_TIME_MS,
                 "INVALID_CAPTURE_TIME")
        digest = hashlib.sha256(payload).hexdigest()
        sid = uuid4().hex
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                bytes_now = db.execute(
                    "SELECT payload_bytes FROM archive_meta WHERE id=1"
                ).fetchone()
                _require(bytes_now is not None, "ARCHIVE_SCHEMA_UNAVAILABLE")
                _require(bytes_now[0] + len(payload) <= self.payload_quota,
                         "ARCHIVE_PAYLOAD_QUOTA")
                db.execute("""INSERT INTO snapshots
                    (id,owner_id,resource_id,source_revision,captured_ms,
                     display_label,sha256,payload)
                    VALUES(?,?,?,?,?,?,?,?)""",
                    (sid, owner_id, resource_id, source_revision, captured_ms,
                     display_label, digest, payload))
                db.execute("""UPDATE archive_meta
                    SET revision=revision+1,payload_bytes=payload_bytes+?
                    WHERE id=1""", (len(payload),))
                db.commit()
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise ArchiveError("SNAPSHOT_ALREADY_EXISTS") from exc
            except sqlite3.DatabaseError as exc:
                db.rollback()
                raise ArchiveError("ARCHIVE_WRITE_FAILED") from exc
            except BaseException:
                db.rollback()
                raise
        return {"id": sid, "sha256": digest, "size": len(payload),
                "ownerId": owner_id, "resourceId": resource_id,
                "sourceRevision": source_revision}

    def status(self):
        with closing(self._connect()) as db:
            revision, size = db.execute(
                "SELECT revision,payload_bytes FROM archive_meta WHERE id=1"
            ).fetchone()
            count = db.execute("SELECT count(*) FROM snapshots").fetchone()[0]
            return {"schema": SCHEMA, "revision": revision, "total": count,
                    "payloadBytes": size, "payloadQuota": self.payload_quota}

    def list_page(self, limit=50, cursor=None):
        _require(type(limit) is int and 1 <= limit <= MAX_PAGE_SIZE,
                 "INVALID_PAGE_SIZE")
        bounds = ()
        where = ""
        if cursor is not None:
            _require(isinstance(cursor, str), "INVALID_PAGE_CURSOR")
            split = cursor.split(":", 1)
            _require(len(split) == 2 and split[0].isdigit()
                     and HEX_ID.fullmatch(split[1]) is not None,
                     "INVALID_PAGE_CURSOR")
            ms = int(split[0])
            _require(1 <= ms <= MAX_TIME_MS, "INVALID_PAGE_CURSOR")
            where = "WHERE (captured_ms,id) < (?,?)"
            bounds = (ms, split[1])
        with closing(self._connect()) as db:
            rows = db.execute(
                "SELECT id,owner_id,resource_id,source_revision,captured_ms,"
                "display_label,sha256,length(payload) FROM snapshots "
                + where + " ORDER BY captured_ms DESC,id DESC LIMIT ?",
                bounds + (limit + 1,)
            ).fetchall()
        more = len(rows) > limit
        selected = rows[:limit]
        fields = ("id", "ownerId", "resourceId", "sourceRevision",
                  "capturedAtMs", "displayLabel", "sha256", "size")
        items = [dict(zip(fields, row)) for row in selected]
        next_cursor = (f"{selected[-1][4]}:{selected[-1][0]}"
                       if more and selected else None)
        return {"items": items, "hasMore": more, "nextCursor": next_cursor}

    def read_verified(self, snapshot_id):
        _require(isinstance(snapshot_id, str)
                 and HEX_ID.fullmatch(snapshot_id) is not None,
                 "INVALID_SNAPSHOT_ID")
        with closing(self._connect()) as db:
            row = db.execute("SELECT payload,sha256 FROM snapshots WHERE id=?",
                             (snapshot_id,)).fetchone()
        _require(row is not None, "SNAPSHOT_NOT_FOUND")
        data, digest = row
        _require(hashlib.sha256(data).hexdigest() == digest,
                 "SNAPSHOT_INTEGRITY_FAILED")
        return bytes(data)

    def verify(self):
        """Full read-only payload audit; deliberately O(n). No auto-repair."""
        with closing(self._connect()) as db:
            check = db.execute("PRAGMA quick_check").fetchone()
            _require(check == ("ok",), "ARCHIVE_DATABASE_CORRUPT")
            count, total = 0, 0
            for data, digest in db.execute("SELECT payload,sha256 FROM snapshots"):
                _require(hashlib.sha256(data).hexdigest() == digest,
                         "SNAPSHOT_INTEGRITY_FAILED")
                count += 1
                total += len(data)
            row = db.execute(
                "SELECT payload_bytes FROM archive_meta WHERE id=1"
            ).fetchone()
            _require(row is not None and row[0] == total,
                     "ARCHIVE_ACCOUNTING_MISMATCH")
            return {"verified": True, "items": count, "payloadBytes": total}
