#!/usr/bin/env python3
"""M10u SQLite local-only custom schema/value operations, synthetic data only."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[2]
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

custom = load(ROOT / "services/projects/ExperimentalTaskSqliteCustomM10u.py",
              "m10u_local_custom")
records = custom.records
TIME = 1700000000000


def fixture():
    return {"version":2,"revision":0,"nextId":4,"nextProjectId":3,
            "nextOperationId":1,
            "projects":[
                {"id":"p1","name":"NORMAL","family":"normal","remote":None,
                 "createdAtMs":TIME,"updatedAtMs":TIME,"fields":[]},
                {"id":"p2","name":"GIT","family":"git",
                 "remote":{"provider":"github","owner":"kudokudo1",
                           "projectNodeId":"PVT_unverified","projectNumber":14},
                 "createdAtMs":TIME,"updatedAtMs":TIME,
                 "fields":[{"id":"f1","label":"Existing","kind":"text","scope":"local"}]}],
            "tasks":[
                {"id":"t1","title":"Local task","done":False,"projectId":"p1",
                 "priority":"none","description":"Keep","dueDate":None,
                 "createdAtMs":TIME,"updatedAtMs":TIME,"remote":None,"values":{}},
                {"id":"t2","title":"GIT task","done":False,"projectId":"p2",
                 "priority":"high","description":"Keep remote values",
                 "dueDate":"2026-10-24","createdAtMs":TIME,"updatedAtMs":TIME,
                 "remote":{"projectItemNodeId":"PVTI_unverified",
                           "contentKind":"DRAFT_ISSUE","contentNodeId":None},
                 "values":{"f1":"Original local"}},
                {"id":"t3","title":"Unassigned","done":False,"projectId":None,
                 "priority":"none","description":"","dueDate":None,
                 "createdAtMs":TIME,"updatedAtMs":TIME,"remote":None,"values":{}}],
            "operations":[]}


def denied(fn,code):
    try:
        fn()
    except (custom.StoreError,sqlite3.Error) as exc:
        assert code in str(exc),(code,str(exc))
        return
    raise AssertionError("Expected refusal: "+code)


with tempfile.TemporaryDirectory(prefix="pa-m10u-custom-") as td:
    base=Path(td)
    path=base/"tasks.db"
    records.initialize(path,fixture())

    def state():
        return records.read(path)

    def do(fn,**kwargs):
        x=state()
        return fn(path,expected_revision=x["revision"],
                  expected_hash=x["hash"],**kwargs)

    original=copy.deepcopy(state()["document"])
    added=do(custom.add_local_field,project_id="p2",label="Estimate",
             kind="number",now_ms=TIME+10)
    assert added["status"]=="LOCAL_COMMITTED" and added["id"]=="f2"
    assert added["remoteSent"] is False
    assert added["remoteWriteAuthorized"] is False
    assert added["remoteIntentCreated"] is False
    model=state()["document"]
    assert model["revision"]==1
    assert model["projects"][1]["fields"][-1]=={
        "id":"f2","label":"Estimate","kind":"number","scope":"local"}
    assert model["projects"][0]==original["projects"][0]
    assert model["tasks"]==original["tasks"]
    assert model["operations"]==[]
    assert model["nextOperationId"]==1

    # GIT linked task is eligible for explicitly local-only custom metadata,
    # but *not* remote operation dispatch, even with a remote shape present.
    result=do(custom.edit_local_value,task_id="t2",field_id="f2",
              value=24.5,now_ms=TIME+20)
    assert result["remoteIntentCreated"] is False
    after=state()["document"]
    assert after["tasks"][1]["values"]=={"f1":"Original local","f2":24.5}
    assert after["tasks"][1]["remote"]==original["tasks"][1]["remote"]
    assert after["tasks"][1]["title"]=="GIT task"
    assert after["tasks"][1]["priority"]=="high"
    assert after["tasks"][1]["dueDate"]=="2026-10-24"
    assert after["operations"]==[] and after["nextOperationId"]==1

    # Existing field values remain stable; null is allowed as an explicit
    # local value and differs from an absent key.
    do(custom.edit_local_value,task_id="t2",field_id="f1",
       value=None,now_ms=TIME+21)
    assert state()["document"]["tasks"][1]["values"]=={"f1":None,"f2":24.5}
    baseline=state()
    denied(lambda:do(custom.edit_local_value,task_id="t2",
                field_id="f2",value=True,now_ms=TIME+22),
                "INVALID_CUSTOM_VALUE")
    denied(lambda:do(custom.edit_local_value,task_id="t2",
                field_id="f2",value=24.5,now_ms=TIME+22),
                "NO_CHANGE")
    denied(lambda:do(custom.edit_local_value,task_id="t3",
                field_id="f1",value="bad",now_ms=TIME+22),
                "NO_PROJECT_FOR_CUSTOM_VALUE")
    denied(lambda:do(custom.edit_local_value,task_id="t2",
                field_id="f9",value="bad",now_ms=TIME+22),
                "UNKNOWN_CUSTOM_FIELD")
    denied(lambda:do(custom.add_local_field,project_id="p2",
                label="estimate",kind="boolean",now_ms=TIME+22),
                "DUPLICATE_FIELD_LABEL")
    denied(lambda:do(custom.add_local_field,project_id="p2",
                label="Unknown",kind="path",now_ms=TIME+22),
                "INVALID_FIELD_REQUEST")
    assert state()==baseline

    # Multiple field kinds on a NORMAL project. No remote work is generated.
    text=do(custom.add_local_field,project_id="p1",label="Context",
            kind="text",now_ms=TIME+30)
    assert text["id"]=="f1"  # Field IDs are unique within a project.
    boolean=do(custom.add_local_field,project_id="p1",label="Approved",
               kind="boolean",now_ms=TIME+31)
    assert boolean["id"]=="f2"
    date=do(custom.add_local_field,project_id="p1",label="Reminder",
            kind="date",now_ms=TIME+32)
    assert date["id"]=="f3"
    do(custom.edit_local_value,task_id="t1",field_id="f1",
       value="Meeting notes",now_ms=TIME+40)
    do(custom.edit_local_value,task_id="t1",field_id="f2",
       value=False,now_ms=TIME+41)
    do(custom.edit_local_value,task_id="t1",field_id="f3",
       value="2024-02-29",now_ms=TIME+42)
    assert state()["document"]["tasks"][0]["values"]=={
        "f1":"Meeting notes","f2":False,"f3":"2024-02-29"}
    snapshot=state()
    denied(lambda:do(custom.edit_local_value,task_id="t1",
                field_id="f3",value="0001-02-29",now_ms=TIME+43),
                "INVALID_CUSTOM_VALUE")
    denied(lambda:do(custom.edit_local_value,task_id="t1",
                field_id="f2",value=0,now_ms=TIME+43),
                "INVALID_CUSTOM_VALUE")
    assert state()==snapshot

    # Wrong revision, older time, unknown project and invalid ID refuse writes.
    old=state()
    do(custom.edit_local_value,task_id="t1",field_id="f1",
       value="Fresh",now_ms=TIME+45)
    denied(lambda:custom.add_local_field(path,expected_revision=old["revision"],
                expected_hash=old["hash"],project_id="p1",label="Stale",
                kind="text",now_ms=TIME+46),"STALE_BASELINE")
    denied(lambda:do(custom.add_local_field,project_id="p1",
                label="Clock",kind="text",now_ms=TIME),
                "STALE_EDIT_TIME")
    denied(lambda:do(custom.add_local_field,project_id="p99",
                label="Missing",kind="text",now_ms=TIME+50),
                "UNKNOWN_PROJECT")

    # One atomic SQL record+meta transaction; synthetic failure does not
    # permit a partial custom field definition or value to escape.
    before=state()
    try:
        do(custom.add_local_field,project_id="p1",label="Rollback",
           kind="text",now_ms=TIME+50,stop_at="before_commit")
    except custom.InterruptedCommit as exc:
        assert "before_commit" in str(exc)
    else:
        raise AssertionError("Expected precommit exception")
    assert state()==before

    # A failed postcommit caller must read again rather than silently replay.
    try:
        do(custom.edit_local_value,task_id="t1",field_id="f2",
           value=True,now_ms=TIME+55,stop_at="after_commit")
    except custom.InterruptedCommit as exc:
        assert "after_commit" in str(exc)
    else:
        raise AssertionError("Expected uncertain postcommit result")
    recovered=state()
    assert recovered["revision"]==before["revision"]+1
    assert recovered["document"]["tasks"][0]["values"]["f2"] is True
    assert recovered["document"]["operations"]==[]
    denied(lambda:custom.edit_local_value(
        path,expected_revision=before["revision"],expected_hash=before["hash"],
        task_id="t1",field_id="f2",value=True,now_ms=TIME+56),
        "STALE_BASELINE")

    # Existing pending GitHub intent stays byte-for-byte and order stable;
    # a LOCAL custom change is a separate revision, never an extra queue item.
    queued=do(records.edit_task,task_id="t2",field="title",
              value="GIT task edited",now_ms=TIME+60)
    assert queued["remoteIntentCreated"] is True
    prior=copy.deepcopy(state()["document"]["operations"])
    assert len(prior)==1 and prior[0]["state"]=="PENDING"
    local=do(custom.edit_local_value,task_id="t2",field_id="f2",
             value=25,now_ms=TIME+61)
    assert local["remoteIntentCreated"] is False
    assert state()["document"]["operations"]==prior

    # A SENDING/UNCERTAIN/CONFLICT journal state blocks new local edits
    # until operator-authorized recovery.
    pending=state()
    records.transition_local_operation(
        path,expected_revision=pending["revision"],
        expected_hash=pending["hash"],operation_id=prior[0]["id"],
        next_state="SENDING")
    assert state()["status"]=="RECOVERY_REVIEW"
    frozen=state()
    denied(lambda:do(custom.edit_local_value,task_id="t2",
                field_id="f2",value=50,now_ms=TIME+70),
                "RECOVERY_REVIEW_REQUIRED")
    denied(lambda:do(custom.add_local_field,project_id="p2",
                label="Should Refuse",kind="text",now_ms=TIME+70),
                "RECOVERY_REVIEW_REQUIRED")
    assert state()==frozen

    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        assert con.execute("PRAGMA foreign_key_check").fetchall()==[]
    print("M10u isolated local fields, GIT no-sync, rollback, recovery: PASS")
