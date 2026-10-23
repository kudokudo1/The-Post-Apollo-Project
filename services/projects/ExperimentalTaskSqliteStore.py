#!/usr/bin/env python3
"""M10j experimental TASKS SQLite adapter. NO live Quickshell/CLI integration.

Every operation requires a caller-supplied database path. The only supported
writers are synthetic test callers. No XDG defaults, no remote sync, no
migration and no access to ApolloHubTodoStore. See M10j design document.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat

SCHEMA_VERSION = 1
MODEL_VERSION = 2
MAX_BYTES = 1048576
FIELDS = ("title", "done", "priority", "description", "dueDate")
STATES = ("PENDING", "SENDING", "UNCERTAIN", "CONFLICT", "ACKNOWLEDGED")
PRIORITIES = ("none", "low", "medium", "high", "urgent")
KINDS = ("text", "number", "boolean", "date")
ROOT = {"version", "revision", "nextId", "nextProjectId", "nextOperationId",
        "projects", "tasks", "operations"}
PROJECT = {"id", "name", "createdAtMs", "updatedAtMs", "family", "remote", "fields"}
TASK = {"id", "title", "done", "createdAtMs", "updatedAtMs", "priority",
        "description", "dueDate", "projectId", "remote", "values"}
OPERATION = {"id", "taskId", "projectId", "field", "before", "after",
             "createdRevision", "state", "ackToken"}


class StoreError(ValueError):
    pass


class InterruptedCommit(RuntimeError):
    """Test-only synthetic interruption. Outcome may have committed."""


def _pairs(items):
    doc = {}
    for key, value in items:
        if key in doc:
            raise StoreError("DUPLICATE_JSON_KEY")
        doc[key] = value
    return doc


def _bad_constant(value):
    raise StoreError("NONFINITE_JSON_NUMBER")


def _json_bytes(doc):
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _keys(obj, expected):
    return type(obj) is dict and set(obj) == expected


def _int(value, minimum=0, maximum=1000000000):
    return type(value) is int and minimum <= value <= maximum


def _identifier(s, prefix):
    return (type(s) is str and re.fullmatch(re.escape(prefix) + r"[1-9][0-9]*", s)
            is not None and len(s) <= 15 and
            _int(int(s[len(prefix):]), 1))


def _text(s, n, nonempty=False):
    return (type(s) is str and len(s) <= n and
            (not nonempty or (bool(s) and s == s.strip())) and
            not any(ord(c) < 32 and c not in "\n\t" or ord(c) == 127 for c in s)
            and (not nonempty or not any(ord(c) < 32 for c in s)))


def _date(s):
    if s is None:
        return True
    if type(s) is not str or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", s) is None:
        return False
    year, month, day = map(int, s.split("-"))
    if year < 1 or not (1 <= month <= 12):
        return False
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days = (31, 29 if leap else 28, 31, 30, 31, 30,
            31, 31, 30, 31, 30, 31)
    return 1 <= day <= days[month - 1]


def _task_value(field, val):
    if field == "title":
        return _text(val, 160, True)
    if field == "done":
        return type(val) is bool
    if field == "priority":
        return type(val) is str and val in PRIORITIES
    if field == "description":
        return _text(val, 2000)
    if field == "dueDate":
        return _date(val)
    return False


def _custom_value(kind, val):
    if val is None:
        return True
    if kind == "text":
        return _text(val, 2000)
    if kind == "number":
        return (type(val) in (int, float) and math.isfinite(val)
                and abs(val) <= 1000000000000)
    if kind == "boolean":
        return type(val) is bool
    if kind == "date":
        return _date(val)
    return False


def validate(doc):
    """Fail-closed minimal full-v2 schema mirror, not a replacement for JS policy."""
    if not _keys(doc, ROOT) or doc["version"] != MODEL_VERSION:
        raise StoreError("INVALID_MODEL_VERSION_OR_FIELDS")
    if not (_int(doc["revision"]) and _int(doc["nextId"], 1) and
            _int(doc["nextProjectId"], 1) and _int(doc["nextOperationId"], 1)):
        raise StoreError("INVALID_SEQUENCE")
    projects, tasks, operations = (doc["projects"], doc["tasks"], doc["operations"])
    if (type(projects) is not list or len(projects) > 30 or
            type(tasks) is not list or len(tasks) > 200 or
            type(operations) is not list or len(operations) > 1000):
        raise StoreError("INVALID_COLLECTION")
    project_map, field_defs, names, pmax = {}, {}, set(), 0
    for p in projects:
        if (not _keys(p, PROJECT) or not _identifier(p["id"], "p")
                or not _text(p["name"], 64, True)
                or p["id"] in project_map or p["name"].lower() in names
                or p["family"] not in ("normal", "git")
                or not _int(p["createdAtMs"], 1, 9007199254740991)
                or not _int(p["updatedAtMs"], p["createdAtMs"], 9007199254740991)):
            raise StoreError("INVALID_PROJECT")
        remote = p["remote"]
        if p["family"] == "normal":
            if remote is not None:
                raise StoreError("NORMAL_PROJECT_HAS_REMOTE_REFERENCE")
        elif (not _keys(remote, {"provider", "owner", "projectNodeId", "projectNumber"})
              or remote["provider"] != "github"
              or not _text(remote["owner"], 39, True)
              or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", remote["owner"]) is None
              or not _text(remote["projectNodeId"], 200, True)
              or any(c.isspace() for c in remote["projectNodeId"])
              or not _int(remote["projectNumber"], 1)):
            raise StoreError("INVALID_UNVERIFIED_GITHUB_PROJECT_REF")
        fields = p["fields"]
        if type(fields) is not list or len(fields) > 24:
            raise StoreError("INVALID_FIELD_DEFINITIONS")
        local_defs, labels = {}, set()
        for f in fields:
            if (not _keys(f, {"id", "label", "kind", "scope"})
                    or not _identifier(f["id"], "f")
                    or f["id"] in local_defs
                    or not _text(f["label"], 64, True)
                    or f["label"].lower() in labels
                    or f["kind"] not in KINDS or f["scope"] != "local"):
                raise StoreError("INVALID_FIELD")
            local_defs[f["id"]] = f["kind"]
            labels.add(f["label"].lower())
        project_map[p["id"]] = p
        field_defs[p["id"]] = local_defs
        names.add(p["name"].lower())
        pmax = max(pmax, int(p["id"][1:]))
    if pmax >= doc["nextProjectId"]:
        raise StoreError("REUSED_PROJECT_SEQUENCE")
    task_map, tmax = {}, 0
    for t in tasks:
        if (not _keys(t, TASK) or not _identifier(t["id"], "t")
                or t["id"] in task_map
                or not _int(t["createdAtMs"], 1, 9007199254740991)
                or not _int(t["updatedAtMs"], t["createdAtMs"], 9007199254740991)
                or (t["projectId"] is not None and t["projectId"] not in project_map)
                or any(not _task_value(k, t[k]) for k in FIELDS)):
            raise StoreError("INVALID_TASK")
        remote = t["remote"]
        if remote is not None:
            if (t["projectId"] is None or project_map[t["projectId"]]["family"] != "git"
                    or not _keys(remote, {"projectItemNodeId", "contentKind",
                                          "contentNodeId"})
                    or not _text(remote["projectItemNodeId"], 200, True)
                    or any(c.isspace() for c in remote["projectItemNodeId"])
                    or remote["contentKind"] not in
                    ("ISSUE", "PULL_REQUEST", "DRAFT_ISSUE")
                    or (remote["contentKind"] != "DRAFT_ISSUE"
                        and not _text(remote["contentNodeId"], 200, True))
                    or (remote["contentNodeId"] is not None and
                        (not _text(remote["contentNodeId"], 200, True) or
                         any(c.isspace() for c in remote["contentNodeId"])))):
                raise StoreError("INVALID_UNVERIFIED_GITHUB_ITEM_REF")
        values = t["values"]
        if type(values) is not dict or len(values) > 24:
            raise StoreError("INVALID_TYPED_VALUES")
        definitions = field_defs.get(t["projectId"], {})
        for field_id, val in values.items():
            if field_id not in definitions or not _custom_value(definitions[field_id], val):
                raise StoreError("INVALID_CUSTOM_FIELD_VALUE")
        task_map[t["id"]] = t
        tmax = max(tmax, int(t["id"][1:]))
    if tmax >= doc["nextId"]:
        raise StoreError("REUSED_TASK_SEQUENCE")
    seen_ops, last_revision, omax = set(), 0, 0
    for op in operations:
        if not _keys(op, OPERATION) or not _identifier(op["id"], "op"):
            raise StoreError("INVALID_OPERATION")
        task, proj = task_map.get(op["taskId"]), project_map.get(op["projectId"])
        if (op["id"] in seen_ops or task is None or proj is None
                or task["projectId"] != proj["id"] or proj["family"] != "git"
                or op["field"] not in FIELDS
                or not _task_value(op["field"], op["before"])
                or not _task_value(op["field"], op["after"])
                or op["before"] == op["after"]
                or not _int(op["createdRevision"], last_revision + 1, doc["revision"])
                or op["state"] not in STATES
                or (op["ackToken"] is not None and
                    not _text(op["ackToken"], 256, True))
                or ((op["state"] == "ACKNOWLEDGED") !=
                    (op["ackToken"] is not None))):
            raise StoreError("INVALID_REMOTE_INTENT")
        last_revision = op["createdRevision"]
        seen_ops.add(op["id"])
        omax = max(omax, int(op["id"][2:]))
    if omax >= doc["nextOperationId"]:
        raise StoreError("REUSED_OPERATION_SEQUENCE")
    data = _json_bytes(doc)
    if len(data) > MAX_BYTES:
        raise StoreError("OVER_CAPACITY")
    return data


def _owned_private_directory(parent):
    info = parent.lstat()
    if (not stat.S_ISDIR(info.st_mode) or parent.is_symlink()
            or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077):
        raise StoreError("UNSAFE_DATABASE_DIRECTORY")


def _owned_private_file(file):
    info = file.lstat()
    if (not stat.S_ISREG(info.st_mode) or file.is_symlink()
            or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077):
        raise StoreError("UNSAFE_DATABASE_FILE")


def connect(file: Path, *, initialize=False):
    """Explicit test path; read-only access never creates directories or DB."""
    if not isinstance(file, Path) or file.name != "tasks.db":
        raise StoreError("EXPLICIT_TASKS_DB_PATH_REQUIRED")
    if not file.parent.exists():
        if not initialize:
            return None
        raise StoreError("TEST_DIRECTORY_MUST_PREEXIST")
    _owned_private_directory(file.parent)
    if file.is_symlink():
        raise StoreError("UNSAFE_DATABASE_LINK")
    exists = file.exists()
    if not exists and not initialize:
        return None
    if not exists:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(file, flags, 0o600)
            os.close(fd)
        except FileExistsError:
            pass
    _owned_private_file(file)
    if initialize:
        con = sqlite3.connect(str(file), timeout=0.2, isolation_level=None)
    else:
        from urllib.parse import quote
        con = sqlite3.connect("file:" + quote(str(file), safe="/") + "?mode=ro",
                              uri=True, timeout=0.2, isolation_level=None)
    try:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout=200")
        con.execute("PRAGMA foreign_keys=ON")
        version = con.execute("PRAGMA user_version").fetchone()[0]
        if version not in ((0, 1) if initialize else (1,)):
            raise StoreError("UNSUPPORTED_DATABASE_SCHEMA")
        if initialize:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
            con.execute("BEGIN IMMEDIATE")
            try:
                ddl = """CREATE TABLE IF NOT EXISTS state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton=1),
                    revision INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    payload_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY, name TEXT NOT NULL,
                    family TEXT NOT NULL, updated_ms INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES projects(project_id),
                    due_date TEXT, done INTEGER NOT NULL,
                    priority TEXT NOT NULL, updated_ms INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
                CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(task_id),
                    project_id TEXT NOT NULL REFERENCES projects(project_id),
                    state TEXT NOT NULL, created_revision INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_ops_state ON operations(state);"""
                for statement in ddl.split(";"):
                    if statement.strip():
                        con.execute(statement)
                con.execute("PRAGMA user_version=1")
                con.commit()
            except Exception:
                con.rollback()
                raise
        else:
            for table in ("state", "projects", "tasks", "operations"):
                if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                               (table,)).fetchone() is None:
                    raise StoreError("MISSING_DATABASE_TABLE")
        return con
    except Exception:
        con.close()
        raise


def _interrupt(stop_at, stage):
    if stop_at == stage:
        raise InterruptedCommit(stage)


def _read(con):
    if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise StoreError("SQLITE_INTEGRITY_CHECK_FAILED")
    row = con.execute("SELECT revision,payload,payload_hash FROM state WHERE singleton=1").fetchone()
    if row is None:
        return None
    raw = row["payload"]
    if type(raw) is not str or len(raw.encode("utf8")) > MAX_BYTES:
        raise StoreError("CORRUPT_PAYLOAD")
    if _digest(raw.encode("utf8")) != row["payload_hash"]:
        raise StoreError("CORRUPT_PAYLOAD_HASH")
    try:
        doc = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except (ValueError, TypeError) as e:
        raise StoreError("INVALID_JSON_PAYLOAD") from e
    validate(doc)
    if row["revision"] != doc["revision"]:
        raise StoreError("REVISION_MISMATCH")
    # Data/index parity is checked, not silently reconstructed.
    indexed_projects = [(p["id"], p["name"], p["family"], p["updatedAtMs"])
                        for p in doc["projects"]]
    indexed_tasks = [(t["id"], t["projectId"], t["dueDate"],
                      int(t["done"]), t["priority"], t["updatedAtMs"])
                     for t in doc["tasks"]]
    indexed_ops = [(o["id"], o["taskId"], o["projectId"], o["state"],
                    o["createdRevision"]) for o in doc["operations"]]
    for table, columns, expected in (
        ("projects", "project_id,name,family,updated_ms", indexed_projects),
        ("tasks", "task_id,project_id,due_date,done,priority,updated_ms", indexed_tasks),
        ("operations", "operation_id,task_id,project_id,state,created_revision", indexed_ops),
    ):
        got = [tuple(x) for x in con.execute(f"SELECT {columns} FROM {table}")]
        if sorted(got, key=lambda x: x[0]) != sorted(expected, key=lambda x: x[0]):
            raise StoreError("INDEX_DIVERGENCE_" + table.upper())
    return {"document": doc, "revision": doc["revision"], "hash": row["payload_hash"]}


def read(file: Path):
    con = connect(file, initialize=False)
    if con is None:
        return {"status": "ABSENT", "available": False}
    try:
        # BEGIN establishes one WAL read snapshot for state, indexes and
        # integrity checks; otherwise a concurrent commit between SELECTs
        # could generate a false INDEX_DIVERGENCE.
        con.execute("BEGIN")
        result = _read(con)
        if result is None:
            return {"status": "EMPTY", "available": False}
        blocked = [op["id"] for op in result["document"]["operations"]
                   if op["state"] in ("SENDING", "UNCERTAIN", "CONFLICT")]
        return {"status": "RECOVERY_REVIEW" if blocked else "READY",
                "available": True, "blockedOperations": blocked, **result}
    finally:
        if con.in_transaction:
            con.rollback()
        con.close()


def commit(file: Path, candidate: dict, *, expected_revision=None,
           expected_hash=None, stop_at=None):
    """Test-only atomic DB commit, no migration or remote permission.

    The first insert requires (None,None) baseline and candidate rev 0.
    Subsequent commits require a matching revision and source hash,
    with exactly +1 revision. Ambiguous postcommit failures need read().
    """
    data = validate(candidate)
    if (expected_revision is None) != (expected_hash is None):
        raise StoreError("PARTIAL_EXPECTED_BASELINE")
    if expected_hash is not None and not re.fullmatch(r"[a-f0-9]{64}", expected_hash):
        raise StoreError("INVALID_EXPECTED_HASH")
    con = connect(file, initialize=True)
    try:
        _interrupt(stop_at, "before_begin")
        con.execute("BEGIN IMMEDIATE")
        try:
            current = _read(con)
            if current is None:
                if expected_revision is not None or candidate["revision"] != 0:
                    raise StoreError("INITIAL_BASELINE_REQUIRED")
            else:
                if (current["revision"] != expected_revision
                        or current["hash"] != expected_hash):
                    raise StoreError("STALE_BASELINE")
                if candidate["revision"] != current["revision"] + 1:
                    raise StoreError("REVISION_STEP_REQUIRED")
            _interrupt(stop_at, "after_begin")
            con.execute("DELETE FROM operations")
            con.execute("DELETE FROM tasks")
            con.execute("DELETE FROM projects")
            for p in candidate["projects"]:
                con.execute("INSERT INTO projects VALUES (?,?,?,?)",
                            (p["id"], p["name"], p["family"], p["updatedAtMs"]))
            _interrupt(stop_at, "after_projects")
            for t in candidate["tasks"]:
                con.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?)",
                            (t["id"], t["projectId"], t["dueDate"], int(t["done"]),
                             t["priority"], t["updatedAtMs"]))
            _interrupt(stop_at, "after_tasks")
            for op in candidate["operations"]:
                con.execute("INSERT INTO operations VALUES (?,?,?,?,?)",
                            (op["id"], op["taskId"], op["projectId"], op["state"],
                             op["createdRevision"]))
            _interrupt(stop_at, "after_operations")
            raw = data.decode("utf8")
            digest = _digest(data)
            if current is None:
                con.execute("INSERT INTO state VALUES (1,?,?,?)",
                            (candidate["revision"], raw, digest))
            else:
                con.execute("UPDATE state SET revision=?,payload=?,payload_hash=? WHERE singleton=1",
                            (candidate["revision"], raw, digest))
            _interrupt(stop_at, "before_commit")
            con.commit()
            _interrupt(stop_at, "after_commit")
            result = _read(con)
            if result is None or result["hash"] != digest:
                raise StoreError("POST_COMMIT_READBACK_FAILED")
            return {"status": "LOCAL_COMMITTED", "revision": candidate["revision"],
                    "hash": digest, "localSaved": True, "remoteSent": False,
                    "remoteWriteAuthorized": False}
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
    finally:
        con.close()
