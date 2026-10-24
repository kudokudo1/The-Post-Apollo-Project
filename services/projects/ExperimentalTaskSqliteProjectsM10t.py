#!/usr/bin/env python3
"""M10t NORMAL project lifecycle for disposable SQLite v2 tests ONLY.

No CLI/default database path, QML mount, migration, or remote operations.
Real TASKS still uses ApolloHubTodoStore.qml and the JSON writer.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "m10t_normal_crud", HERE / "ExperimentalTaskSqliteCrudM10s.py")
crud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crud)
records = crud.records
StoreError = crud.StoreError
InterruptedCommit = crud.InterruptedCommit


def rename_normal_project(file, *, expected_revision, expected_hash,
                          project_id, name, now_ms, stop_at=None):
    """Rename only a NORMAL project; duplicate names fail without mutation."""
    if not (type(project_id) is str
            and records._validator._identifier(project_id, "p")
            and records._validator._text(name, 64, True)
            and crud._timestamp(now_ms)):
        raise StoreError("INVALID_PROJECT_RENAME")

    def update(con, doc):
        project = crud._normal_project(doc, project_id)
        if project["name"] == name:
            raise StoreError("NO_CHANGE")
        if any(p["id"] != project_id and p["name"].lower() == name.lower()
               for p in doc["projects"]):
            raise StoreError("PROJECT_NAME_CONFLICT")
        if now_ms < project["updatedAtMs"] or project["updatedAtMs"] >= crud.MAX_MS:
            raise StoreError("STALE_EDIT_TIME")
        project["name"] = name
        project["updatedAtMs"] = max(now_ms, project["updatedAtMs"] + 1)
        con.execute("UPDATE projects SET name=?,updated_ms=? WHERE id=?",
                    (name, project["updatedAtMs"], project_id))
        return project_id

    return crud._transaction(file, expected_revision, expected_hash,
                             update, stop_at)


def delete_normal_project(file, *, expected_revision, expected_hash,
                          project_id, confirmed, now_ms, stop_at=None):
    """Atomically detach ordinary tasks and remove NORMAL project.

    Refuse projects holding custom field definitions, tasks with remote/custom
    values, any operations referencing the project/tasks, or GIT projects.
    Existing task content, IDs, dates, and completion are never removed.
    """
    if not (confirmed is True and type(project_id) is str
            and records._validator._identifier(project_id, "p")
            and crud._timestamp(now_ms)):
        raise StoreError("DELETE_NOT_CONFIRMED")

    def update(con, doc):
        project = crud._normal_project(doc, project_id)
        if project["fields"]:
            raise StoreError("PROJECT_CUSTOM_FIELDS_REQUIRE_REVIEW")
        if now_ms < project["updatedAtMs"]:
            raise StoreError("STALE_EDIT_TIME")
        tasks = [t for t in doc["tasks"] if t["projectId"] == project_id]
        ids = {t["id"] for t in tasks}
        if any(op["projectId"] == project_id or op["taskId"] in ids
               for op in doc["operations"]):
            raise StoreError("PROJECT_JOURNAL_REQUIRES_REVIEW")
        for t in tasks:
            if t["remote"] is not None or t["values"]:
                raise StoreError("TASK_REMOTE_OR_CUSTOM_DATA_REQUIRES_REVIEW")
            if now_ms < t["updatedAtMs"] or t["updatedAtMs"] >= crud.MAX_MS:
                raise StoreError("STALE_EDIT_TIME")

        for t in tasks:
            # Update rows while retaining all properties unrelated to
            # ownership and the necessary monotonically increasing timestamp.
            t["projectId"] = None
            t["updatedAtMs"] = max(now_ms, t["updatedAtMs"] + 1)
            con.execute(
                "UPDATE tasks SET project_id=NULL,updated_ms=? WHERE id=?",
                (t["updatedAtMs"], t["id"]))
        doc["projects"] = [p for p in doc["projects"] if p["id"] != project_id]
        con.execute("DELETE FROM projects WHERE id=?", (project_id,))
        # No tasks/operations discarded; project counters never move backward.
        return project_id

    return crud._transaction(file, expected_revision, expected_hash,
                             update, stop_at)
