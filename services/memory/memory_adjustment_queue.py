"""M1c.3b: unprivileged durable intent store; no execution or readiness authority.

The caller supplies the database path and observed identity. These are claims
of intent, not trusted host evidence. No service starts or polls in this slice.
"""
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid


class QueueError(Exception):
    """Invalid request, conflict, or unavailable/corrupt queue."""


STATES = {"QUEUED", "CANCELLED", "REPLACED", "EXPIRED"}
GIB_KIB = 1048576
MAX_INT = 2**63 - 1
FIELDS = {"id", "allocation", "target_gib", "source", "actual_kib",
          "requested_at", "expires_at", "changed_at", "state",
          "authorization_mode", "replaced_by"}


def _int(value, low=0, high=MAX_INT):
    if type(value) is not int or not low <= value <= high:
        raise QueueError("INVALID_INTEGER")
    return value


def _uuid(value):
    try:
        if type(value) is not str or str(uuid.UUID(value)) != value:
            raise ValueError()
    except (ValueError, AttributeError, TypeError):
        raise QueueError("INVALID_IDENTITY") from None
    return value


def _source(value):
    if type(value) is not dict or set(value) != {"boot_id", "base", "extension"}:
        raise QueueError("INVALID_SOURCE")
    _uuid(value["boot_id"])
    total = 0
    identities = set()
    for key in ("base", "extension"):
        row = value[key]
        if row is None:
            continue
        if type(row) is not dict or set(row) != {"device", "inode", "size_kib"}:
            raise QueueError("INVALID_SOURCE")
        identity = (_int(row["device"]), _int(row["inode"], 1))
        if identity in identities:
            raise QueueError("DUPLICATE_SOURCE")
        identities.add(identity)
        total += _int(row["size_kib"], 1)
    return _int(total)


def _validate(record):
    if type(record) is not dict or set(record) != FIELDS:
        raise QueueError("INVALID_RECORD")
    _uuid(record["id"])
    if record["allocation"] != "managed-nvme" or record["authorization_mode"] != "fresh-explicit":
        raise QueueError("INVALID_SCOPE")
    if _int(record["target_gib"], 0, 64) % 4:
        raise QueueError("INVALID_TARGET_STEP")
    if _source(record["source"]) != _int(record["actual_kib"]):
        raise QueueError("SOURCE_CAPACITY_MISMATCH")
    created = _int(record["requested_at"])
    expires = _int(record["expires_at"])
    changed = _int(record["changed_at"])
    state = record["state"]
    if type(state) is not str or state not in STATES or expires <= created or changed < created:
        raise QueueError("INVALID_LIFECYCLE")
    if state == "QUEUED" and changed != created:
        raise QueueError("INVALID_LIFECYCLE")
    if state == "EXPIRED" and changed < expires:
        raise QueueError("INVALID_EXPIRY")
    if state == "REPLACED":
        if _uuid(record["replaced_by"]) == record["id"]:
            raise QueueError("INVALID_REPLACEMENT")
    elif record["replaced_by"] is not None:
        raise QueueError("INVALID_REPLACEMENT")
    return record


def _new(target_gib, source, now, expires_at):
    return _validate({"id": str(uuid.uuid4()), "allocation": "managed-nvme",
                      "target_gib": target_gib, "source": source,
                      "actual_kib": _source(source), "requested_at": now,
                      "expires_at": expires_at, "changed_at": now,
                      "state": "QUEUED", "authorization_mode": "fresh-explicit",
                      "replaced_by": None})


class Queue:
    """One pending intent; immutable terminal rows retained for recovery.

    All writes use SQLite transactions and compare the expected request ID.
    Reopening never evaluates safety, dispatches, or silently repairs a DB.
    A caller must explicitly choose expiry; there is no production default.
    """
    def __init__(self, path):
        self.path = Path(path).absolute()
        created = False
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            created = True
        except FileExistsError:
            pass
        except OSError as exc:
            raise QueueError("QUEUE_UNAVAILABLE") from exc
        try:
            meta = self.path.lstat()
            if not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid() or meta.st_mode & 0o077:
                raise QueueError("UNSAFE_QUEUE_FILE")
            with self._transaction(write=created, initializing=created) as db:
                if created:
                    db.execute("""CREATE TABLE requests (
                        id TEXT PRIMARY KEY NOT NULL,
                        state TEXT NOT NULL CHECK(state IN ('QUEUED','CANCELLED','REPLACED','EXPIRED')),
                        payload TEXT NOT NULL
                    )""")
                    db.execute("CREATE UNIQUE INDEX one_pending ON requests(state) WHERE state='QUEUED'")
                    db.execute("PRAGMA user_version=1")
                if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                    raise QueueError("CORRUPT_QUEUE")
                self._pending(db)
        except OSError as exc:
            raise QueueError("QUEUE_UNAVAILABLE") from exc

    @contextlib.contextmanager
    def _transaction(self, write=False, initializing=False):
        try:
            with contextlib.closing(sqlite3.connect(self.path.as_uri() + "?mode=rw",
                                                     uri=True, timeout=1,
                                                     isolation_level=None)) as db:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                try:
                    if not initializing and db.execute("PRAGMA user_version").fetchone() != (1,):
                        raise QueueError("UNSUPPORTED_QUEUE_SCHEMA")
                    yield db
                    db.commit()
                except BaseException:
                    db.rollback()
                    raise
        except sqlite3.Error as exc:
            raise QueueError("QUEUE_STORAGE_ERROR") from exc

    @staticmethod
    def _decode(row):
        try:
            record = _validate(json.loads(row[2]))
            if (record["id"], record["state"]) != row[:2]:
                raise QueueError("ROW_MISMATCH")
            return record
        except (ValueError, TypeError, RecursionError) as exc:
            raise QueueError("CORRUPT_RECORD") from exc

    @classmethod
    def _pending(cls, db):
        rows = db.execute("SELECT id,state,payload FROM requests WHERE state='QUEUED' LIMIT 2").fetchall()
        if len(rows) > 1:
            raise QueueError("MULTIPLE_PENDING")
        return cls._decode(rows[0]) if rows else None

    @staticmethod
    def _insert(db, record):
        db.execute("INSERT INTO requests VALUES(?,?,?)",
                   (record["id"], record["state"], json.dumps(record, sort_keys=True)))

    @staticmethod
    def _finish(db, record, state, now, replacement=None):
        record = _validate(dict(record, state=state, changed_at=now, replaced_by=replacement))
        result = db.execute("UPDATE requests SET state=?,payload=? WHERE id=? AND state='QUEUED'",
                            (state, json.dumps(record, sort_keys=True), record["id"]))
        if result.rowcount != 1:
            raise QueueError("STALE_REQUEST")
        return record

    @classmethod
    def _expected(cls, db, expected_id):
        _uuid(expected_id)
        pending = cls._pending(db)
        if not pending or pending["id"] != expected_id:
            raise QueueError("STALE_REQUEST")
        return pending

    def pending(self):
        with self._transaction() as db:
            return self._pending(db)

    def lookup(self, request_id):
        _uuid(request_id)
        with self._transaction() as db:
            row = db.execute("SELECT id,state,payload FROM requests WHERE id=?", (request_id,)).fetchone()
            return self._decode(row) if row else None

    def enqueue(self, *, target_gib, source, now, expires_at):
        record = _new(target_gib, source, now, expires_at)
        with self._transaction(write=True) as db:
            if self._pending(db) is not None:
                raise QueueError("PENDING_EXISTS")
            self._insert(db, record)
        return record

    def replace(self, expected_id, *, target_gib, source, now, expires_at):
        record = _new(target_gib, source, now, expires_at)
        with self._transaction(write=True) as db:
            old = self._expected(db, expected_id)
            self._finish(db, old, "REPLACED", now, record["id"])
            self._insert(db, record)
        return record

    def cancel(self, expected_id, *, now):
        with self._transaction(write=True) as db:
            return self._finish(db, self._expected(db, expected_id), "CANCELLED", now)

    def expire(self, expected_id, *, now):
        with self._transaction(write=True) as db:
            old = self._expected(db, expected_id)
            if _int(now) < old["expires_at"]:
                raise QueueError("NOT_EXPIRED")
            return self._finish(db, old, "EXPIRED", now)
