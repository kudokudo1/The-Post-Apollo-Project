#!/usr/bin/env python3
"""M10j SQLite tests only in user-unrelated disposable tempfile roots."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "services/projects/ExperimentalTaskSqliteStore.py"
spec = importlib.util.spec_from_file_location("sqlite_tasks_prototype", PATH)
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)
TIME = 1700000000000


def fixture():
    return {
        "version": 2, "revision": 0, "nextId": 45,
        "nextProjectId": 3, "nextOperationId": 1,
        "projects": [
            {"id": "p1", "name": "Local", "family": "normal", "remote": None,
             "createdAtMs": TIME, "updatedAtMs": TIME, "fields": []},
            {"id": "p2", "name": "Git Research", "family": "git",
             "remote": {"provider": "github", "owner": "kudokudo1",
                        "projectNodeId": "PVT_not_verified", "projectNumber": 12},
             "createdAtMs": TIME, "updatedAtMs": TIME,
             "fields": [{"id": "f1", "label": "Budget", "kind": "number",
                         "scope": "local"}]},
        ],
        "tasks": [
            {"id": "t1", "title": "Read", "done": False, "projectId": "p1",
             "createdAtMs": TIME, "updatedAtMs": TIME,
             "priority": "none", "description": "Unscheduled local task",
             "dueDate": None, "remote": None, "values": {}},
            {"id": "t44", "title": "Plan dates", "done": False, "projectId": "p2",
             "createdAtMs": TIME, "updatedAtMs": TIME,
             "priority": "high", "description": "unicode 🏥 example",
             "dueDate": "2026-10-23", "remote": None, "values": {"f1": 512.25}},
        ],
        "operations": [],
    }


def candidate(previous, *, field="title", value="Plan dates offline"):
    after = copy.deepcopy(previous)
    t = after["tasks"][1]
    old = t[field]
    t[field] = value
    t["updatedAtMs"] += 1
    after["revision"] += 1
    op_id = "op" + str(after["nextOperationId"])
    after["nextOperationId"] += 1
    after["operations"].append({
        "id": op_id, "taskId": "t44", "projectId": "p2",
        "field": field, "before": old, "after": value,
        "createdRevision": after["revision"], "state": "PENDING",
        "ackToken": None
    })
    return after


def expect_error(operation, part):
    try:
        operation()
    except (store.StoreError, store.InterruptedCommit, sqlite3.Error) as e:
        assert part in str(e), (part, str(e))
        return
    raise AssertionError("expected failure " + part)


def same_payload(expected, result):
    assert result["available"], result
    assert result["document"] == expected
    assert result["revision"] == expected["revision"]


with tempfile.TemporaryDirectory(prefix="pa-task-sqlite-m10j-") as temp:
    root = Path(temp)
    path = root / "tasks.db"
    invalid = root / "does-not-exist" / "tasks.db"

    # Read-only query never creates absent file or directory.
    assert store.read(invalid) == {"status": "ABSENT", "available": False}
    assert not invalid.parent.exists()
    assert store.read(path) == {"status": "ABSENT", "available": False}
    assert not path.exists()
    assert store.connect(path, initialize=False) is None

    original = fixture()
    before = json.dumps(original, sort_keys=True)
    assert store.validate(original)
    result = store.commit(path, original)
    assert result["status"] == "LOCAL_COMMITTED"
    assert result["localSaved"] is True
    assert result["remoteSent"] is False
    assert result["remoteWriteAuthorized"] is False
    assert path.is_file()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not original["operations"]
    assert json.dumps(original, sort_keys=True) == before

    current = store.read(path)
    assert current["status"] == "READY"
    same_payload(original, current)
    assert current["blockedOperations"] == []
    with store.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 1
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 0
    expect_error(lambda: store.commit(path, original), "INITIAL_BASELINE")
    proposed = candidate(original)
    assert store.validate(proposed)
    commit = store.commit(path, proposed,
                          expected_revision=current["revision"],
                          expected_hash=current["hash"])
    assert commit["localSaved"]
    latest = store.read(path)
    same_payload(proposed, latest)
    assert latest["document"]["tasks"][1]["updatedAtMs"] == TIME + 1
    assert latest["document"]["tasks"][1]["values"]["f1"] == 512.25
    assert latest["document"]["operations"][0]["state"] == "PENDING"
    with store.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 1
        assert con.execute("SELECT task_id,state FROM operations").fetchone()[:] == ("t44", "PENDING")
        assert con.execute("SELECT due_date FROM tasks WHERE task_id='t44'").fetchone()[0] == "2026-10-23"

    # Two callers who read revision zero cannot both commit their first edit.
    expect_error(lambda: store.commit(
        path, candidate(original, value="Racing other writer"),
        expected_revision=current["revision"], expected_hash=current["hash"]
    ), "STALE_BASELINE")
    assert store.read(path)["document"] == proposed
    expect_error(lambda: store.commit(path, proposed,
        expected_revision=latest["revision"], expected_hash=latest["hash"]),
        "REVISION_STEP_REQUIRED")

    # Simulated error before SQL COMMIT rolls back ALL related tables.
    for stop_at in ("before_begin", "after_begin", "after_projects",
                    "after_tasks", "after_operations", "before_commit"):
        snapshot = store.read(path)
        next_doc = candidate(snapshot["document"], field="description",
                             value="Test stage " + stop_at)
        expect_error(lambda: store.commit(path, next_doc,
            expected_revision=snapshot["revision"], expected_hash=snapshot["hash"],
            stop_at=stop_at), stop_at)
        reloaded = store.read(path)
        assert reloaded["hash"] == snapshot["hash"], stop_at
        same_payload(snapshot["document"], reloaded)
        assert len(reloaded["document"]["operations"]) == 1

    # A post-COMMIT exception has an uncertain caller result, while reopening
    # discovers the complete new task+journal in a single SQLite transaction.
    previous = store.read(path)
    next_doc = candidate(previous["document"], field="done", value=True)
    expect_error(lambda: store.commit(
        path, next_doc, expected_revision=previous["revision"],
        expected_hash=previous["hash"], stop_at="after_commit"), "after_commit")
    reboot = store.read(path)
    same_payload(next_doc, reboot)
    assert len(reboot["document"]["operations"]) == 2
    assert reboot["document"]["operations"][1]["field"] == "done"
    assert reboot["document"]["operations"][1]["state"] == "PENDING"
    assert reboot["document"]["tasks"][1]["done"]
    assert reboot["hash"] != previous["hash"]

    # SENDING survived restart -> block remote dispatch, do not fabricate ACK.
    sending = copy.deepcopy(next_doc)
    sending["revision"] += 1
    sending["operations"][0]["state"] = "SENDING"
    store.commit(path, sending,
        expected_revision=reboot["revision"], expected_hash=reboot["hash"])
    restart = store.read(path)
    assert restart["status"] == "RECOVERY_REVIEW"
    assert restart["blockedOperations"] == ["op1"]
    assert restart["document"]["operations"][0]["state"] == "SENDING"
    assert not restart["document"]["operations"][0]["ackToken"]
    assert not hasattr(store, "send_github")

    # Do not permit future schema, unknown keys, malformed references.
    for mutation in (
        lambda x: x.update(version=3),
        lambda x: x.update(unrecognized="drop me"),
        lambda x: x["tasks"][1].update(dueDate="2026-02-29"),
        lambda x: x["tasks"][1]["values"].update(f99=42),
        lambda x: x["projects"][1].update(remote={"provider": "github"}),
        lambda x: x["operations"][1].update(state="ACKNOWLEDGED")
    ):
        bad = copy.deepcopy(sending)
        mutation(bad)
        expect_error(lambda: store.validate(bad), "INVALID")

    # Inspect corruption without repairing it. Atomic transaction refuses
    # to overwrite even if another process damages indexed summary rows.
    con = store.connect(path, initialize=True)
    try:
        with con:
            con.execute("DELETE FROM operations WHERE operation_id='op2'")
    finally:
        con.close()
    expect_error(lambda: store.read(path), "INDEX_DIVERGENCE")
    expect_error(lambda: store.commit(path, candidate(sending),
            expected_revision=restart["revision"],
            expected_hash=restart["hash"]), "INDEX_DIVERGENCE")

    # A different test DB protects the custom NORMAL-only edit path.
    second = root / "local" 
    second.mkdir(mode=0o700)
    local_file = second / "tasks.db"
    first_result = store.commit(local_file, original)
    assert first_result["localSaved"]
    local_snap = store.read(local_file)
    normal = copy.deepcopy(original)
    normal["revision"] = 1
    normal["tasks"][0]["done"] = True
    normal["tasks"][0]["updatedAtMs"] += 1
    store.commit(local_file, normal, expected_revision=local_snap["revision"],
                 expected_hash=local_snap["hash"])
    assert store.read(local_file)["document"]["operations"] == []
    assert store.read(local_file)["document"]["tasks"][0]["done"] is True

    # Source tree contains NO call sites for this prototype, only tests.
    source = PATH.read_text()
    assert "Quickshell.dataDir" not in source
    assert "GitHubProjectsService" not in source
    assert "process.env.HOME" not in source
    assert not (root / "hospital.db").exists()

print("TASKS M10j experimental SQLite atomic snapshot+journal and restart tests: PASS")
