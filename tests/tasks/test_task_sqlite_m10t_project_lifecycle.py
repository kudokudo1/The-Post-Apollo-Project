#!/usr/bin/env python3
"""M10t disposable NORMAL project rename/detach/delete regressions."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "m10t_lifecycle", ROOT / "services/projects/ExperimentalTaskSqliteProjectsM10t.py")
life = importlib.util.module_from_spec(spec)
spec.loader.exec_module(life)
crud = life.crud
records = life.records
TIME = 1700000000000


def project(pid, name, *, family="normal", fields=None):
    return {"id":pid, "name":name, "createdAtMs":TIME,
            "updatedAtMs":TIME, "family":family,
            "remote":None if family=="normal" else {
                "provider":"github","owner":"kudokudo1",
                "projectNodeId":"PVT_not_verified","projectNumber":42},
            "fields":[] if fields is None else fields}


def task(tid, project_id, name, *, values=None):
    return {"id":tid,"title":name,"done":False,"priority":"medium",
            "description":"Keep "+name,"dueDate":"2026-10-24",
            "createdAtMs":TIME,"updatedAtMs":TIME,"projectId":project_id,
            "remote":None,"values":{} if values is None else values}


def initial():
    return {"version":2,"revision":0,"nextId":5,"nextProjectId":4,
            "nextOperationId":1,
            "projects":[project("p1","Personal"),project("p2","School"),
                        project("p3","Git",family="git")],
            "tasks":[task("t1","p1","One"),task("t2","p1","Two"),
                     task("t3","p2","Three"),task("t4","p3","Remote")],
            "operations":[]}


def denied(fn, code):
    try:
        fn()
    except (life.StoreError, sqlite3.Error) as exc:
        assert code in str(exc), (code,str(exc))
        return
    raise AssertionError("Expected refusal: "+code)


with tempfile.TemporaryDirectory(prefix="pa-m10t-projects-") as td:
    base=Path(td)
    db=base/"tasks.db"
    records.initialize(db,initial())

    def state():
        return records.read(db)

    def op(fn, **kwargs):
        x=state()
        return fn(db,expected_revision=x["revision"],expected_hash=x["hash"],
                  **kwargs)

    # Rename is NORMAL-only and changes only name + project timestamp.
    original=copy.deepcopy(state()["document"])
    renamed=op(life.rename_normal_project,project_id="p1",
               name="Personal Plans",now_ms=TIME+10)
    assert renamed["status"]=="LOCAL_COMMITTED"
    assert renamed["remoteWriteAuthorized"] is False
    assert renamed["remoteIntentCreated"] is False
    after=state()["document"]
    assert after["revision"]==1
    assert after["projects"][0]["name"]=="Personal Plans"
    assert after["projects"][0]["updatedAtMs"]==TIME+10
    assert after["projects"][0]["createdAtMs"]==TIME
    assert after["projects"][1:]==original["projects"][1:]
    assert after["tasks"]==original["tasks"]
    assert after["nextProjectId"]==4 and after["operations"]==[]

    before=state()
    denied(lambda:op(life.rename_normal_project,project_id="p1",
                  name="SCHOOL",now_ms=TIME+20),"PROJECT_NAME_CONFLICT")
    denied(lambda:op(life.rename_normal_project,project_id="p3",
                  name="Git New",now_ms=TIME+20),"GIT_PROJECT_UNSUPPORTED")
    denied(lambda:op(life.rename_normal_project,project_id="p1",
                  name=" Bad ",now_ms=TIME+20),"INVALID_PROJECT_RENAME")
    denied(lambda:op(life.rename_normal_project,project_id="p1",
                  name="Personal Plans",now_ms=TIME+20),"NO_CHANGE")
    denied(lambda:op(life.rename_normal_project,project_id="p9",
                  name="Missing",now_ms=TIME+20),"UNKNOWN_PROJECT")
    denied(lambda:op(life.rename_normal_project,project_id="p1",
                  name="Old Time",now_ms=TIME),"STALE_EDIT_TIME")
    assert state()==before

    # Explicit confirmation and fail-closed GIT project isolation.
    denied(lambda:op(life.delete_normal_project,project_id="p1",
                  confirmed=1,now_ms=TIME+30),"DELETE_NOT_CONFIRMED")
    denied(lambda:op(life.delete_normal_project,project_id="p3",
                  confirmed=True,now_ms=TIME+30),"GIT_PROJECT_UNSUPPORTED")
    assert state()==before

    # Before commit, task detach and SQL project deletion roll back together.
    try:
        op(life.delete_normal_project,project_id="p1",
           confirmed=True,now_ms=TIME+30,stop_at="before_commit")
    except life.InterruptedCommit as exc:
        assert "before_commit" in str(exc)
    else:
        raise AssertionError("Expected interrupted deletion")
    assert state()==before

    # Successful delete detaches both tasks while retaining every other field.
    delete=op(life.delete_normal_project,project_id="p1",
              confirmed=True,now_ms=TIME+30)
    assert delete["id"]=="p1" and delete["localSaved"] is True
    assert delete["remoteSent"] is False and delete["remoteIntentCreated"] is False
    after=state()["document"]
    assert [p["id"] for p in after["projects"]]==["p2","p3"]
    assert after["nextProjectId"]==4
    assert [t["id"] for t in after["tasks"]]==["t1","t2","t3","t4"]
    assert after["tasks"][2:]==original["tasks"][2:]
    for i in (0,1):
        preserved=copy.deepcopy(original["tasks"][i])
        preserved["projectId"]=None
        preserved["updatedAtMs"]=TIME+30
        assert after["tasks"][i]==preserved
    assert after["operations"]==[]
    with sqlite3.connect(db) as con:
        assert con.execute("PRAGMA foreign_key_check").fetchall()==[]
        assert con.execute("PRAGMA integrity_check").fetchone()[0]=="ok"

    # M10s project creation must not reuse old IDs or collide with SQL positions.
    added=op(crud.create_normal_project,name="New Project",now_ms=TIME+40)
    assert added["id"]=="p4"
    assert [p["id"] for p in state()["document"]["projects"]]==["p2","p3","p4"]
    assert state()["document"]["nextProjectId"]==5

    # Reopen after an uncertain after-COMMIT outcome; never blindly retry.
    before=state()
    try:
        op(life.delete_normal_project,project_id="p2",
           confirmed=True,now_ms=TIME+50,stop_at="after_commit")
    except life.InterruptedCommit as exc:
        assert "after_commit" in str(exc)
    else:
        raise AssertionError("Expected post-commit uncertainty")
    recovered=state()
    assert recovered["revision"]==before["revision"]+1
    assert [p["id"] for p in recovered["document"]["projects"]]==["p3","p4"]
    assert recovered["document"]["tasks"][2]["projectId"] is None
    denied(lambda:life.rename_normal_project(
        db,expected_revision=before["revision"],expected_hash=before["hash"],
        project_id="p2",name="Blind replay",now_ms=TIME+60),
        "STALE_BASELINE")
    assert state()==recovered

    # Strict handling of NORMAL custom project fields: refuse deletion rather
    # than silently dropping field definitions or task custom values.
    custom_root=base/"custom"
    custom_root.mkdir(mode=0o700)
    custom_db=custom_root/"tasks.db"
    custom=initial()
    custom["projects"][0]["fields"]=[
        {"id":"f1","label":"Category","kind":"text","scope":"local"}]
    custom["tasks"][0]["values"]={"f1":"retain"}
    records.initialize(custom_db,custom)
    original_custom=records.read(custom_db)
    denied(lambda:life.delete_normal_project(
        custom_db,expected_revision=original_custom["revision"],
        expected_hash=original_custom["hash"],project_id="p1",
        confirmed=True,now_ms=TIME+10),"PROJECT_CUSTOM_FIELDS_REQUIRE_REVIEW")
    assert records.read(custom_db)==original_custom

    # No fixture path is created implicitly by a mutation request.
    missing_root=base/"missing"
    missing_root.mkdir(mode=0o700)
    missing=missing_root/"tasks.db"
    denied(lambda:life.delete_normal_project(
        missing,expected_revision=0,expected_hash="0"*64,
        project_id="p1",confirmed=True,now_ms=TIME+10),"DATABASE_ABSENT")
    assert not missing.exists()

    print("M10t NORMAL project lifecycle: rename, detach, rollback, recovery PASS")
