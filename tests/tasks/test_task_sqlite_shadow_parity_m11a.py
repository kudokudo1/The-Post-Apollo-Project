#!/usr/bin/env python3
"""M11a isolated JSON/SQLite v2 shadow parity: real read subprocess + Node.

No production files, runtime instance, GitHub network or writer switching.
A disposable synthetic SQLite DB is created once using the M10z fixture.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/"tests/tasks/fixtures/m10z_snapshot_fixture.py"
PROBE=ROOT/"services/projects/TaskSqliteSnapshotProbeM10y.py"
ORACLE=ROOT/"tests/tasks/fixtures/task_shadow_parity_m11a_oracle.cjs"
RECORDS=ROOT/"services/projects/ExperimentalTaskSqliteRecordsV2.py"
TIME=1700000000000

# An independently specified legacy document with exactly the expected data,
# NOT generated from the SQLite probe's response.
def frozen_legacy():
    return {"version":3,"nextId":3,"nextProjectId":2,
            "projects":[{"id":"p1","name":"TEST PROJECT",
                         "createdAtMs":TIME,"updatedAtMs":TIME}],
            "tasks":[
                {"id":"t1","projectId":"p1",
                 "title":"M10z disposable example task","done":False,
                 "priority":"low","description":"Synthetic sample only",
                 "dueDate":"2026-10-24","createdAtMs":TIME,"updatedAtMs":TIME},
                {"id":"t2","projectId":"p1",
                 "title":"M10z completed example","done":True,
                 "priority":"none","description":"","dueDate":None,
                 "createdAtMs":TIME,"updatedAtMs":TIME}]}


def call_node(doc, sql):
    proc=subprocess.run(["node",str(ORACLE)],cwd=ROOT,
                        input=json.dumps({"legacy":doc,"sqlite":sql}),
                        text=True,capture_output=True,check=True,timeout=15)
    assert proc.stderr==""
    return json.loads(proc.stdout)


with tempfile.TemporaryDirectory(prefix="pa-m11a-shadow-") as tmp:
    path=Path(tmp)/"m10y-snapshot-test"
    path.mkdir(mode=0o700)
    db=path/"tasks.db"
    subprocess.run([sys.executable,"-B","-I",str(FIXTURE),"--db",str(db)],
                   check=True,capture_output=True,timeout=15)
    def read():
        p=subprocess.run([sys.executable,"-B","-I",str(PROBE),"--db",str(db)],
                         check=True,text=True,capture_output=True,timeout=15)
        assert p.stderr==""
        return json.loads(p.stdout)
    original=read()
    assert original["status"]=="READY"
    assert original["revision"]==0
    assert original["writeReady"] is False

    spec=importlib.util.spec_from_file_location("m11a_records",RECORDS)
    records=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(records)
    baseline=records.read(db)

    reviewed=call_node(frozen_legacy(),original)
    assert reviewed=={
        "status":"MATCH_FOR_REVIEW_ONLY","matched":True,
        "blockers":[],"writeReady":False,"activate":False,
        "restore":False,"sqliteWriterAuthorized":False,
        "snapshotWritable":False,"total":2,"remaining":1,"completed":1}
    assert records.read(db)==baseline

    # Independently changed JSON with identical counts is NOT parity.
    changed=frozen_legacy()
    changed["tasks"][0]["dueDate"]="2026-10-25"
    drift=call_node(changed,original)
    assert drift["status"]=="DIVERGED"
    assert drift["snapshotWritable"] is None
    assert "tasks[0].dueDate" in drift["blockers"]
    assert "Synthetic sample only" not in json.dumps(drift)

    # A source whose JSON contains a new project/task must not be replaced
    # by old matching counts or a stale SHA asserted by the caller.
    changed=frozen_legacy()
    changed["projects"][0]["name"]="Updated Project"
    drift=call_node(changed,original)
    assert "projects[0].name" in drift["blockers"]

    broken=dict(original,status="RECOVERY_REVIEW",blockedOperations=1)
    assert call_node(frozen_legacy(),broken)["status"]=="BLOCKED"
    broken=dict(original,status="ABSENT",available=False,document=None)
    assert call_node(frozen_legacy(),broken)["status"]=="BLOCKED"
    assert records.read(db)==baseline
    assert read()==original

    # A source SQLite edit *after* a matching snapshot causes a new
    # mismatch, even if the legacy view still has the same number of tasks.
    records.edit_task(db,expected_revision=baseline["revision"],
                      expected_hash=baseline["hash"],task_id="t1",
                      field="priority",value="urgent",now_ms=TIME+10)
    updated=read()
    assert updated["revision"]==1
    assert updated["document"]["tasks"][0]["priority"]=="urgent"
    drift=call_node(frozen_legacy(),updated)
    assert drift["status"]=="DIVERGED"
    assert "tasks[0].priority" in drift["blockers"]
    assert drift["activate"] is False
    assert drift["writeReady"] is False
    assert records.read(db)["revision"]==1

print("M11a disposable JSON/SQLite shadow compare, drift and read-only integration: PASS")
