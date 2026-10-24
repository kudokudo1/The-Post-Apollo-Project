#!/usr/bin/env python3
"""M10u test-only SQLite LOCAL custom fields, including on GIT projects.

No live writer, CLI, default data directory, migration or GitHub transport.
ProjectV2 custom fields have scope='local', never a remote ProjectV2 mapping.
Uses M10s guarded revision/hash/SQLite transaction and M10l schema validation.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "m10u_normal_crud", HERE / "ExperimentalTaskSqliteCrudM10s.py")
crud = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crud)
records = crud.records
StoreError = crud.StoreError
InterruptedCommit = crud.InterruptedCommit


def _project(doc, project_id):
    project = next((p for p in doc["projects"] if p["id"] == project_id), None)
    if project is None:
        raise StoreError("UNKNOWN_PROJECT")
    # GIT project identity is *only metadata* here; field scope is local.
    # No remote service, mapping, journal dispatch or ACK is authorized.
    return project


def _allow_local_operation(doc):
    # Do not make even a local mutation while remote effects may be unresolved.
    if any(op["state"] in records.BLOCKED for op in doc["operations"]):
        raise StoreError("RECOVERY_REVIEW_REQUIRED")


def add_local_field(file, *, expected_revision, expected_hash,
                    project_id, label, kind, now_ms, stop_at=None):
    """Append typed LOCAL field metadata in one transaction, NORMAL or GIT."""
    validate = records._validator
    if not (type(project_id) is str
            and validate._identifier(project_id, "p")
            and validate._text(label, 64, True)
            and kind in validate.KINDS and type(kind) is str
            and crud._timestamp(now_ms)):
        raise StoreError("INVALID_FIELD_REQUEST")

    def update(con, doc):
        _allow_local_operation(doc)
        project = _project(doc, project_id)
        fields = project["fields"]
        if len(fields) >= 24:
            raise StoreError("FIELD_CAPACITY")
        if any(f["label"].lower() == label.lower() for f in fields):
            raise StoreError("DUPLICATE_FIELD_LABEL")
        if now_ms < project["updatedAtMs"] or project["updatedAtMs"] >= crud.MAX_MS:
            raise StoreError("STALE_EDIT_TIME")
        max_field = max((int(f["id"][1:]) for f in fields), default=0)
        if max_field >= 1000000000:
            raise StoreError("FIELD_ID_EXHAUSTED")
        field_id = "f" + str(max_field + 1)
        fields.append({"id":field_id,"label":label,"kind":kind,"scope":"local"})
        project["updatedAtMs"] = max(now_ms, project["updatedAtMs"] + 1)
        con.execute("UPDATE projects SET fields_json=?,updated_ms=? WHERE id=?",
                    (records._json(fields), project["updatedAtMs"], project_id))
        return field_id

    return crud._transaction(file, expected_revision, expected_hash,
                             update, stop_at)


def edit_local_value(file, *, expected_revision, expected_hash,
                     task_id, field_id, value, now_ms, stop_at=None):
    """Atomic local-only typed value update. Never appends a GitHub operation."""
    validate = records._validator
    if not (type(task_id) is str and validate._identifier(task_id, "t")
            and type(field_id) is str and validate._identifier(field_id, "f")
            and crud._timestamp(now_ms)):
        raise StoreError("INVALID_CUSTOM_EDIT")

    def update(con, doc):
        _allow_local_operation(doc)
        task = next((t for t in doc["tasks"] if t["id"] == task_id), None)
        if task is None:
            raise StoreError("UNKNOWN_TASK")
        if task["projectId"] is None:
            raise StoreError("NO_PROJECT_FOR_CUSTOM_VALUE")
        project = _project(doc, task["projectId"])
        definition = next((f for f in project["fields"]
                           if f["id"] == field_id), None)
        if definition is None:
            raise StoreError("UNKNOWN_CUSTOM_FIELD")
        if definition["scope"] != "local":
            raise StoreError("UNSUPPORTED_FIELD_SCOPE")
        if not validate._custom_value(definition["kind"], value):
            raise StoreError("INVALID_CUSTOM_VALUE")
        if field_id in task["values"] and task["values"][field_id] == value:
            raise StoreError("NO_CHANGE")
        if now_ms < task["updatedAtMs"] or task["updatedAtMs"] >= crud.MAX_MS:
            raise StoreError("STALE_EDIT_TIME")
        task["values"][field_id] = value
        task["updatedAtMs"] = max(now_ms, task["updatedAtMs"] + 1)
        con.execute("UPDATE tasks SET values_json=?,updated_ms=? WHERE id=?",
                    (records._json(task["values"]), task["updatedAtMs"], task_id))
        return task_id

    return crud._transaction(file, expected_revision, expected_hash,
                             update, stop_at)
