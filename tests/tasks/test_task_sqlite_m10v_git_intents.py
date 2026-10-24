#!/usr/bin/env python3
"""M10v test-only GIT standard-field edits and ordered SQLite intent journal."""
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

git = load(ROOT/"services/projects/ExperimentalTaskSqliteGitM10v.py","m10v_git")
records = git.records
TIME=1700000000000


def fixture():
    return {"version":2,"revision":0,"nextId":4,"nextProjectId":3,
            "nextOperationId":1,
            "projects":[
                {"id":"p1","name":"NORMAL","family":"normal","remote":None,
                 "fields":[],"createdAtMs":TIME,"updatedAtMs":TIME},
                {"id":"p2","name":"GIT","family":"git",
                 "remote":{"provider":"github","owner":"kudokudo1",
                           "projectNodeId":"PVT_unverified",
                           "projectNumber":14},
                 "fields":[{"id":"f1","label":"Local note","kind":"text",
                            "scope":"local"}],
                 "createdAtMs":TIME,"updatedAtMs":TIME}],
            "tasks":[
                {"id":"t1","projectId":"p1","title":"Normal",
                 "done":False,"priority":"none","description":"Normal data",
                 "dueDate":None,"remote":None,"values":{},
                 "createdAtMs":TIME,"updatedAtMs":TIME},
                {"id":"t2","projectId":"p2","title":"GIT title",
                 "done":False,"priority":"medium",
                 "description":"GIT details","dueDate":"2026-10-24",
                 "remote":{"projectItemNodeId":"PVTI_unverified",
                           "contentKind":"DRAFT_ISSUE","contentNodeId":None},
                 "values":{"f1":"Private custom"},
                 "createdAtMs":TIME,"updatedAtMs":TIME},
                {"id":"t3","projectId":None,"title":"Unassigned",
                 "done":False,"priority":"none","description":"",
                 "dueDate":None,"remote":None,"values":{},
                 "createdAtMs":TIME,"updatedAtMs":TIME}],
            "operations":[]}


def denied(fn,code):
    try:
        fn()
    except (git.StoreError,sqlite3.Error) as exc:
        assert code in str(exc),(code,str(exc))
        return
    raise AssertionError("Expected "+code)


with tempfile.TemporaryDirectory(prefix="pa-m10v-git-intents-") as td:
    base=Path(td)
    serial=[0]
    def fresh():
        serial[0]+=1
        directory=base/str(serial[0])
        directory.mkdir(mode=0o700)
        file=directory/"tasks.db"
        records.initialize(file,fixture())
        return file
    file=fresh()
    def state(db=file):
        return records.read(db)
    def edit(changes, db=file, **kwargs):
        current=state(db)
        return git.edit_git_task_fields(
            db,expected_revision=current["revision"],
            expected_hash=current["hash"],task_id="t2",changes=changes,
            now_ms=kwargs.pop("now_ms",TIME+10),**kwargs)

    initial=state()
    original=copy.deepcopy(initial["document"])
    # User-supplied key order is deliberately not journal order. The v2 model
    # requires one createdRevision per field even with one SQL commit.
    result=edit({"dueDate":"2026-11-01","priority":"urgent",
                 "description":"Changed"})
    assert result["status"]=="LOCAL_COMMITTED"
    assert result["remoteIntentCreated"] is True
    assert result["remoteSent"] is False
    assert result["remoteWriteAuthorized"] is False
    assert result["operationIds"]==["op1","op2","op3"]
    now=state()["document"]
    assert now["revision"]==3 and now["nextOperationId"]==4
    assert now["tasks"][1]["description"]=="Changed"
    assert now["tasks"][1]["priority"]=="urgent"
    assert now["tasks"][1]["dueDate"]=="2026-11-01"
    assert now["tasks"][1]["remote"]==original["tasks"][1]["remote"]
    assert now["tasks"][1]["values"]=={"f1":"Private custom"}
    assert now["tasks"][0]==original["tasks"][0]
    assert now["tasks"][2]==original["tasks"][2]
    assert now["projects"]==original["projects"]
    assert [(x["id"],x["field"],x["createdRevision"],x["state"])
            for x in now["operations"]]==[
                ("op1","priority",1,"PENDING"),
                ("op2","description",2,"PENDING"),
                ("op3","dueDate",3,"PENDING")]
    assert [(x["before"],x["after"]) for x in now["operations"]]==[
        ("medium","urgent"),("GIT details","Changed"),
        ("2026-10-24","2026-11-01")]

    # Old baselines rejected. No-op values do not create duplicate entries.
    denied(lambda:git.edit_git_task_fields(
        file,expected_revision=initial["revision"],
        expected_hash=initial["hash"],task_id="t2",
        changes={"title":"Stale"},now_ms=TIME+20),"STALE_BASELINE")
    assert state()["document"]==now
    denied(lambda:edit({"description":"Changed"}),"NO_CHANGE")
    denied(lambda:edit({"priority":"super"}),"INVALID_GIT_EDIT")
    denied(lambda:edit({"dueDate":"2026-02-30"}),"INVALID_GIT_EDIT")
    denied(lambda:edit({"done":1}),"INVALID_GIT_EDIT")
    denied(lambda:edit({"projectId":"p1"}),"INVALID_GIT_EDIT")
    denied(lambda:edit({}),"INVALID_GIT_EDIT")
    denied(lambda:edit({"title":"Early"},now_ms=TIME-1),"STALE_EDIT_TIME")
    denied(lambda:git.edit_git_task_fields(
        file,expected_revision=state()["revision"],
        expected_hash=state()["hash"],task_id="t1",
        changes={"title":"Should refuse"},now_ms=TIME+20),
        "GIT_PROJECT_REQUIRED")
    denied(lambda:git.edit_git_task_fields(
        file,expected_revision=state()["revision"],
        expected_hash=state()["hash"],task_id="t3",
        changes={"title":"Should refuse"},now_ms=TIME+20),
        "GIT_PROJECT_REQUIRED")
    assert state()["document"]==now

    # Existing pending op stays in order; subsequent single field change
    # allocates a new revision, ID, and uses current local value as before.
    result2=edit({"done":True,"priority":"high",
                  "description":"Changed"},now_ms=TIME+20)
    assert result2["operationIds"]==["op4","op5"]
    mid=state()["document"]
    assert mid["revision"]==5 and mid["nextOperationId"]==6
    assert mid["operations"][:3]==now["operations"]
    assert [(x["field"],x["before"],x["after"],x["createdRevision"])
            for x in mid["operations"][3:]]==[
                ("done",False,True,4),("priority","urgent","high",5)]
    assert mid["operations"][4]["ackToken"] is None
    assert state()["blockedOperations"]==[]

    # A remote-operation dispatch is NOT implied by recording PENDING.
    sending=state()
    records.transition_local_operation(
        file,expected_revision=sending["revision"],
        expected_hash=sending["hash"],operation_id="op1",
        next_state="SENDING")
    frozen=state()
    assert frozen["status"]=="RECOVERY_REVIEW"
    denied(lambda:edit({"title":"Cannot bypass recovery"},now_ms=TIME+30),
           "RECOVERY_REVIEW_REQUIRED")
    assert state()==frozen

    # Interrupt at EVERY meaningful SQL boundary. Before commit: no task or
    # operation escapes. After commit: complete batch exists, read first.
    for phase in ("before_task_update","after_task_update",
                  "after_first_operation_insert","after_operation_insert",
                  "before_commit","after_commit"):
        db=fresh()
        before=state(db)
        try:
            edit({"priority":"urgent","description":"Offline",
                  "dueDate":"2026-10-25"},db=db,stop_at=phase)
        except git.InterruptedCommit as exc:
            assert phase in str(exc),(phase,str(exc))
        else:
            raise AssertionError("Expected injected fault "+phase)
        after=state(db)
        if phase!="after_commit":
            assert after==before,phase
        else:
            assert after["revision"]==3 and after["document"]["nextOperationId"]==4
            assert [op["id"] for op in after["document"]["operations"]]==[
                "op1","op2","op3"]
            assert after["document"]["tasks"][1]["dueDate"]=="2026-10-25"
            denied(lambda:git.edit_git_task_fields(
                db,expected_revision=before["revision"],
                expected_hash=before["hash"],task_id="t2",
                changes={"priority":"urgent"},now_ms=TIME+20),
                "STALE_BASELINE")
        with sqlite3.connect(db) as sql:
            assert sql.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
            assert sql.execute("PRAGMA foreign_key_check").fetchall()==[]

    # A write request must never auto-create an uninitialized DB.
    missing=base/"missing"
    missing.mkdir(mode=0o700)
    absent=missing/"tasks.db"
    denied(lambda:git.edit_git_task_fields(
        absent,expected_revision=0,expected_hash="0"*64,
        task_id="t2",changes={"title":"Missing"},now_ms=TIME+20),
        "DATABASE_ABSENT")
    assert not absent.exists()
    assert not hasattr(git,"send_github")
    assert not hasattr(git,"acknowledge_remote")
    print("M10v GIT atomic field intents, ordered revisions, rollback, recovery: PASS")
