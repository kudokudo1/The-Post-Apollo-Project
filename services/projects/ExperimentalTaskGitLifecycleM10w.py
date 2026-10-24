#!/usr/bin/env python3
"""M10w pure, review-only GIT lifecycle intent proposals.

An intentionally SEPARATE proposed journal protocol, NOT v2 persisted schema.
No default path, database connection, QML mount, remote service, execution,
dispatch, migration, or authorization. Source model v2 is NEVER mutated.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "m10w_v2_validator", _HERE / "ExperimentalTaskSqliteRecordsV2.py")
records = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(records)
StoreError = records.StoreError

PREVIEW_VERSION = 1
PROPOSED_JOURNAL_VERSION = 3  # Design label only; NO migration or v3 serializer.
KINDS = ("CREATE_GIT_TASK", "DELETE_GIT_TASK", "MOVE_GIT_TASK")
_COMMON = ("kind", "taskId")
_SHAPES = {
    "CREATE_GIT_TASK": frozenset(_COMMON),
    "DELETE_GIT_TASK": frozenset((*_COMMON, "confirmed")),
    "MOVE_GIT_TASK": frozenset((*_COMMON, "targetProjectId")),
}
_GLOBAL_GATES = ("VERSIONED_JOURNAL_MIGRATION",
                 "EXPLICIT_OPERATOR_APPROVAL",
                 "FRESH_REMOTE_IDENTITY_AND_BASELINE",
                 "VERIFIED_PERMISSION_AND_REMOTE_READBACK")
_KIND_GATES = {
    "CREATE_GIT_TASK": ("REMOTE_CREATE_IDEMPOTENCY_AND_IDENTITY_BINDING",
                        "DEPENDENT_EDITS_AND_RESTART_RECOVERY"),
    "DELETE_GIT_TASK": ("REMOTE_ARCHIVE_VS_DELETE_POLICY",
                        "DELETION_RECOVERY_AND_TOMBSTONE_RETENTION"),
    "MOVE_GIT_TASK": ("REMOTE_CROSS_PROJECT_MOVE_POLICY",
                      "TARGET_FIELD_MAPPING_AND_ROLLBACK"),
}


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(obj):
    return hashlib.sha256(_canonical(obj)).hexdigest()


def _task(doc, task_id):
    return next((task for task in doc["tasks"] if task["id"] == task_id), None)


def _project(doc, project_id):
    return next((project for project in doc["projects"]
                 if project["id"] == project_id), None)


def _validate(doc, request):
    records._validator.validate(doc)  # Strict full v2 model, not a subset.
    if type(request) is not dict or type(request.get("kind")) is not str:
        raise StoreError("INVALID_LIFECYCLE_REQUEST")
    kind = request["kind"]
    if kind not in _SHAPES or set(request) != _SHAPES[kind]:
        raise StoreError("INVALID_LIFECYCLE_REQUEST")
    task_id = request["taskId"]
    if (type(task_id) is not str or
            not records._validator._identifier(task_id, "t")):
        raise StoreError("INVALID_TASK_ID")
    task = _task(doc, task_id)
    if task is None:
        raise StoreError("UNKNOWN_TASK")
    project = _project(doc, task["projectId"])
    if project is None or project["family"] != "git":
        raise StoreError("GIT_PROJECT_REQUIRED")
    # No assumption that remote metadata is verified just because it exists.
    if project["remote"] is None:
        raise StoreError("GIT_PROJECT_REFERENCE_MISSING")
    if any(op["state"] in records.BLOCKED for op in doc["operations"]):
        raise StoreError("RECOVERY_REVIEW_REQUIRED")
    if any(op["taskId"] == task_id and op["state"] != "ACKNOWLEDGED"
           for op in doc["operations"]):
        raise StoreError("TASK_DEPENDENCY_REVIEW_REQUIRED")
    if len(doc["operations"]) >= 1000 or doc["nextOperationId"] >= 1000000000:
        raise StoreError("JOURNAL_CAPACITY_REVIEW_REQUIRED")
    if doc["revision"] >= 1000000000:
        raise StoreError("REVISION_EXHAUSTED")

    if kind == "CREATE_GIT_TASK":
        if task["remote"] is not None:
            raise StoreError("TASK_ALREADY_HAS_REMOTE_REFERENCE")
    elif kind == "DELETE_GIT_TASK":
        if request["confirmed"] is not True:
            raise StoreError("DELETE_CONFIRMATION_REQUIRED")
        if task["remote"] is None:
            raise StoreError("REMOTE_DELETE_IDENTITY_REQUIRED")
    else:
        dest = request["targetProjectId"]
        if (type(dest) is not str or
                not records._validator._identifier(dest, "p")):
            raise StoreError("INVALID_TARGET_PROJECT")
        target = _project(doc, dest)
        if target is None:
            raise StoreError("UNKNOWN_TARGET_PROJECT")
        if target["id"] == project["id"]:
            raise StoreError("NO_CHANGE")
        if target["family"] != "git" or target["remote"] is None:
            raise StoreError("CROSS_FAMILY_MOVE_UNSUPPORTED")
        if task["remote"] is None:
            raise StoreError("REMOTE_MOVE_IDENTITY_REQUIRED")
        if task["values"]:
            # An existing local fN key can refer to a different field in
            # the target project. Never discard or reinterpret these values.
            raise StoreError("LOCAL_FIELD_TRANSFER_POLICY_REQUIRED")
    return task, project


def propose(doc, request):
    """Return immutable-in-practice review data; no write/remote readiness.

    The proposedOperationId is NOT reserved. This cannot be inserted into
    the v2 operations table, whose FK requires a live task and standard field.
    """
    task, project = _validate(doc, request)
    kind = request["kind"]
    proposed = {
        "previewVersion": PREVIEW_VERSION,
        "proposedJournalVersion": PROPOSED_JOURNAL_VERSION,
        "kind": kind,
        "sourceModelVersion": doc["version"],
        "expectedRevision": doc["revision"],
        "expectedModelHash": records._hash(doc),
        "taskId": task["id"],
        "sourceProjectId": project["id"],
        "targetProjectId": request.get("targetProjectId"),
        "proposedOperationId": "op" + str(doc["nextOperationId"]),
        "existingOperationIds": [op["id"] for op in doc["operations"]],
        "taskBefore": copy.deepcopy(task),
        "projectReferenceBefore": copy.deepcopy(project["remote"]),
        "targetProjectReference": (
            copy.deepcopy(_project(doc, request["targetProjectId"])["remote"])
            if kind == "MOVE_GIT_TASK" else None),
        "requiredGates": list(_GLOBAL_GATES + _KIND_GATES[kind]),
        "status": "REVIEW_ONLY",
        "localWriteAuthorized": False,
        "journalWriteAuthorized": False,
        "remoteWriteAuthorized": False,
        "remoteSent": False,
        "remoteAcknowledged": False,
    }
    proposed["fingerprint"] = _hash(proposed)  # Integrity hint, NOT a signature.
    return proposed


def review_current(doc, request, previous):
    """Only exact fresh re-derivation may confirm a nonstale review preview.

    Does not become executable when true, and does not reserve an operation ID.
    """
    if type(previous) is not dict:
        return {"current": False, "reason": "INVALID_PREVIEW"}
    try:
        current = propose(doc, request)
    except (StoreError, ValueError, TypeError):
        return {"current": False, "reason": "PREVIEW_INVALID_OR_STALE"}
    if current != previous:
        return {"current": False, "reason": "PREVIEW_INVALID_OR_STALE"}
    return {"current": True, "reason": "PREVIEW_MATCHES_ONLY",
            "localWriteAuthorized": False,
            "journalWriteAuthorized": False,
            "remoteWriteAuthorized": False}
