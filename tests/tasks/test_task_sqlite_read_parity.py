#!/usr/bin/env python3
"""M10k pure JS/Python v2 validation parity and explicit read-probe contracts."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "services/projects/ExperimentalTaskSqliteStore.py"
PROBE = ROOT / "services/projects/TaskSqliteReadProbe.py"
ORACLE = ROOT / "tests/tasks/fixtures/model_v2_parity_oracle.cjs"
QML = ROOT / "services/projects/TaskSqliteReadBridge.qml"

spec = importlib.util.spec_from_file_location("tasks_parity_sqlite", ADAPTER)
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)
M = 1700000000000


def baseline():
    return {"version": 2, "revision": 1, "nextId": 3, "nextProjectId": 3,
            "nextOperationId": 2,
            "projects": [
                {"id": "p1", "name": "Personal", "family": "normal",
                 "remote": None, "fields": [],
                 "createdAtMs": M, "updatedAtMs": M},
                {"id": "p2", "name": "Development", "family": "git",
                 "remote": {"provider": "github", "owner": "kudokudo1",
                            "projectNodeId": "PVT_unverified",
                            "projectNumber": 12},
                 "fields": [
                     {"id": "f1", "label": "Cost", "kind": "number", "scope": "local"},
                     {"id": "f2", "label": "Notes", "kind": "text", "scope": "local"}],
                 "createdAtMs": M, "updatedAtMs": M + 2}
            ],
            "tasks": [
                {"id": "t1", "projectId": "p1", "remote": None,
                 "title": "Read", "done": False, "priority": "none",
                 "description": "", "dueDate": None, "values": {},
                 "createdAtMs": M, "updatedAtMs": M},
                {"id": "t2", "projectId": "p2",
                 "remote": {"projectItemNodeId": "PVTI_unverified",
                            "contentKind": "ISSUE",
                            "contentNodeId": "I_unverified"},
                 "title": "Implement", "done": False, "priority": "high",
                 "description": "Offline first", "dueDate": "2026-10-23",
                 "values": {"f1": 125.25, "f2": "Schedule\nReview"},
                 "createdAtMs": M, "updatedAtMs": M + 3}
            ],
            "operations": [
                {"id": "op1", "taskId": "t2", "projectId": "p2",
                 "field": "priority", "before": "none", "after": "high",
                 "createdRevision": 1, "state": "PENDING", "ackToken": None}
            ]}


fixtures = []
def case(label, alter=None, source=None):
    candidate = copy.deepcopy(baseline() if source is None else source)
    if alter:
        alter(candidate)
    fixtures.append((label, candidate))


case("valid_full")
case("valid_empty", source={"version":2,"revision":0,"nextId":1,
                            "nextProjectId":1,"nextOperationId":1,
                            "projects":[],"tasks":[],"operations":[]})
case("valid_null_custom", lambda x: x["tasks"][1]["values"].update(f1=None))
case("valid_unicode", lambda x: x["tasks"][0].update(title="Café"))
case("valid_leap_day", lambda x: x["tasks"][1].update(dueDate="2024-02-29"))
case("valid_draft_item", lambda x: x["tasks"][1].update(
    remote={"projectItemNodeId":"PVTI_unverified",
            "contentKind":"DRAFT_ISSUE","contentNodeId":None}))
case("valid_pending_conflict", lambda x: x["operations"][0].update(state="UNCERTAIN"))
case("invalid_schema", lambda x: x.update(version=3))
case("invalid_extra_root", lambda x: x.update(unseen=True))
case("invalid_extra_task", lambda x: x["tasks"][0].update(unseen="lost"))
case("invalid_extra_project", lambda x: x["projects"][0].update(wat=1))
case("invalid_counter", lambda x: x.update(nextId=2))
case("invalid_revision", lambda x: x.update(revision=0))
case("invalid_bool_rev", lambda x: x.update(revision=True))
case("invalid_duplicate_project", lambda x: x["projects"][1].update(id="p1"))
case("invalid_duplicate_project_name", lambda x: x["projects"][1].update(name="PERSONAL"))
case("invalid_unverified_remote_shape", lambda x: x["projects"][1]["remote"].update(provider="gitlab"))
case("invalid_normal_remote", lambda x: x["projects"][0].update(remote=x["projects"][1]["remote"]))
case("invalid_remote_item_kind", lambda x: x["tasks"][1]["remote"].update(contentKind="REPO"))
case("invalid_wrong_custom_number", lambda x: x["tasks"][1]["values"].update(f1="not a number"))
case("invalid_unknown_field", lambda x: x["tasks"][1]["values"].update(f99=1))
case("invalid_null_project_custom", lambda x: x["tasks"][1].update(projectId=None))
case("invalid_duplicate_field", lambda x: x["projects"][1]["fields"][1].update(id="f1"))
case("invalid_duplicate_field_label", lambda x: x["projects"][1]["fields"][1].update(label="COST"))
case("invalid_remote_scope", lambda x: x["projects"][1]["fields"][0].update(scope="github"))
case("invalid_date", lambda x: x["tasks"][1].update(dueDate="2026-02-29"))
case("invalid_timestamp", lambda x: x["tasks"][1].update(updatedAtMs=M-1))
case("invalid_orphan", lambda x: x["tasks"][0].update(projectId="p3"))
case("invalid_operation_wrong_project", lambda x: x["operations"][0].update(projectId="p1"))
case("invalid_operation_ack", lambda x: x["operations"][0].update(state="ACKNOWLEDGED"))
case("invalid_operation_same_value", lambda x: x["operations"][0].update(before="high"))
case("invalid_operation_counter", lambda x: x.update(nextOperationId=1))
case("invalid_operation_state", lambda x: x["operations"][0].update(state="SUCCESS"))
case("invalid_priority", lambda x: x["tasks"][1].update(priority="lowest"))
case("invalid_done_int", lambda x: x["tasks"][0].update(done=0))
case("invalid_custom_float", lambda x: x["tasks"][1]["values"].update(f1=1000000000001))
case("invalid_date_control", lambda x: x["tasks"][1].update(title="Bad\x01"))
case("invalid_missing_field", lambda x: x["tasks"][1].pop("createdAtMs"))
case("invalid_ordered_revision", lambda x: x["operations"][0].update(createdRevision=2))

batch = [x[1] for x in fixtures]
node = subprocess.run(["node", str(ORACLE)], cwd=ROOT,
                      input=json.dumps(batch, ensure_ascii=False), text=True,
                      capture_output=True, timeout=20, check=True)
accepted = json.loads(node.stdout)
assert len(accepted) == len(fixtures)
valid_labels = []
for (label, candidate), oracle_ok in zip(fixtures, accepted):
    try:
        store.validate(candidate)
        python_ok = True
    except store.StoreError:
        python_ok = False
    assert python_ok == oracle_ok, (label, python_ok, oracle_ok)
    if python_ok:
        valid_labels.append(label)
assert len(valid_labels) >= 5, valid_labels
assert len(fixtures) >= 35

qml = QML.read_text()
assert "Scope {" in qml and "Process {" in qml and "StdioCollector" in qml
assert "function requestStatus()" in qml
assert "function acceptResult()" in qml
assert 'remoteWriteAuthorized: false' in qml
assert 'writeReady: false' in qml
for forbidden in ("FileView {", "setText(", "onCompleted:", "Timer {",
                  "function save(", "function migrate(", "function commit(",
                  "onCandidatePathChanged:", "onStatusChanged:"):
    assert forbidden not in qml, forbidden
# Prove other widgets do not import the bridge or invoke the status helper.
for other in list((ROOT / "widgets").rglob("*.qml")) + list((ROOT / "services").rglob("*.qml")):
    if other == QML:
        continue
    content = other.read_text()
    assert "TaskSqliteReadBridge" not in content, other

with tempfile.TemporaryDirectory(prefix="tasks-m10k-parity-") as directory:
    root = Path(directory)
    database = root / "tasks.db"
    def invoke(file):
        completed = subprocess.run(
            [sys.executable, "-B", "-I", str(PROBE), "--db", str(file)],
            capture_output=True, text=True, timeout=12)
        payload = json.loads(completed.stdout)
        assert "document" not in payload and "title" not in payload
        assert payload["writeReady"] is False
        assert payload["remoteWriteAuthorized"] is False
        return completed.returncode, payload

    code, empty = invoke(database)
    assert code == 0 and empty["status"] == "ABSENT"
    assert not database.exists()
    assert not (root / "tasks.db-wal").exists()
    first = baseline()
    first["revision"] = 0
    first["operations"] = []
    first["nextOperationId"] = 1
    store.commit(database, first)
    code, active = invoke(database)
    assert code == 0 and active["status"] == "READY", active
    assert (active["revision"],active["tasks"],active["projects"],
            active["operations"],active["blockedOperations"]) == (0,2,2,0,0)
    current = store.read(database)
    second = baseline()
    store.commit(database, second,
                 expected_revision=current["revision"],
                 expected_hash=current["hash"])
    code, pending = invoke(database)
    assert code == 0 and pending["status"] == "READY", pending
    assert pending["operations"] == 1
    # Force a committed SENDING state on a synthetic DB; read-only bridge
    # must surface recovery review rather than dispatch/retry.
    snapshot = store.read(database)
    third = copy.deepcopy(snapshot["document"])
    third["revision"] += 1
    third["operations"][0]["state"] = "SENDING"
    store.commit(database, third,
                 expected_revision=snapshot["revision"],
                 expected_hash=snapshot["hash"])
    code, blocked = invoke(database)
    assert code == 0 and blocked["status"] == "RECOVERY_REVIEW", blocked
    assert blocked["blockedOperations"] == 1
    assert blocked["operations"] == 1
    code, bad = invoke(root)  # Explicit database filename required
    assert code == 2 and bad["status"] == "ERROR"
    code, missing = invoke(root / "not-here" / "tasks.db")
    assert code == 0 and missing["status"] == "ABSENT"
    assert not (root / "not-here").exists()
    # Break the index, then verify sanitization and fail-closed metadata.
    con=store.connect(database, initialize=True)
    with con:
        con.execute("DELETE FROM tasks WHERE task_id='t1'")
    con.close()
    code, rejected=invoke(database)
    assert code == 2 and rejected["status"] == "ERROR", rejected
    assert rejected["reason"] == "STORAGE_VALIDATION_FAILED"
    assert "hash" not in rejected and "tasks" not in rejected

print("TASKS M10k JS/Python parity and read-only Quickshell status probe: PASS")
