#!/usr/bin/env python3
"""M10l synthetic normalized SQLite data + atomic task and journal tests."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sqlite3
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[2]
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

store = load(ROOT / "services/projects/ExperimentalTaskSqliteRecordsV2.py",
             "m10l_record_adapter")
v1 = load(ROOT / "services/projects/ExperimentalTaskSqliteStore.py",
          "m10j_snapshot_adapter")
TIME = 1700000000000
serial = 0


def original():
    return {"version": 2, "revision": 0, "nextId": 4, "nextProjectId": 3,
            "nextOperationId": 1,
            "projects": [
                {"id": "p1", "name": "Normal", "family": "normal", "remote": None,
                 "createdAtMs": TIME, "updatedAtMs": TIME, "fields": []},
                {"id": "p2", "name": "Git-linked", "family": "git",
                 "remote": {"provider":"github", "owner":"kudokudo1",
                            "projectNodeId":"PVT_unverified", "projectNumber":14},
                 "createdAtMs": TIME, "updatedAtMs": TIME,
                 "fields":[{"id":"f1", "label":"Review", "kind":"text",
                            "scope":"local"}]}
            ],
            "tasks": [
                {"id":"t1", "projectId":"p1", "title":"Read", "done":False,
                 "createdAtMs":TIME, "updatedAtMs":TIME, "priority":"none",
                 "description":"Keep it local", "dueDate":None, "remote":None,
                 "values":{}},
                {"id":"t3", "projectId":"p2", "title":"Write notes 🏥",
                 "done":False, "createdAtMs":TIME, "updatedAtMs":TIME,
                 "priority":"high", "description":"Private task content",
                 "dueDate":"2026-10-23", "remote":None,
                 "values":{"f1":"Some offline details"}}
            ], "operations":[]}


def denied(fn, reason):
    try:
        fn()
    except (store.StoreError, store.InterruptedCommit, sqlite3.Error) as exc:
        assert reason in str(exc), (reason, str(exc))
        return
    raise AssertionError("Expected refusal: " + reason)


with tempfile.TemporaryDirectory(prefix="pa-m10l-record-fixture-") as td:
    base = Path(td)
    def fresh():
        global serial
        serial += 1
        root = base / str(serial)
        root.mkdir(mode=0o700)
        file = root / "tasks.db"
        assert store.read(file) == {"status":"ABSENT","available":False}
        assert not file.exists()
        starter = original()
        initial = store.initialize(file, starter)
        assert initial["status"] == "LOCAL_COMMITTED"
        assert initial["localSaved"] is True
        assert initial["remoteSent"] is False
        assert stat.S_IMODE(file.stat().st_mode) == 0o600
        return file, starter

    file, starter = fresh()
    assert store.read(file)["document"] == starter
    assert store.read(file)["status"] == "READY"
    denied(lambda: store.initialize(file, starter), "INITIALIZATION_REQUIRES_NEW_DATABASE")
    with sqlite3.connect(file) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 0
        assert "payload" not in [row[1] for row in
            db.execute("PRAGMA table_info(meta)").fetchall()]
        # Any attempted DELETE+REINSERT of existing data must fail. This
        # discriminates real record-level editing from M10j table rebuilds.
        for sql in [
          "CREATE TRIGGER no_project_delete BEFORE DELETE ON projects "
          "BEGIN SELECT RAISE(ABORT,'PROJECT_REWRITE'); END",
          "CREATE TRIGGER no_task_delete BEFORE DELETE ON tasks "
          "BEGIN SELECT RAISE(ABORT,'TASK_REWRITE'); END",
          "CREATE TRIGGER no_op_delete BEFORE DELETE ON operations "
          "BEGIN SELECT RAISE(ABORT,'OP_REWRITE'); END",
          "CREATE TRIGGER no_project_update BEFORE UPDATE ON projects "
          "BEGIN SELECT RAISE(ABORT,'PROJECT_CHANGED'); END",
        ]:
            db.execute(sql)

    baseline = store.read(file)
    updated = store.edit_task(file, expected_revision=baseline["revision"],
                              expected_hash=baseline["hash"], task_id="t3",
                              field="title", value="Write notes offline",
                              now_ms=TIME+1)
    assert updated["status"] == "LOCAL_COMMITTED"
    assert updated["remoteIntentCreated"] is True
    assert updated["remoteWriteAuthorized"] is False
    assert updated["remoteSent"] is False
    after = store.read(file)
    assert after["revision"] == 1
    assert after["document"]["tasks"][1]["title"] == "Write notes offline"
    assert after["document"]["tasks"][1]["updatedAtMs"] == TIME+1
    assert after["document"]["tasks"][1]["values"]["f1"] == "Some offline details"
    assert after["document"]["tasks"][0] == starter["tasks"][0]
    assert after["document"]["operations"][0]["id"] == "op1"
    assert after["document"]["operations"][0]["state"] == "PENDING"
    assert after["document"]["nextOperationId"] == 2
    with sqlite3.connect(file) as db:
        assert db.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 1
        assert db.execute("SELECT title FROM tasks WHERE id='t3'").fetchone()[0] == "Write notes offline"

    # A stale writer cannot overwrite the committed task or duplicate op1.
    denied(lambda: store.edit_task(file, expected_revision=baseline["revision"],
        expected_hash=baseline["hash"], task_id="t3", field="done",
        value=True, now_ms=TIME+2), "STALE_BASELINE")
    assert store.read(file)["document"] == after["document"]
    denied(lambda: store.edit_task(file, expected_revision=after["revision"],
        expected_hash=after["hash"], task_id="t3", field="title",
        value="Write notes offline", now_ms=TIME+2), "NO_CHANGE")
    denied(lambda: store.edit_task(file, expected_revision=after["revision"],
        expected_hash=after["hash"], task_id="t3", field="done",
        value=True, now_ms=TIME-1), "STALE_EDIT_TIME")

    # NORMAL edit does not insert an operation.
    local = store.edit_task(file, expected_revision=after["revision"],
        expected_hash=after["hash"], task_id="t1", field="dueDate",
        value="2026-10-24", now_ms=TIME+2)
    assert local["localSaved"] is True
    assert local["remoteIntentCreated"] is False
    next = store.read(file)
    assert len(next["document"]["operations"]) == 1
    assert next["document"]["tasks"][0]["dueDate"] == "2026-10-24"

    # Explicit operation-state transitions remain LOCAL and unacknowledged.
    send = store.transition_local_operation(file,
        expected_revision=next["revision"], expected_hash=next["hash"],
        operation_id="op1", next_state="SENDING")
    assert send["remoteSent"] is False
    assert send["remoteWriteAuthorized"] is False
    blocked = store.read(file)
    assert blocked["status"] == "RECOVERY_REVIEW"
    assert blocked["blockedOperations"] == ["op1"]
    assert blocked["document"]["operations"][0]["ackToken"] is None
    denied(lambda: store.transition_local_operation(file,
        expected_revision=blocked["revision"], expected_hash=blocked["hash"],
        operation_id="op1", next_state="ACKNOWLEDGED"), "INVALID_TRANSITION_REQUEST")
    unsent = store.transition_local_operation(file,
        expected_revision=blocked["revision"], expected_hash=blocked["hash"],
        operation_id="op1", next_state="UNCERTAIN")
    assert unsent["localSaved"]
    assert store.read(file)["document"]["operations"][0]["state"] == "UNCERTAIN"
    assert store.read(file)["status"] == "RECOVERY_REVIEW"

    # Precommit failures roll back the exact task AND any operation inserts.
    for phase in ("before_task_update", "after_task_update",
                  "after_operation_insert", "before_commit", "after_commit"):
        case_file, case_original = fresh()
        old = store.read(case_file)
        denied(lambda: store.edit_task(case_file,
            expected_revision=old["revision"], expected_hash=old["hash"],
            task_id="t3", field="priority", value="urgent", now_ms=TIME+1,
            stop_at=phase), "INJECTED_"+phase)
        again = store.read(case_file)
        applied = phase == "after_commit"
        assert again["revision"] == (1 if applied else 0), phase
        assert again["document"]["tasks"][1]["priority"] == (
            "urgent" if applied else "high"), phase
        assert len(again["document"]["operations"]) == (1 if applied else 0), phase
        assert again["document"]["nextOperationId"] == (2 if applied else 1), phase
        if applied:
            denied(lambda: store.edit_task(case_file,
                expected_revision=old["revision"], expected_hash=old["hash"],
                task_id="t3", field="priority", value="urgent", now_ms=TIME+1),
                "STALE_BASELINE")

    # Operation transitions also commit a single row and revision together.
    case_file,_ = fresh()
    first = store.read(case_file)
    store.edit_task(case_file, expected_revision=first["revision"],
        expected_hash=first["hash"], task_id="t3", field="done",
        value=True, now_ms=TIME+1)
    op_baseline = store.read(case_file)
    denied(lambda: store.transition_local_operation(case_file,
        expected_revision=op_baseline["revision"],
        expected_hash=op_baseline["hash"], operation_id="op1",
        next_state="SENDING", stop_at="after_operation_update"),
        "INJECTED_after_operation_update")
    assert store.read(case_file)["document"]["operations"][0]["state"] == "PENDING"
    denied(lambda: store.transition_local_operation(case_file,
        expected_revision=op_baseline["revision"],
        expected_hash=op_baseline["hash"], operation_id="op1",
        next_state="SENDING", stop_at="after_commit"),
        "INJECTED_after_commit")
    assert store.read(case_file)["document"]["operations"][0]["state"] == "SENDING"
    assert store.read(case_file)["status"] == "RECOVERY_REVIEW"

    # Unsupported snapshot schema 1 cannot be opened as normalized v2.
    older_dir=base / "older"
    older_dir.mkdir(mode=0o700)
    older_path=older_dir / "tasks.db"
    v1.commit(older_path, original())
    denied(lambda: store.read(older_path), "UNSUPPORTED_SQLITE_SCHEMA")

    # A non-cooperative SQL modification is detected by the persisted
    # content hash; no silent repair or empty-list fallback.
    corrupt_file,_ = fresh()
    with sqlite3.connect(corrupt_file) as sql:
        sql.execute("UPDATE tasks SET title='corrupted' WHERE id='t3'")
    denied(lambda: store.read(corrupt_file), "MODEL_HASH_MISMATCH")

    # No default, no activation. A writable call against absent DB MUST NOT
    # create the file (only explicit initialize is allowed).
    missing=base / "not_here"
    missing.mkdir(mode=0o700)
    absent=missing / "tasks.db"
    denied(lambda: store.edit_task(absent,
        expected_revision=0,expected_hash="0"*64,task_id="t1",
        field="title",value="No",now_ms=TIME), "DATABASE_ABSENT")
    assert not absent.exists()
    assert not hasattr(store, "send_github")
    assert not hasattr(store, "migrate_live_data")

print("TASKS M10l normalized SQLite record writes and journal recovery: PASS")
