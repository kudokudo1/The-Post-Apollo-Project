#!/usr/bin/env python3
"""M10s isolated SQLite NORMAL-task CRUD. TEST-ONLY; never a live task writer.

All writes require a caller-supplied private absolute tasks.db created by M10l.
No CLI, default data path, QML mount, startup migration, network or GitHub API.
GIT linked tasks/projects are deliberately not mutable here: their identity
and pending-operation semantics need an independently reviewed contract.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "m10s_records_backend", HERE / "ExperimentalTaskSqliteRecordsV2.py")
records = importlib.util.module_from_spec(spec)
spec.loader.exec_module(records)
StoreError = records.StoreError
InterruptedCommit = records.InterruptedCommit
MAX_MS = records.MAX_SAFE_MS


def _timestamp(value):
    return type(value) is int and 1 <= value <= MAX_MS


def _normal_project(model, pid):
    if pid is None:
        return None
    p = next((p for p in model["projects"] if p["id"] == pid), None)
    if p is None:
        raise StoreError("UNKNOWN_PROJECT")
    if p["family"] != "normal" or p["remote"] is not None:
        raise StoreError("GIT_PROJECT_UNSUPPORTED")
    return p


def _normal_task(model, tid):
    t = next((t for t in model["tasks"] if t["id"] == tid), None)
    if t is None:
        raise StoreError("UNKNOWN_TASK")
    _normal_project(model, t["projectId"])
    if t["remote"] is not None or t["values"]:
        raise StoreError("REMOTE_OR_CUSTOM_TASK_UNSUPPORTED")
    if any(op["taskId"] == tid for op in model["operations"]):
        raise StoreError("JOURNALED_TASK_UNSUPPORTED")
    return t


def _transaction(file, expected_revision, expected_hash, update, stop_at):
    if (type(expected_revision) is not int or expected_revision < 0
            or type(expected_hash) is not str
            or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None):
        raise StoreError("INVALID_BASELINE")
    con = records._connect(file, writable=True)
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            baseline = records._load(con)
            if (baseline["revision"] != expected_revision
                    or baseline["hash"] != expected_hash):
                raise StoreError("STALE_BASELINE")
            if baseline["revision"] >= 1000000000:
                raise StoreError("REVISION_EXHAUSTED")
            candidate = copy.deepcopy(baseline["document"])
            record_id = update(con, candidate)
            candidate["revision"] += 1
            records._validator.validate(candidate)
            records._stop(stop_at, "after_record_write")
            digest = records._hash(candidate)
            con.execute(
                "UPDATE meta SET revision=?,next_id=?,next_project_id=?,"
                "next_operation_id=?,model_hash=? WHERE singleton=1",
                (candidate["revision"], candidate["nextId"],
                 candidate["nextProjectId"], candidate["nextOperationId"], digest))
            records._stop(stop_at, "before_commit")
            con.commit()
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        # A fault after COMMIT has an uncertain outcome; caller MUST read()
        # instead of trying the same mutation again blindly.
        records._stop(stop_at, "after_commit")
        confirmed = records._load(con)
        if confirmed["document"] != candidate or confirmed["hash"] != digest:
            raise StoreError("POST_COMMIT_VERIFICATION_FAILED")
        return {"status": "LOCAL_COMMITTED", "localSaved": True,
                "remoteSent": False, "remoteWriteAuthorized": False,
                "remoteIntentCreated": False, "id": record_id,
                "revision": candidate["revision"], "hash": digest}
    finally:
        con.close()


def create_normal_project(file, *, expected_revision, expected_hash,
                          name, now_ms, stop_at=None):
    if not (records._validator._text(name, 64, True) and _timestamp(now_ms)):
        raise StoreError("INVALID_PROJECT_CREATE")
    def update(con, doc):
        if len(doc["projects"]) >= 30 or doc["nextProjectId"] >= 1000000000:
            raise StoreError("PROJECT_CAPACITY_EXHAUSTED")
        if any(p["name"].lower() == name.lower() for p in doc["projects"]):
            raise StoreError("PROJECT_NAME_CONFLICT")
        pid = "p" + str(doc["nextProjectId"])
        item = {"id": pid, "name": name, "family": "normal",
                "remote": None, "fields": [],
                "createdAtMs": now_ms, "updatedAtMs": now_ms}
        doc["nextProjectId"] += 1
        records._insert_project(con, item, len(doc["projects"]))
        doc["projects"].append(item)
        return pid
    return _transaction(file, expected_revision, expected_hash, update, stop_at)


def create_task(file, *, expected_revision, expected_hash, title, due_date,
                now_ms, project_id=None, priority="none", description="",
                stop_at=None):
    if not (_timestamp(now_ms)
            and records._validator._task_value("title", title)
            and records._validator._task_value("dueDate", due_date)
            and records._validator._task_value("priority", priority)
            and records._validator._task_value("description", description)
            and (project_id is None or
                 type(project_id) is str and
                 records._validator._identifier(project_id, "p"))):
        raise StoreError("INVALID_TASK_CREATE")
    def update(con, doc):
        _normal_project(doc, project_id)
        if len(doc["tasks"]) >= 200 or doc["nextId"] >= 1000000000:
            raise StoreError("TASK_CAPACITY_EXHAUSTED")
        tid = "t" + str(doc["nextId"])
        item = {"id": tid, "projectId": project_id, "title": title,
                "done": False, "priority": priority, "description": description,
                "dueDate": due_date, "createdAtMs": now_ms,
                "updatedAtMs": now_ms, "remote": None, "values": {}}
        doc["nextId"] += 1
        records._insert_task(con, item, len(doc["tasks"]))
        doc["tasks"].append(item)
        return tid
    return _transaction(file, expected_revision, expected_hash, update, stop_at)


def assign_normal_project(file, *, expected_revision, expected_hash,
                          task_id, project_id, now_ms, stop_at=None):
    if not (_timestamp(now_ms) and type(task_id) is str
            and records._validator._identifier(task_id, "t")
            and (project_id is None or type(project_id) is str
                 and records._validator._identifier(project_id, "p"))):
        raise StoreError("INVALID_ASSIGNMENT")
    def update(con, doc):
        task = _normal_task(doc, task_id)
        _normal_project(doc, project_id)
        if task["projectId"] == project_id:
            raise StoreError("NO_CHANGE")
        if now_ms < task["updatedAtMs"] or task["updatedAtMs"] >= MAX_MS:
            raise StoreError("STALE_EDIT_TIME")
        task["projectId"] = project_id
        task["updatedAtMs"] = max(now_ms, task["updatedAtMs"] + 1)
        con.execute("UPDATE tasks SET project_id=?,updated_ms=? WHERE id=?",
                    (project_id, task["updatedAtMs"], task_id))
        return task_id
    return _transaction(file, expected_revision, expected_hash, update, stop_at)


def edit_normal_task_details(file, *, expected_revision, expected_hash,
                             task_id, priority, description, due_date, now_ms,
                             stop_at=None):
    """ONE transaction for priority + description + due date; no second save."""
    if not (_timestamp(now_ms) and type(task_id) is str
            and records._validator._identifier(task_id, "t")
            and records._validator._task_value("priority", priority)
            and records._validator._task_value("description", description)
            and records._validator._task_value("dueDate", due_date)):
        raise StoreError("INVALID_DETAILS")
    def update(con, doc):
        task = _normal_task(doc, task_id)
        if (task["priority"], task["description"], task["dueDate"]) == (
                priority, description, due_date):
            raise StoreError("NO_CHANGE")
        if now_ms < task["updatedAtMs"] or task["updatedAtMs"] >= MAX_MS:
            raise StoreError("STALE_EDIT_TIME")
        task.update(priority=priority, description=description, dueDate=due_date)
        task["updatedAtMs"] = max(now_ms, task["updatedAtMs"] + 1)
        con.execute(
            "UPDATE tasks SET priority=?,description=?,due_date=?,updated_ms=?"
            " WHERE id=?",
            (priority, description, due_date, task["updatedAtMs"], task_id))
        return task_id
    return _transaction(file, expected_revision, expected_hash, update, stop_at)


def remove_normal_task(file, *, expected_revision, expected_hash, task_id,
                       confirmed, stop_at=None):
    """Requires explicit confirmation; never removes journaled or GIT tasks."""
    if not (confirmed is True and type(task_id) is str
            and records._validator._identifier(task_id, "t")):
        raise StoreError("DELETE_NOT_CONFIRMED")
    def update(con, doc):
        _normal_task(doc, task_id)
        doc["tasks"] = [task for task in doc["tasks"] if task["id"] != task_id]
        con.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        # Keep stable ordering under strict UNIQUE position and preserve nextId.
        # Gaps are allowed in row positions because reads sort by position.
        return task_id
    return _transaction(file, expected_revision, expected_hash, update, stop_at)
