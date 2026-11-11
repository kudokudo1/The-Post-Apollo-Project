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

from scripts.trash.archive_v2_capacity import (
    CapacityError, DEFAULT_DISK_QUOTA, MAX_DISK_QUOTA,
    MIN_DISK_QUOTA, capacity,
)
from scripts.trash.archive_v2_provenance import (
    ProvenanceError, RECEIPT_SCHEMA, create_receipt, verify_receipt,
)

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


def _private_file(path, allow_missing=False, require_private_mode=True):
    try:
        info = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return
        raise ArchiveError("ARCHIVE_FILE_MISSING")
    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
             and info.st_uid == os.geteuid()
             and (not require_private_mode or info.st_mode & 0o077 == 0),
             "ARCHIVE_FILE_UNSAFE")


class ArchiveStore:
    """A private durable copy store. Owner-specific adapters must validate bytes.

    The library is not a permission boundary for future owner integrations:
    a source writer must independently authorize and verify its own revisions.
    """

    def __init__(self, directory, payload_quota=DEFAULT_PAYLOAD_QUOTA,
                 disk_quota=DEFAULT_DISK_QUOTA):
        _require(isinstance(directory, (str, Path)), "INVALID_ARCHIVE_ROOT")
        self.root = Path(directory)
        _require(self.root.is_absolute()
                 and len(str(self.root)) <= 4096
                 and isinstance(payload_quota, int)
                 and not isinstance(payload_quota, bool)
                 and MAX_ITEM_BYTES <= payload_quota <= 2**40
                 and type(disk_quota) is int
                 and MIN_DISK_QUOTA <= disk_quota <= MAX_DISK_QUOTA,
                 "INVALID_ARCHIVE_CONFIG")
        self.payload_quota = payload_quota
        self.disk_quota = disk_quota
        self.path = self.root / DB_NAME
        self._check_root()
        _private_file(self.path, allow_missing=True)
        # SQLite creates/removes its rollback journal while concurrent writers
        # run. Keep its owner/type/link checks, but do not race SQLite's
        # temporary file mode; the parent directory is already private 0700.
        _private_file(self.root / (DB_NAME + "-journal"), allow_missing=True,
                      require_private_mode=False)
        created = False
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                             | getattr(os, "O_NOFOLLOW", 0), 0o600)
                os.close(fd)
                created = True
            except FileExistsError:
                _private_file(self.path)
            except OSError as exc:
                raise ArchiveError("ARCHIVE_CREATE_FAILED") from exc
        self._init()
        # Persist the newly created database directory entry as well as its pages.
        if created:
            try:
                fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY
                             | getattr(os, "O_NOFOLLOW", 0))
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError as exc:
                raise ArchiveError("ARCHIVE_DIRECTORY_SYNC_FAILED") from exc

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
        # SQLite creates/removes its rollback journal while concurrent writers
        # run. Keep its owner/type/link checks, but do not race SQLite's
        # temporary file mode; the parent directory is already private 0700.
        _private_file(self.root / (DB_NAME + "-journal"), allow_missing=True,
                      require_private_mode=False)
        # This store uses rollback journals, not WAL. Refuse unexpected
        # sidecars before SQLite can open them, including dangling symlinks.
        for extension in ("-wal", "-shm"):
            try:
                (self.root / (DB_NAME + extension)).lstat()
            except FileNotFoundError:
                continue
            raise ArchiveError("ARCHIVE_UNEXPECTED_SIDECAR")
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
                    # V2i is an additive, in-place migration: old rows
                    # default to 0 (no receipt) and are never retroactively
                    # stamped as having witnessed source provenance.
                    columns = {col[1] for col in
                               db.execute("PRAGMA table_info(snapshots)")}
                    if "provenance_required" not in columns:
                        db.execute("""ALTER TABLE snapshots ADD COLUMN
                            provenance_required INTEGER NOT NULL DEFAULT 0
                            CHECK(provenance_required IN (0,1))""")
                    db.execute("""CREATE TABLE IF NOT EXISTS snapshot_receipts (
                        snapshot_id TEXT PRIMARY KEY
                            REFERENCES snapshots(id),
                        owner_id TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        source_revision TEXT NOT NULL,
                        source_captured_ms INTEGER NOT NULL,
                        archived_ms INTEGER NOT NULL,
                        display_label TEXT NOT NULL,
                        payload_sha256 TEXT NOT NULL,
                        previous_receipt_sha256 TEXT NOT NULL,
                        receipt_sha256 TEXT NOT NULL UNIQUE,
                        receipt_schema TEXT NOT NULL
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

    def _capacity(self):
        try:
            return capacity(self.root, self.disk_quota)
        except CapacityError as exc:
            raise ArchiveError(str(exc)) from exc

    def save(self, owner_id, resource_id, source_revision, payload,
             display_label="", captured_ms=None):
        """Store a validated, source-provided copy; never read the source file."""
        _require(isinstance(owner_id, str) and owner_id in PILOT_OWNERS,
                 "OWNER_NOT_AUTHORIZED")
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
                # Per-connection SQLite max_page_count caps the main DB even
                # before our total DB+journal footprint check. Read-only
                # operations do not change this connection-level setting.
                page_size = db.execute("PRAGMA page_size").fetchone()[0]
                limit_pages = self.disk_quota // page_size
                if db.execute("PRAGMA page_count").fetchone()[0] > limit_pages:
                    raise ArchiveError("ARCHIVE_DISK_QUOTA")
                max_pages = db.execute(
                    "PRAGMA max_page_count=" + str(limit_pages)).fetchone()[0]
                _require(max_pages <= limit_pages, "ARCHIVE_DISK_QUOTA")
                db.execute("BEGIN IMMEDIATE")
                before = self._capacity()
                _require(before["chargedBytes"] < self.disk_quota,
                         "ARCHIVE_DISK_QUOTA")
                # Do not use the final bytes available to the whole host.
                # These are conservative preflight figures, not a reserved
                # filesystem quota against unrelated writers.
                _require(before["filesystemAvailableBytes"] >=
                         max(16 * 1024 * 1024, len(payload) * 2),
                         "ARCHIVE_FILESYSTEM_SPACE")
                bytes_now = db.execute(
                    "SELECT payload_bytes FROM archive_meta WHERE id=1"
                ).fetchone()
                _require(bytes_now is not None, "ARCHIVE_SCHEMA_UNAVAILABLE")
                _require(bytes_now[0] + len(payload) <= self.payload_quota,
                         "ARCHIVE_PAYLOAD_QUOTA")
                previous = db.execute("""SELECT r.receipt_sha256
                    FROM snapshot_receipts r JOIN snapshots s
                      ON s.id=r.snapshot_id
                    WHERE s.owner_id=? AND s.resource_id=?
                    ORDER BY s.rowid DESC LIMIT 1""",
                    (owner_id, resource_id)).fetchone()
                if previous is not None:
                    # Refuse chaining from corrupted local evidence.
                    ancestor = db.execute("""SELECT s.id,s.owner_id,s.resource_id,
                        s.source_revision,s.captured_ms,s.display_label,s.sha256,
                        s.provenance_required,
                        r.snapshot_id,r.owner_id,r.resource_id,r.source_revision,
                        r.source_captured_ms,r.archived_ms,r.display_label,
                        r.payload_sha256,r.previous_receipt_sha256,
                        r.receipt_sha256,r.receipt_schema
                        FROM snapshot_receipts r JOIN snapshots s
                          ON s.id=r.snapshot_id
                        WHERE r.receipt_sha256=?""", (previous[0],)).fetchone()
                    _require(ancestor is not None, "SNAPSHOT_PROVENANCE_INVALID")
                    try:
                        verify_receipt(ancestor[:8], ancestor[8:])
                    except ProvenanceError as exc:
                        raise ArchiveError(str(exc)) from exc
                archived_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
                receipt = create_receipt(
                    sid, owner_id, resource_id, source_revision, captured_ms,
                    archived_ms, display_label, digest,
                    previous[0] if previous else "")
                db.execute("""INSERT INTO snapshots
                    (id,owner_id,resource_id,source_revision,captured_ms,
                     display_label,sha256,payload,provenance_required)
                    VALUES(?,?,?,?,?,?,?,?,1)""",
                    (sid, owner_id, resource_id, source_revision, captured_ms,
                     display_label, digest, payload))
                db.execute("""INSERT INTO snapshot_receipts
                    (snapshot_id,owner_id,resource_id,source_revision,
                     source_captured_ms,archived_ms,display_label,
                     payload_sha256,previous_receipt_sha256,
                     receipt_sha256,receipt_schema)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (sid,owner_id,resource_id,source_revision,captured_ms,
                     archived_ms,display_label,digest,
                     receipt["previousReceiptHash"],receipt["receiptSha256"],
                     RECEIPT_SCHEMA))
                db.execute("""UPDATE archive_meta
                    SET revision=revision+1,payload_bytes=payload_bytes+?
                    WHERE id=1""", (len(payload),))
                # Accounting includes the currently present rollback journal,
                # not just payload length. Refuse and roll back before commit
                # if this transaction has exceeded our logical/allocated
                # footprint budget.
                _require(self._capacity()["chargedBytes"] <= self.disk_quota,
                         "ARCHIVE_DISK_QUOTA")
                db.commit()
            except sqlite3.IntegrityError as exc:
                db.rollback()
                raise ArchiveError("SNAPSHOT_ALREADY_EXISTS") from exc
            except sqlite3.DatabaseError as exc:
                db.rollback()
                code = getattr(exc, "sqlite_errorcode", None)
                if code == sqlite3.SQLITE_FULL:
                    raise ArchiveError("ARCHIVE_DISK_QUOTA") from exc
                raise ArchiveError("ARCHIVE_WRITE_FAILED") from exc
            except BaseException:
                db.rollback()
                raise
        return {"id": sid, "sha256": digest, "size": len(payload),
                "ownerId": owner_id, "resourceId": resource_id,
                "sourceRevision": source_revision,
                "provenance": {"state": "RECEIPT_MATCHED",
                               "sourceCapturedAtMs": captured_ms,
                               "archivedAtMs": archived_ms,
                               "receiptSha256": receipt["receiptSha256"],
                               "previousReceiptHash": receipt["previousReceiptHash"],
                               "authentication": "UNSIGNED_LOCAL"}}

    def status(self):
        with closing(self._connect()) as db:
            revision, size = db.execute(
                "SELECT revision,payload_bytes FROM archive_meta WHERE id=1"
            ).fetchone()
            count = db.execute("SELECT count(*) FROM snapshots").fetchone()[0]
            return {"schema": SCHEMA, "revision": revision, "total": count,
                    "payloadBytes": size, "payloadQuota": self.payload_quota,
                    "capacity": self._capacity()}

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
            row = db.execute("""SELECT s.id,s.owner_id,s.resource_id,
                s.source_revision,s.captured_ms,s.display_label,s.sha256,
                s.provenance_required,s.payload,
                r.snapshot_id,r.owner_id,r.resource_id,r.source_revision,
                r.source_captured_ms,r.archived_ms,r.display_label,
                r.payload_sha256,r.previous_receipt_sha256,
                r.receipt_sha256,r.receipt_schema
                FROM snapshots s LEFT JOIN snapshot_receipts r
                  ON r.snapshot_id=s.id WHERE s.id=?""",
                (snapshot_id,)).fetchone()
        _require(row is not None, "SNAPSHOT_NOT_FOUND")
        try:
            verify_receipt(row[:8], row[9:])
        except ProvenanceError as exc:
            raise ArchiveError(str(exc)) from exc
        data, digest = row[8], row[6]
        _require(hashlib.sha256(data).hexdigest() == digest,
                 "SNAPSHOT_INTEGRITY_FAILED")
        return bytes(data)

    def verify(self):
        """Full read-only payload audit; deliberately O(n). No auto-repair."""
        with closing(self._connect()) as db:
            check = db.execute("PRAGMA quick_check").fetchone()
            _require(check == ("ok",), "ARCHIVE_DATABASE_CORRUPT")
            count, total = 0, 0
            for record in db.execute("""SELECT s.id,s.owner_id,
                s.resource_id,s.source_revision,s.captured_ms,s.display_label,
                s.sha256,s.provenance_required,s.payload,
                r.snapshot_id,r.owner_id,r.resource_id,r.source_revision,
                r.source_captured_ms,r.archived_ms,r.display_label,
                r.payload_sha256,r.previous_receipt_sha256,
                r.receipt_sha256,r.receipt_schema
                FROM snapshots s LEFT JOIN snapshot_receipts r
                  ON r.snapshot_id=s.id"""):
                try:
                    verify_receipt(record[:8], record[9:])
                except ProvenanceError as exc:
                    raise ArchiveError(str(exc)) from exc
                _require(hashlib.sha256(record[8]).hexdigest() == record[6],
                         "SNAPSHOT_INTEGRITY_FAILED")
                count += 1
                total += len(record[8])
            row = db.execute(
                "SELECT payload_bytes FROM archive_meta WHERE id=1"
            ).fetchone()
            _require(row is not None and row[0] == total,
                     "ARCHIVE_ACCOUNTING_MISMATCH")
            return {"verified": True, "items": count, "payloadBytes": total}
