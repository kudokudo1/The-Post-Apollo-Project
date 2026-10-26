#!/usr/bin/env python3
"""M11l REAL-SCHEMA, DISPOSABLE-COPY owner candidate. NEVER a live TASKS host.

Only an explicit private directory literally named m11l-tasks-copy is accepted.
Holds a lifetime OS flock; journals reservations for an existing task JSON
copy, independently reads back fixture writes, and fails closed on restart.
There is intentionally NO production CLI, Quickshell mount or writer method.
"""
from __future__ import annotations

from datetime import date
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat


class GateError(RuntimeError):
    pass


MAX_BYTES = 1048576
MAX_TASKS = 200
MAX_PROJECTS = 30
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,95}\Z")


def require(ok, reason):
    if not ok:
        raise GateError(reason)


def private_dir(path):
    require(isinstance(path, Path) and path.is_absolute()
            and path.name == "m11l-tasks-copy", "DISPOSABLE_COPY_REQUIRED")
    m = path.lstat()
    require(stat.S_ISDIR(m.st_mode) and not path.is_symlink()
            and m.st_uid == os.geteuid()
            and stat.S_IMODE(m.st_mode) & 0o077 == 0,
            "PRIVATE_DIRECTORY_REQUIRED")
    return path


def owned_regular(path, max_bytes=None):
    m = path.lstat()
    require(stat.S_ISREG(m.st_mode) and not path.is_symlink()
            and m.st_uid == os.geteuid() and m.st_nlink == 1
            and stat.S_IMODE(m.st_mode) & 0o077 == 0,
            "UNSAFE_FILE_IDENTITY")
    if max_bytes is not None:
        require(0 < m.st_size <= max_bytes, "INVALID_SOURCE_SIZE")
    return m


def source_bytes(path):
    try:
        before = owned_regular(path, MAX_BYTES)
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            current = os.fstat(fd)
            require((current.st_dev, current.st_ino) ==
                    (before.st_dev, before.st_ino), "SOURCE_REPLACED")
            data = os.read(fd, MAX_BYTES + 1)
            after = os.fstat(fd)
            require(len(data) == before.st_size
                    and (current.st_size, current.st_mtime_ns, current.st_ctime_ns)
                    == (after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                    "SOURCE_CHANGED_DURING_READ")
        finally:
            os.close(fd)
        tail = path.lstat()
        require((tail.st_dev, tail.st_ino) ==
                (before.st_dev, before.st_ino), "SOURCE_PATH_REPLACED")
        return data
    except (FileNotFoundError, OSError) as exc:
        raise GateError("SOURCE_UNAVAILABLE") from exc


def stable_source(path):
    first = source_bytes(path)
    require(first == source_bytes(path), "UNSTABLE_SOURCE")
    return first


def no_duplicates(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def valid_number(v, minimum=1, maximum=1000000000):
    return type(v) is int and minimum <= v <= maximum


def valid_text(s, limit, *, allow_empty=False, multiline=False):
    return (type(s) is str and (allow_empty or bool(s))
            and len(s) <= limit and (allow_empty or s == s.strip())
            and not any(ord(ch) == 127 or ord(ch) < 32 and
                        (not multiline or ch not in "\t\n\r")
                        for ch in s))


def valid_date(value):
    if value is None:
        return True
    if type(value) is not str or re.fullmatch(r"\d{4}-\d\d-\d\d", value) is None:
        return False
    try:
        year, month, day = map(int, value.split("-"))
        return year > 0 and date(year, month, day).isoformat() == value
    except ValueError:
        return False


def parse_task_document(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES,
            "INVALID_JSON_BYTES")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (ValueError, UnicodeError) as exc:
        raise GateError("INVALID_JSON_DOCUMENT") from exc
    require(type(doc) is dict, "INVALID_DOCUMENT")
    version = doc.get("version")
    require(type(version) is int and version in (1, 2, 3),
            "UNSUPPORTED_VERSION")
    require(valid_number(doc.get("nextId")), "INVALID_NEXT_ID")
    tasks = doc.get("tasks")
    require(type(tasks) is list and len(tasks) <= MAX_TASKS, "INVALID_TASK_LIST")
    projects = []
    project_ids = set()
    if version == 3:
        require(valid_number(doc.get("nextProjectId")),
                "INVALID_NEXT_PROJECT_ID")
        projects = doc.get("projects")
        require(type(projects) is list and len(projects) <= MAX_PROJECTS,
                "INVALID_PROJECT_LIST")
        seen_names = set()
        for p in projects:
            require(type(p) is dict and type(p.get("id")) is str and
                    re.fullmatch(r"p[1-9][0-9]*", p["id"]) and
                    valid_text(p.get("name"), 64) and
                    valid_number(p.get("createdAtMs"), maximum=2**53-1) and
                    valid_number(p.get("updatedAtMs"),
                                 minimum=p["createdAtMs"], maximum=2**53-1),
                    "INVALID_PROJECT")
            require(p["id"] not in project_ids and
                    p["name"].lower() not in seen_names,
                    "DUPLICATE_PROJECT")
            project_ids.add(p["id"])
            seen_names.add(p["name"].lower())
        require(all(int(p["id"][1:]) < doc["nextProjectId"] for p in projects),
                "PROJECT_SEQUENCE_REWIND")
    seen = set()
    for task in tasks:
        require(type(task) is dict and type(task.get("id")) is str and
                re.fullmatch(r"t[1-9][0-9]*", task["id"]) and
                valid_text(task.get("title"), 160) and
                type(task.get("done")) is bool and
                valid_number(task.get("createdAtMs"), maximum=2**53-1) and
                valid_number(task.get("updatedAtMs"),
                             minimum=task["createdAtMs"], maximum=2**53-1),
                "INVALID_TASK")
        require(task["id"] not in seen, "DUPLICATE_TASK")
        seen.add(task["id"])
        if version >= 2:
            require(task.get("priority") in
                    ("none", "low", "medium", "high", "urgent") and
                    valid_text(task.get("description"), 2000, allow_empty=True,
                               multiline=True) and
                    valid_date(task.get("dueDate", "__MISSING__")),
                    "INVALID_TASK_DETAILS")
        if version == 3:
            require("projectId" in task and
                    (task["projectId"] is None or
                     task["projectId"] in project_ids),
                    "INVALID_TASK_PROJECT")
    require(all(int(t["id"][1:]) < doc["nextId"] for t in tasks),
            "TASK_SEQUENCE_REWIND")
    return doc


def digest(data):
    return hashlib.sha256(data).hexdigest()


class CandidateOwner:
    """Disposable-copy authority. FileView simulation is external to this class."""

    def __init__(self, folder: Path, writer_id: str, *, bootstrap=False):
        private_dir(folder)
        require(type(writer_id) is str and ID_RE.fullmatch(writer_id),
                "INVALID_WRITER_ID")
        self.folder = folder
        self.source = folder / "todo-copy.json"
        self.dbpath = folder / "gate-review.db"
        self._lock = None
        self._db = None
        self._closed = False
        self._pid = os.getpid()
        try:
            raw = stable_source(self.source)
            parse_task_document(raw)
            lock_path = folder / "gate-review.lock"
            if not lock_path.exists():
                try:
                    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                                 getattr(os, "O_NOFOLLOW", 0), 0o600)
                    os.close(fd)
                except FileExistsError:
                    pass
            owned_regular(lock_path)
            self._lock = os.open(lock_path, os.O_RDONLY |
                                 getattr(os, "O_NOFOLLOW", 0))
            try:
                fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise GateError("LOCK_CONTENDED") from exc
            require(not self.dbpath.is_symlink(), "UNSAFE_JOURNAL")
            if bootstrap:
                require(not self.dbpath.exists(), "JOURNAL_ALREADY_EXISTS")
                backup = folder / "source-before-gate.bak"
                require(not backup.exists(), "BACKUP_ALREADY_EXISTS")
                bfd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                              getattr(os, "O_NOFOLLOW", 0), 0o600)
                try:
                    os.write(bfd, raw)
                    os.fsync(bfd)
                finally:
                    os.close(bfd)
                require(source_bytes(backup) == raw, "BACKUP_READBACK_FAILED")
                fd = os.open(self.dbpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                             getattr(os, "O_NOFOLLOW", 0), 0o600)
                os.close(fd)
            else:
                require(self.dbpath.exists(), "JOURNAL_MISSING")
                previous_backup = stable_source(folder / "source-before-gate.bak")
                parse_task_document(previous_backup)
            owned_regular(self.dbpath)
            self._db = sqlite3.connect(str(self.dbpath),
                                       timeout=0.2, isolation_level=None)
            self._db.row_factory = sqlite3.Row
            self._db.execute("PRAGMA busy_timeout=200")
            self._db.execute("PRAGMA synchronous=FULL")
            if bootstrap:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute("""CREATE TABLE owner (
                    id INTEGER PRIMARY KEY CHECK (id=1),
                    phase TEXT NOT NULL, epoch INTEGER NOT NULL,
                    writer TEXT NOT NULL, source_hash TEXT NOT NULL,
                    backup_hash TEXT NOT NULL,
                    pending_stage TEXT, expected_hash TEXT,
                    reason TEXT NOT NULL)""")
                self._db.execute("INSERT INTO owner VALUES (1,'JSON_ACTIVE',0,?,?,?,NULL,NULL,'')",
                                 (writer_id, digest(raw), digest(raw)))
                self._db.execute("PRAGMA user_version=1")
                self._db.commit()
            else:
                require(self._db.execute("PRAGMA user_version").fetchone()[0] == 1,
                        "UNKNOWN_JOURNAL_SCHEMA")
                self._db.execute("BEGIN IMMEDIATE")
                row = self._row()
                require(row["epoch"] < 1000000000, "EPOCH_EXHAUSTED")
                require(row["backup_hash"] == digest(previous_backup),
                        "BACKUP_CHANGED")
                self._db.execute("""UPDATE owner SET phase='RECOVERY_REVIEW',
                    epoch=epoch+1, writer=?, reason='FRESH_OWNER_MUST_REVIEW'
                    WHERE id=1""", (writer_id,))
                self._db.commit()
            self.writer_id = writer_id
        except BaseException:
            self.close()
            raise

    def _guard(self):
        require(not self._closed and os.getpid() == self._pid and
                self._db is not None and self._lock is not None,
                "OWNER_NOT_ACTIVE")
        return self._db

    def _row(self):
        row = self._db.execute("SELECT * FROM owner WHERE id=1").fetchone()
        require(row is not None, "JOURNAL_CORRUPT")
        return row

    def state(self):
        self._guard()
        row = self._row()
        require(row["writer"] == self.writer_id, "STALE_OWNER")
        return {"phase": row["phase"], "epoch": row["epoch"],
                "pending": row["pending_stage"] is not None,
                "liveWriterAuthorized": False, "sqliteWriteAuthorized": False}

    def reserve(self, stage_id: str, candidate: bytes):
        self._guard()
        require(type(stage_id) is str and ID_RE.fullmatch(stage_id),
                "INVALID_STAGE_ID")
        parse_task_document(candidate)
        current = stable_source(self.source)
        self._db.execute("BEGIN IMMEDIATE")
        try:
            row = self._row()
            require(row["writer"] == self.writer_id and
                    row["phase"] == "JSON_ACTIVE" and
                    row["pending_stage"] is None, "STAGE_NOT_ADMISSIBLE")
            require(digest(current) == row["source_hash"],
                    "SOURCE_CHANGED_EXTERNALLY")
            require(candidate != current, "NO_CHANGE")
            self._db.execute("UPDATE owner SET pending_stage=?, expected_hash=? WHERE id=1",
                             (stage_id, digest(candidate)))
            self._db.commit()
        except BaseException:
            self._db.rollback()
            raise
        return {"stageId": stage_id, "epoch": row["epoch"],
                "expectedHash": digest(candidate),
                "liveWriterAuthorized": False}

    def verify(self, stage_id: str, expected_epoch: int):
        self._guard()
        current = stable_source(self.source)
        parse_task_document(current)
        self._db.execute("BEGIN IMMEDIATE")
        try:
            row = self._row()
            phase_ok = (row["phase"] == "JSON_ACTIVE"
                        and row["epoch"] == expected_epoch) or (
                        row["phase"] == "FREEZE_REQUESTED"
                        and row["epoch"] == expected_epoch + 1)
            require(phase_ok and row["writer"] == self.writer_id and
                    row["pending_stage"] == stage_id, "STALE_STAGE")
            require(digest(current) == row["expected_hash"],
                    "READBACK_MISMATCH")
            self._db.execute("""UPDATE owner SET pending_stage=NULL,
                expected_hash=NULL,source_hash=?,
                phase=CASE WHEN phase='FREEZE_REQUESTED' THEN
                    'JSON_QUIESCED' ELSE phase END WHERE id=1""",
                             (digest(current),))
            self._db.commit()
        except BaseException:
            self._db.rollback()
            raise
        return {"settled": True, "liveWriterAuthorized": False}

    def freeze(self, expected_epoch: int):
        self._guard()
        self._db.execute("BEGIN IMMEDIATE")
        try:
            row = self._row()
            require(row["writer"] == self.writer_id and
                    row["phase"] == "JSON_ACTIVE" and
                    row["epoch"] == expected_epoch, "FREEZE_REFUSED")
            next_phase = ("FREEZE_REQUESTED" if row["pending_stage"] is not None
                          else "JSON_QUIESCED")
            self._db.execute("""UPDATE owner SET phase=?,
                epoch=epoch+1, reason='EXPLICIT_TEST_FREEZE' WHERE id=1""",
                             (next_phase,))
            self._db.commit()
        except BaseException:
            self._db.rollback()
            raise
        return self.state()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._db is not None:
            self._db.close()
            self._db = None
        if self._lock is not None:
            fcntl.flock(self._lock, fcntl.LOCK_UN)
            os.close(self._lock)
            self._lock = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
