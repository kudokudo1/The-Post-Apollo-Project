#!/usr/bin/env python3
"""M10l record-authoritative SQLite TASKS prototype. UNMOUNTED, TEST-ONLY.

No default path, CLI, migrations, remote calls, live Quickshell writer, or
automatic recovery. Every caller explicitly supplies its own private
disposable tasks.db path. This is a separate schema-v2 experiment, not an
upgrade of the M10j schema-v1 snapshot store.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import quote

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "m10l_existing_validator", _HERE / "ExperimentalTaskSqliteStore.py"
)
_validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validator)
StoreError = _validator.StoreError
InterruptedCommit = _validator.InterruptedCommit

DB_SCHEMA_VERSION = 2
MODEL_VERSION = 2
MAX_SAFE_MS = 9007199254740991
FIELDS = ("title", "done", "priority", "description", "dueDate")
BLOCKED = ("SENDING", "UNCERTAIN", "CONFLICT")
DDL = (
    """CREATE TABLE meta (
       singleton INTEGER PRIMARY KEY CHECK(singleton=1),
       model_version INTEGER NOT NULL,
       revision INTEGER NOT NULL,
       next_id INTEGER NOT NULL,
       next_project_id INTEGER NOT NULL,
       next_operation_id INTEGER NOT NULL,
       model_hash TEXT NOT NULL)""",
    """CREATE TABLE projects (
       id TEXT PRIMARY KEY,
       position INTEGER NOT NULL UNIQUE,
       name TEXT NOT NULL,
       family TEXT NOT NULL,
       created_ms INTEGER NOT NULL,
       updated_ms INTEGER NOT NULL,
       remote_json TEXT NOT NULL,
       fields_json TEXT NOT NULL)""",
    """CREATE TABLE tasks (
       id TEXT PRIMARY KEY,
       position INTEGER NOT NULL UNIQUE,
       project_id TEXT REFERENCES projects(id),
       title TEXT NOT NULL,
       done INTEGER NOT NULL CHECK(done IN (0,1)),
       created_ms INTEGER NOT NULL,
       updated_ms INTEGER NOT NULL,
       priority TEXT NOT NULL,
       description TEXT NOT NULL,
       due_date TEXT,
       remote_json TEXT NOT NULL,
       values_json TEXT NOT NULL)""",
    """CREATE INDEX tasks_due_idx ON tasks(due_date)""",
    """CREATE INDEX tasks_project_idx ON tasks(project_id)""",
    """CREATE TABLE operations (
       id TEXT PRIMARY KEY,
       position INTEGER NOT NULL UNIQUE,
       task_id TEXT NOT NULL REFERENCES tasks(id),
       project_id TEXT NOT NULL REFERENCES projects(id),
       field TEXT NOT NULL,
       before_json TEXT NOT NULL,
       after_json TEXT NOT NULL,
       created_revision INTEGER NOT NULL,
       state TEXT NOT NULL,
       ack_token TEXT)""",
    """CREATE INDEX operations_state_idx ON operations(state)""",
)


def _canonical_bytes(doc):
    return json.dumps(doc, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(doc):
    return hashlib.sha256(_canonical_bytes(doc)).hexdigest()


def _json(val):
    return json.dumps(val, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))


def _unjson(raw):
    try:
        return json.loads(raw, object_pairs_hook=_validator._pairs,
                          parse_constant=_validator._bad_constant)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise StoreError("INVALID_STORED_JSON") from exc


def _path(file):
    if not isinstance(file, Path) or file.name != "tasks.db" or not file.is_absolute():
        raise StoreError("EXPLICIT_ABSOLUTE_TASKS_DB_REQUIRED")
    return file


def _connect(file, *, create=False):
    file = _path(file)
    if not file.parent.exists():
        if create:
            raise StoreError("TEST_DIRECTORY_MUST_PREEXIST")
        return None
    _validator._owned_private_directory(file.parent)
    if file.is_symlink():
        raise StoreError("UNSAFE_DATABASE_LINK")
    exists = file.exists()
    if not exists and not create:
        return None
    if not exists:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(file, flags, 0o600)
        os.close(fd)
    _validator._owned_private_file(file)
    if create:
        con = sqlite3.connect(str(file), timeout=0.2, isolation_level=None)
    else:
        con = sqlite3.connect("file:" + quote(str(file), safe="/") + "?mode=ro",
                              uri=True, timeout=0.2, isolation_level=None)
    try:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout=200")
        con.execute("PRAGMA foreign_keys=ON")
        version = con.execute("PRAGMA user_version").fetchone()[0]
        if create:
            if exists or version != 0:
                raise StoreError("INITIALIZATION_REQUIRES_NEW_DATABASE")
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=FULL")
        elif version != DB_SCHEMA_VERSION:
            raise StoreError("UNSUPPORTED_SQLITE_SCHEMA")
        return con
    except Exception:
        con.close()
        raise


def _insert_project(con, p, pos):
    con.execute("INSERT INTO projects VALUES(?,?,?,?,?,?,?,?)",
                (p["id"], pos, p["name"], p["family"], p["createdAtMs"],
                 p["updatedAtMs"], _json(p["remote"]), _json(p["fields"])))


def _insert_task(con, t, pos):
    con.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (t["id"], pos, t["projectId"], t["title"], int(t["done"]),
                 t["createdAtMs"], t["updatedAtMs"], t["priority"],
                 t["description"], t["dueDate"], _json(t["remote"]),
                 _json(t["values"])))


def _insert_operation(con, op, pos):
    con.execute("INSERT INTO operations VALUES(?,?,?,?,?,?,?,?,?,?)",
                (op["id"], pos, op["taskId"], op["projectId"], op["field"],
                 _json(op["before"]), _json(op["after"]),
                 op["createdRevision"], op["state"], op["ackToken"]))


def _load(con):
    if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise StoreError("SQLITE_INTEGRITY_CHECK_FAILED")
    meta = con.execute("SELECT * FROM meta WHERE singleton=1").fetchone()
    if meta is None:
        raise StoreError("MISSING_METADATA")
    projects = [
        {"id": r["id"], "name": r["name"], "family": r["family"],
         "createdAtMs": r["created_ms"], "updatedAtMs": r["updated_ms"],
         "remote": _unjson(r["remote_json"]), "fields": _unjson(r["fields_json"])}
        for r in con.execute("SELECT * FROM projects ORDER BY position")
    ]
    tasks = [
        {"id": r["id"], "projectId": r["project_id"],
         "title": r["title"], "done": bool(r["done"]),
         "createdAtMs": r["created_ms"], "updatedAtMs": r["updated_ms"],
         "priority": r["priority"], "description": r["description"],
         "dueDate": r["due_date"], "remote": _unjson(r["remote_json"]),
         "values": _unjson(r["values_json"])}
        for r in con.execute("SELECT * FROM tasks ORDER BY position")
    ]
    operations = [
        {"id": r["id"], "taskId": r["task_id"], "projectId": r["project_id"],
         "field": r["field"], "before": _unjson(r["before_json"]),
         "after": _unjson(r["after_json"]),
         "createdRevision": r["created_revision"], "state": r["state"],
         "ackToken": r["ack_token"]}
        for r in con.execute("SELECT * FROM operations ORDER BY position")
    ]
    doc = {
        "version": meta["model_version"], "revision": meta["revision"],
        "nextId": meta["next_id"], "nextProjectId": meta["next_project_id"],
        "nextOperationId": meta["next_operation_id"],
        "projects": projects, "tasks": tasks, "operations": operations
    }
    _validator.validate(doc)
    if _hash(doc) != meta["model_hash"]:
        raise StoreError("MODEL_HASH_MISMATCH")
    if len(_canonical_bytes(doc)) > _validator.MAX_BYTES:
        raise StoreError("OVER_CAPACITY")
    return {"document": doc, "revision": doc["revision"], "hash": meta["model_hash"]}


def initialize(file, model):
    """Synthetic only: initializes a *new* DB; never migrates an existing one."""
    _validator.validate(model)
    if model["version"] != MODEL_VERSION or model["revision"] != 0:
        raise StoreError("INITIAL_MODEL_MUST_BE_REVISION_ZERO")
    con = _connect(file, create=True)
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            for statement in DDL:
                con.execute(statement)
            con.execute("INSERT INTO meta VALUES(1,?,?,?,?,?,?)",
                        (MODEL_VERSION, 0, model["nextId"],
                         model["nextProjectId"], model["nextOperationId"],
                         _hash(model)))
            for i, p in enumerate(model["projects"]):
                _insert_project(con, p, i)
            for i, t in enumerate(model["tasks"]):
                _insert_task(con, t, i)
            for i, op in enumerate(model["operations"]):
                _insert_operation(con, op, i)
            con.execute("PRAGMA user_version=2")
            con.commit()
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        result = _load(con)
        if result["document"] != model:
            raise StoreError("INITIAL_READBACK_FAILED")
        return {"status": "LOCAL_COMMITTED", "localSaved": True,
                "remoteSent": False, "writeReady": False, **result}
    finally:
        con.close()


def read(file):
    con = _connect(file, create=False)
    if con is None:
        return {"status": "ABSENT", "available": False}
    try:
        con.execute("BEGIN")
        x = _load(con)
        blocked = [op["id"] for op in x["document"]["operations"]
                   if op["state"] in BLOCKED]
        return {"status": "RECOVERY_REVIEW" if blocked else "READY",
                "available": True, "blockedOperations": blocked, **x}
    finally:
        if con.in_transaction:
            con.rollback()
        con.close()


def edit_task(file, *, expected_revision, expected_hash,
              task_id, field, value, now_ms, stop_at=None):
    """Atomic single-record edit plus optional GIT journal append.

    Explicit test-only path, no QML caller and no GitHub transport. No
    mutation after a post-COMMIT exception is inferred without fresh read().
    """
    if not (type(expected_revision) is int and expected_revision >= 0
            and type(expected_hash) is str and re.fullmatch(r"[0-9a-f]{64}", expected_hash)
            and type(task_id) is str and field in FIELDS
            and _validator._task_value(field, value)
            and type(now_ms) is int and 1 <= now_ms <= MAX_SAFE_MS):
        raise StoreError("INVALID_EDIT_REQUEST")
    con = _connect(file, create=False)
    if con is None:
        raise StoreError("DATABASE_ABSENT")
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            current = _load(con)
            if current["revision"] != expected_revision or current["hash"] != expected_hash:
                raise StoreError("STALE_BASELINE")
            old = current["document"]
            task_index = next((i for i,t in enumerate(old["tasks"])
                               if t["id"] == task_id), None)
            if task_index is None:
                raise StoreError("UNKNOWN_TASK")
            task = old["tasks"][task_index]
            if task[field] == value:
                raise StoreError("NO_CHANGE")
            if now_ms < task["updatedAtMs"] or task["updatedAtMs"] >= MAX_SAFE_MS:
                raise StoreError("STALE_EDIT_TIME")
            if old["revision"] >= 1000000000:
                raise StoreError("REVISION_EXHAUSTED")
            project = next((p for p in old["projects"]
                            if p["id"] == task["projectId"]), None)
            queue = project is not None and project["family"] == "git"
            if queue and (len(old["operations"]) >= 1000
                          or old["nextOperationId"] >= 1000000000):
                raise StoreError("OPERATION_QUEUE_FULL")
            next_doc = copy.deepcopy(old)
            next_task = next_doc["tasks"][task_index]
            before = next_task[field]
            next_task[field] = value
            next_task["updatedAtMs"] = max(now_ms, task["updatedAtMs"] + 1)
            next_doc["revision"] += 1
            op = None
            if queue:
                op = {"id": "op"+str(next_doc["nextOperationId"]),
                      "taskId": task_id, "projectId": project["id"],
                      "field": field, "before": before, "after": value,
                      "createdRevision": next_doc["revision"], "state": "PENDING",
                      "ackToken": None}
                next_doc["nextOperationId"] += 1
                next_doc["operations"].append(op)
            _validator.validate(next_doc)
            _stop(stop_at, "before_task_update")
            col = {"title":"title", "done":"done", "priority":"priority",
                   "description":"description", "dueDate":"due_date"}[field]
            value_for_sql = int(value) if field == "done" else value
            con.execute(f"UPDATE tasks SET {col}=?,updated_ms=? WHERE id=?",
                        (value_for_sql, next_task["updatedAtMs"], task_id))
            _stop(stop_at, "after_task_update")
            if op:
                _insert_operation(con, op, len(old["operations"]))
            _stop(stop_at, "after_operation_insert")
            new_hash = _hash(next_doc)
            con.execute("UPDATE meta SET revision=?,next_operation_id=?,model_hash=? "
                        "WHERE singleton=1",
                        (next_doc["revision"], next_doc["nextOperationId"], new_hash))
            _stop(stop_at, "before_commit")
            con.commit()
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        _stop(stop_at, "after_commit")
        confirmed = _load(con)
        if confirmed["hash"] != new_hash or confirmed["document"] != next_doc:
            raise StoreError("POST_COMMIT_VERIFICATION_FAILED")
        return {"status": "LOCAL_COMMITTED", "localSaved": True,
                "remoteSent": False, "remoteWriteAuthorized": False,
                "remoteIntentCreated": bool(op),
                "revision": next_doc["revision"], "hash": new_hash}
    finally:
        con.close()


def _stop(selected, phase):
    if selected == phase:
        raise InterruptedCommit("INJECTED_" + phase)
