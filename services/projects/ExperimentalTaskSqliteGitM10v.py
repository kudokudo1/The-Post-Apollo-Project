#!/usr/bin/env python3
"""M10v GIT task standard-field edits + ordered local pending intents.

DISPOSABLE SQLITE TESTS ONLY. No default path, CLI, Quickshell writer, GitHub
transport, remote identity verification, ACK, live migration, or automatic retry.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "m10v_record_backend", HERE / "ExperimentalTaskSqliteRecordsV2.py")
records = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(records)
StoreError = records.StoreError
InterruptedCommit = records.InterruptedCommit

_COLUMNS = {
    "title": "title", "done": "done", "priority": "priority",
    "description": "description", "dueDate": "due_date",
}
_ORDER = records.FIELDS
MAX_REVISION = 1000000000


def edit_git_task_fields(file, *, expected_revision, expected_hash,
                         task_id, changes, now_ms, stop_at=None):
    """Atomically store changed GIT fields + ordered PENDING operations.

    Each changed field consumes one distinct model revision and one stable
    operation ID, even though all fields and journal entries commit together.
    The current v2 validator REQUIRES strictly increasing createdRevision.
    """
    validator = records._validator
    if not (type(expected_revision) is int and expected_revision >= 0
            and type(expected_hash) is str
            and re.fullmatch(r"[0-9a-f]{64}", expected_hash) is not None
            and type(task_id) is str
            and validator._identifier(task_id, "t")
            and type(changes) is dict and 1 <= len(changes) <= len(_ORDER)
            and all(key in _ORDER and validator._task_value(key, val)
                    for key, val in changes.items())
            and type(now_ms) is int and 1 <= now_ms <= records.MAX_SAFE_MS):
        raise StoreError("INVALID_GIT_EDIT")

    con = records._connect(file, writable=True)
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            baseline = records._load(con)
            if (baseline["revision"] != expected_revision
                    or baseline["hash"] != expected_hash):
                raise StoreError("STALE_BASELINE")
            original = baseline["document"]
            if any(op["state"] in records.BLOCKED for op in original["operations"]):
                raise StoreError("RECOVERY_REVIEW_REQUIRED")

            task = next((t for t in original["tasks"] if t["id"] == task_id), None)
            if task is None:
                raise StoreError("UNKNOWN_TASK")
            project = next((p for p in original["projects"]
                            if p["id"] == task["projectId"]), None)
            if project is None or project["family"] != "git":
                raise StoreError("GIT_PROJECT_REQUIRED")
            # Synthetic GIT identity is unverified. Store only local intent.
            if project["remote"] is None:
                raise StoreError("GIT_PROJECT_METADATA_REQUIRED")
            if now_ms < task["updatedAtMs"] or task["updatedAtMs"] >= records.MAX_SAFE_MS:
                raise StoreError("STALE_EDIT_TIME")

            changed = [key for key in _ORDER
                       if key in changes and task[key] != changes[key]]
            if not changed:
                raise StoreError("NO_CHANGE")
            count = len(changed)
            if original["revision"] + count > MAX_REVISION:
                raise StoreError("REVISION_EXHAUSTED")
            if (len(original["operations"]) + count > 1000 or
                    original["nextOperationId"] + count > MAX_REVISION):
                raise StoreError("OPERATION_QUEUE_FULL")

            candidate = copy.deepcopy(original)
            entry = next(t for t in candidate["tasks"] if t["id"] == task_id)
            entry["updatedAtMs"] = max(now_ms, task["updatedAtMs"] + 1)
            operations = []
            for index, field in enumerate(changed):
                before = entry[field]
                after = changes[field]
                entry[field] = after
                operations.append({
                    "id": "op" + str(candidate["nextOperationId"] + index),
                    "taskId": task_id, "projectId": project["id"],
                    "field": field, "before": before, "after": after,
                    "createdRevision": original["revision"] + index + 1,
                    "state": "PENDING", "ackToken": None})
            candidate["revision"] += count
            candidate["nextOperationId"] += count
            candidate["operations"].extend(operations)
            validator.validate(candidate)

            records._stop(stop_at, "before_task_update")
            assignments = [(_COLUMNS[field], int(entry[field])
                            if field == "done" else entry[field])
                           for field in changed]
            sql = ("UPDATE tasks SET " +
                   ",".join(col+"=?" for col, _ in assignments) +
                   ",updated_ms=? WHERE id=?")
            con.execute(sql, [value for _, value in assignments] +
                        [entry["updatedAtMs"], task_id])
            records._stop(stop_at, "after_task_update")

            next_position = con.execute(
                "SELECT COALESCE(MAX(position),-1)+1 FROM operations").fetchone()[0]
            for offset, operation in enumerate(operations):
                records._insert_operation(con, operation, next_position + offset)
                if offset == 0:
                    records._stop(stop_at, "after_first_operation_insert")
            records._stop(stop_at, "after_operation_insert")

            digest = records._hash(candidate)
            con.execute(
                "UPDATE meta SET revision=?,next_operation_id=?,model_hash=? "
                "WHERE singleton=1",
                (candidate["revision"], candidate["nextOperationId"], digest))
            records._stop(stop_at, "before_commit")
            con.commit()
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise

        # Post-commit interruption is ambiguous. Caller must fresh-read first;
        # NEVER blindly append a duplicate operation or infer remote success.
        records._stop(stop_at, "after_commit")
        confirmed = records._load(con)
        if confirmed["document"] != candidate or confirmed["hash"] != digest:
            raise StoreError("POST_COMMIT_VERIFICATION_FAILED")
        return {
            "status": "LOCAL_COMMITTED", "localSaved": True,
            "remoteSent": False, "remoteWriteAuthorized": False,
            "remoteIntentCreated": True,
            "operationIds": [op["id"] for op in operations],
            "revision": candidate["revision"], "hash": digest}
    finally:
        con.close()
