#!/usr/bin/env python3
"""M10y read-only SQLite-v2 snapshot parity, process and QML boundary tests."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
PROBE=ROOT/"services/projects/TaskSqliteSnapshotProbeM10y.py"
QML=ROOT/"services/projects/TaskSqliteSnapshotBridgeM10y.qml"
ORACLE=ROOT/"tests/tasks/fixtures/task_sqlite_snapshot_m10y_oracle.cjs"
RECORDS=ROOT/"services/projects/ExperimentalTaskSqliteRecordsV2.py"
spec=importlib.util.spec_from_file_location("m10y_fixture_v2",RECORDS)
records=importlib.util.module_from_spec(spec)
spec.loader.exec_module(records)
TIME=1700000000000


def model(empty=False):
    result={"version":2,"revision":0,"nextId":4,"nextProjectId":3,
            "nextOperationId":1,
            "projects":[
                {"id":"p1","name":"Personal","family":"normal","remote":None,
                 "fields":[],"createdAtMs":TIME,"updatedAtMs":TIME},
                {"id":"p2","name":"Git Work","family":"git",
                 "remote":{"provider":"github","owner":"kudokudo1",
                           "projectNodeId":"PVT_unverified",
                           "projectNumber":42},
                 "fields":[{"id":"f1","label":"Private note","kind":"text",
                            "scope":"local"}],
                 "createdAtMs":TIME,"updatedAtMs":TIME}],
            "tasks":[
                {"id":"t1","projectId":"p1","title":"Write project plan",
                 "done":False,"priority":"high","description":"Local detail",
                 "dueDate":"2026-10-24","remote":None,"values":{},
                 "createdAtMs":TIME,"updatedAtMs":TIME},
                {"id":"t2","projectId":"p2","title":"Finished work",
                 "done":True,"priority":"low","description":"Hidden remote note",
                 "dueDate":None,
                 "remote":{"projectItemNodeId":"PVTI_unverified",
                           "contentKind":"DRAFT_ISSUE","contentNodeId":None},
                 "values":{"f1":"Secret custom value"},
                 "createdAtMs":TIME,"updatedAtMs":TIME},
                {"id":"t3","projectId":"p2","title":"Pending offline",
                 "done":False,"priority":"medium","description":"Important",
                 "dueDate":"2026-10-25",
                 "remote":None,"values":{"f1":"Do not flatten"},
                 "createdAtMs":TIME,"updatedAtMs":TIME}],
            "operations":[]}
    if empty:
        result["projects"]=[]
        result["tasks"]=[]
        result["nextId"]=1
        result["nextProjectId"]=1
    return result


def invoke(path):
    proc=subprocess.run([sys.executable,"-B","-I",str(PROBE),
                        "--db",str(path)],cwd=ROOT,text=True,
                        capture_output=True,timeout=15)
    assert proc.stderr=="",proc.stderr
    payload=json.loads(proc.stdout)
    assert payload["writeReady"] is False
    assert payload["remoteWriteAuthorized"] is False
    assert payload["protocol"]==1
    return proc.returncode,payload,proc.stdout


def oracle(payload):
    proc=subprocess.run(["node",str(ORACLE)],cwd=ROOT,
                        input=json.dumps(payload),capture_output=True,
                        text=True,timeout=15,check=True)
    return json.loads(proc.stdout)


qml=QML.read_text()
assert 'import "../hub/ApolloHubTodoPolicy.js" as TodoPolicy' in qml
assert "Scope {" in qml and "Process {" in qml
assert "function requestSnapshot()" in qml
assert "function acceptResult()" in qml
assert 'readonly property bool writeReady: false' in qml
assert 'readonly property bool remoteWriteAuthorized: false' in qml
assert 'readonly property bool activate: false' in qml
assert "TodoPolicy.validate(doc).ok" in qml
assert "safeView.writable = false;" in qml
assert '"m10y-snapshot-test' not in qml  # Only path segment; no fixed user path.
assert 'm10y-snapshot-test' in qml
assert "onExited: function(code, exitStatus)" in qml
for forbidden in ("FileView {","stdinEnabled: true","setText(",
                  "onCompleted:","Timer {","onCandidatePathChanged:",
                  "function save(","function commit(","function migrate(",
                  "Quickshell.execDetached(","GitHubProjectsService {"):
    assert forbidden not in qml,forbidden
# The new bridge is completely absent from mounted live shell and consumer QML.
for folder in ("widgets","services"):
    for path in (ROOT/folder).rglob("*.qml"):
        if path==QML:
            continue
        assert "TaskSqliteSnapshotBridgeM10y" not in path.read_text(),path
assert "TaskSqliteSnapshotBridgeM10y" not in (ROOT/"shell.qml").read_text()
probe=PROBE.read_text()
for forbidden in ("CREATE TABLE","UPDATE ","INSERT INTO","DELETE FROM",
                  "os.system(","subprocess.run(","requests.post(",
                  "GitHubProjectsService","ApolloHubTodoStore"):
    assert forbidden not in probe,forbidden

with tempfile.TemporaryDirectory(prefix="pa-m10y-read-only-") as td:
    base=Path(td)
    fixture_dir=base/"m10y-snapshot-test"
    fixture_dir.mkdir(mode=0o700)
    db=fixture_dir/"tasks.db"

    code,absent,raw=invoke(db)
    assert code==0 and absent["status"]=="ABSENT"
    assert absent["document"] is None and absent["available"] is False
    assert absent["sourceHash"] is None and absent["revision"] is None
    assert not db.exists()
    assert "Write project plan" not in raw

    # Disallow arbitrary production-like paths (even if a tasks.db exists).
    wrong_dir=base/"normal-task-store"
    wrong_dir.mkdir(mode=0o700)
    code,rejected,_=invoke(wrong_dir/"tasks.db")
    assert code==2 and rejected["status"]=="ERROR"
    assert rejected["document"] is None
    assert not (wrong_dir/"tasks.db").exists()

    first=model()
    records.initialize(db,first)
    before=records.read(db)
    code,ready,raw=invoke(db)
    assert code==0 and ready["status"]=="READY"
    assert ready["revision"]==before["revision"]
    assert ready["sourceHash"]==before["hash"]
    assert ready["blockedOperations"]==0
    assert ready["available"] is True
    doc=ready["document"]
    assert doc["version"]==3
    assert doc["nextId"]==4 and doc["nextProjectId"]==3
    assert doc["projects"][1]["name"]=="Git Work"
    assert doc["tasks"][0]["title"]=="Write project plan"
    assert doc["tasks"][0]["description"]=="Local detail"
    assert doc["tasks"][2]["projectId"]=="p2"
    assert '"remote":' not in raw and '"values":' not in raw
    assert "Secret custom value" not in raw
    assert "PVT_unverified" not in raw and "PVTI_unverified" not in raw
    assert '"operations":' not in raw
    assert records.read(db)==before # Probe only read, never staged a write.

    parity=oracle(ready)
    assert parity["writable"] is False
    assert parity["state"]=="ready" and parity["total"]==3
    assert parity["remaining"]==2 and parity["completed"]==1
    assert parity["ids"]==["t1","t3","t2"]
    assert parity["projectIds"]==["p1","p2"]
    assert parity["todayCount"]==1 and parity["agendaCount"]==1

    # Real v2 local GIT edit stores a PENDING intent. Read view still works;
    # neither identity metadata nor operation bodies are exported.
    pending=records.edit_task(db,expected_revision=before["revision"],
                              expected_hash=before["hash"],task_id="t3",
                              field="priority",value="urgent",
                              now_ms=TIME+10)
    assert pending["remoteIntentCreated"] is True
    state=records.read(db)
    code,updated,raw=invoke(db)
    assert code==0 and updated["status"]=="READY"
    assert updated["blockedOperations"]==0
    assert updated["revision"]==state["revision"]
    assert updated["document"]["tasks"][2]["priority"]=="urgent"
    assert "op1" not in raw and "PENDING" not in raw
    oracle(updated)
    assert records.read(db)==state

    records.transition_local_operation(
        db,expected_revision=state["revision"],expected_hash=state["hash"],
        operation_id="op1",next_state="SENDING")
    blocked_before=records.read(db)
    code,blocked,raw=invoke(db)
    assert code==0 and blocked["status"]=="RECOVERY_REVIEW"
    assert blocked["blockedOperations"]==1
    assert blocked["document"]["tasks"][2]["priority"]=="urgent"
    assert blocked["writeReady"] is False
    assert "SENDING" not in raw
    oracle(blocked)
    assert records.read(db)==blocked_before  # Never converts SENDING itself.

    # Wrong schema must fail closed, never become a misleading EMPTY view.
    bogus_dir=base/"older"/"m10y-snapshot-test"
    bogus_dir.mkdir(mode=0o700,parents=True)
    bogus_db=bogus_dir/"tasks.db"
    with sqlite3.connect(bogus_db) as con:
        con.execute("PRAGMA user_version=1")
    bogus_db.chmod(0o600)
    code,bad,_=invoke(bogus_db)
    assert code==2 and bad["status"]=="ERROR"
    assert bad["document"] is None

    # Empty but present DB differs from absent and can still be viewed
    # through the deployed TODAY/PLANNER model without implying writability.
    empty_dir=base/"empty"/"m10y-snapshot-test"
    empty_dir.mkdir(mode=0o700,parents=True)
    empty_db=empty_dir/"tasks.db"
    records.initialize(empty_db,model(empty=True))
    code,empty_payload,_=invoke(empty_db)
    assert code==0 and empty_payload["status"]=="EMPTY"
    assert empty_payload["available"] is True
    assert oracle(empty_payload)["total"]==0

print("TASKS M10y v2 SQLite process snapshot, deployed view parity, recovery and QML isolation: PASS")
