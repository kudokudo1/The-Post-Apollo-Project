#!/usr/bin/env python3
"""M10s disposable SQLite NORMAL task lifecycle and atomic failure windows."""
from __future__ import annotations

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

store = load(ROOT / "services/projects/ExperimentalTaskSqliteCrudM10s.py",
             "m10s_crud")
records = store.records
TIME = 1700000000000


def baseline():
    return {"version":2, "revision":0, "nextId":3, "nextProjectId":3,
            "nextOperationId":1,
            "projects":[
                {"id":"p1","name":"Personal","family":"normal","remote":None,
                 "fields":[],"createdAtMs":TIME,"updatedAtMs":TIME},
                {"id":"p2","name":"Linked","family":"git",
                 "remote":{"provider":"github","owner":"kudokudo1",
                           "projectNodeId":"PVT_unverified","projectNumber":14},
                 "fields":[{"id":"f1","label":"Note","kind":"text","scope":"local"}],
                 "createdAtMs":TIME,"updatedAtMs":TIME}],
            "tasks":[
                {"id":"t1","projectId":"p1","title":"Original","done":False,
                 "createdAtMs":TIME,"updatedAtMs":TIME,"priority":"none",
                 "description":"Preserve","dueDate":None,
                 "remote":None,"values":{}},
                {"id":"t2","projectId":"p2","title":"Remote-linked","done":False,
                 "createdAtMs":TIME,"updatedAtMs":TIME,"priority":"high",
                 "description":"Protected","dueDate":"2026-10-24",
                 "remote":None,"values":{"f1":"Keep local"}}],
            "operations":[]}


def denied(operation, reason):
    try:
        operation()
    except (store.StoreError, sqlite3.Error) as exc:
        assert reason in str(exc), (reason, str(exc))
        return
    raise AssertionError("Expected rejection: "+reason)


def run():
    with tempfile.TemporaryDirectory(prefix="pa-m10s-only-") as td:
        base=Path(td)
        db=base/"tasks.db"
        original=baseline()
        assert records.read(db)["status"]=="ABSENT"
        assert not db.exists()
        denied(lambda: store.create_task(
            db, expected_revision=0, expected_hash="0"*64,
            title="No implicit DB",due_date=None,now_ms=TIME),
            "DATABASE_ABSENT")
        assert not db.exists()
        records.initialize(db,original)
        def state():
            return records.read(db)
        def attempt(method, **kwargs):
            current=state()
            return method(db, expected_revision=current["revision"],
                          expected_hash=current["hash"], **kwargs)
        remote_original=state()["document"]["tasks"][1].copy()

        # Creation with a date is ONE revision and ONE verified SQL commit,
        # not an undated create followed by a second separately failing save.
        created=attempt(store.create_task,title="Doctor appointment",
                        due_date="2026-10-25", project_id="p1",
                        priority="medium",description="Visit",
                        now_ms=TIME+100)
        assert created["status"]=="LOCAL_COMMITTED"
        assert created["remoteIntentCreated"] is False
        assert created["remoteWriteAuthorized"] is False
        assert created["remoteSent"] is False
        assert created["id"]=="t3"
        after=state()
        assert after["revision"]==1 and after["document"]["nextId"]==4
        assert after["document"]["nextOperationId"]==1
        assert after["document"]["tasks"][2]["dueDate"]=="2026-10-25"
        assert after["document"]["tasks"][2]["description"]=="Visit"
        assert after["document"]["tasks"][1]==remote_original

        denied(lambda:attempt(store.create_task,title="Invalid date",
                  due_date="2026-02-30",now_ms=TIME+101), "INVALID_TASK_CREATE")
        denied(lambda:attempt(store.create_task,title="Should not be GIT",
                  due_date=None,project_id="p2",now_ms=TIME+101),
                  "GIT_PROJECT_UNSUPPORTED")
        denied(lambda:attempt(store.create_task,title="Not existent",
                  due_date=None,project_id="p9",now_ms=TIME+101),
                  "UNKNOWN_PROJECT")
        denied(lambda:attempt(store.create_task,title="   ",
                  due_date=None,now_ms=TIME+101), "INVALID_TASK_CREATE")
        assert state()["revision"]==1

        # New NORMAL project keeps its own stable ID and counter.
        new_project=attempt(store.create_normal_project,name="School",
                            now_ms=TIME+110)
        assert new_project["id"]=="p3"
        assert state()["document"]["nextProjectId"]==4
        denied(lambda:attempt(store.create_normal_project,name="school",
                  now_ms=TIME+111),"PROJECT_NAME_CONFLICT")
        denied(lambda:attempt(store.create_normal_project,name=" bad ",
                  now_ms=TIME+111),"INVALID_PROJECT_CREATE")

        # Assignment is local-only; refusal prevents accidental GIT mutations.
        assigned=attempt(store.assign_normal_project,task_id="t3",
                         project_id="p3",now_ms=TIME+120)
        assert assigned["id"]=="t3"
        assert state()["document"]["tasks"][2]["projectId"]=="p3"
        denied(lambda:attempt(store.assign_normal_project,task_id="t3",
                   project_id="p2",now_ms=TIME+121),"GIT_PROJECT_UNSUPPORTED")
        denied(lambda:attempt(store.assign_normal_project,task_id="t2",
                   project_id=None,now_ms=TIME+121),"GIT_PROJECT_UNSUPPORTED")
        denied(lambda:attempt(store.assign_normal_project,task_id="t3",
                   project_id="p3",now_ms=TIME+121),"NO_CHANGE")

        # Three detail fields update together in one transaction.
        previous=state()
        edited=attempt(store.edit_normal_task_details,task_id="t3",
                       priority="urgent",description="Updated details",
                       due_date="2024-02-29",now_ms=TIME+130)
        assert edited["revision"]==previous["revision"]+1
        row=state()["document"]["tasks"][2]
        assert (row["priority"],row["description"],row["dueDate"])==(
            "urgent","Updated details","2024-02-29")
        assert row["projectId"]=="p3"
        denied(lambda:attempt(store.edit_normal_task_details,task_id="t2",
                   priority="urgent",description="No",due_date=None,
                   now_ms=TIME+140),"GIT_PROJECT_UNSUPPORTED")
        denied(lambda:attempt(store.edit_normal_task_details,task_id="t3",
                   priority="high",description="No",
                   due_date="0001-02-29",now_ms=TIME+140),"INVALID_DETAILS")

        # Stale base refused before any row update or counter change.
        old=state()
        attempt(store.assign_normal_project,task_id="t3",
                project_id="p1",now_ms=TIME+140)
        denied(lambda:store.create_task(
            db,expected_revision=old["revision"],expected_hash=old["hash"],
            title="Stale",due_date=None,now_ms=TIME+150),"STALE_BASELINE")
        before=state()
        assert before["document"]["tasks"][1]==remote_original

        # Before-COMMIT fault rolls back task, journal and counters.
        try:
            attempt(store.create_task,title="Pre-commit interrupted",
                    due_date="2026-10-26",now_ms=TIME+160,
                    stop_at="before_commit")
        except store.InterruptedCommit as exc:
            assert "before_commit" in str(exc)
        else:
            raise AssertionError("Expected interruption")
        assert state()==before

        # After-COMMIT interruption is uncertain; must inspect, never retry.
        try:
            attempt(store.create_task,title="Post-commit interrupted",
                    due_date="2026-10-27",now_ms=TIME+170,
                    stop_at="after_commit")
        except store.InterruptedCommit as exc:
            assert "after_commit" in str(exc)
        else:
            raise AssertionError("Expected post-commit uncertainty")
        recovered=state()
        assert recovered["revision"]==before["revision"]+1
        assert recovered["document"]["tasks"][-1]["title"]=="Post-commit interrupted"
        assert recovered["document"]["nextOperationId"]==1

        # Guarded delete, stable IDs never reused and remaining rows persist.
        denied(lambda:attempt(store.remove_normal_task,task_id="t3",
                   confirmed=False),"DELETE_NOT_CONFIRMED")
        denied(lambda:attempt(store.remove_normal_task,task_id="t2",
                   confirmed=True),"GIT_PROJECT_UNSUPPORTED")
        deleted=attempt(store.remove_normal_task,task_id="t3",
                        confirmed=True)
        assert deleted["id"]=="t3"
        assert [t["id"] for t in state()["document"]["tasks"]]==["t1","t2","t4"]
        assert state()["document"]["nextId"]==5

        # Recreating after deleting a non-final row must NOT reuse its ID or
        # collide with the SQLite UNIQUE position of the surviving last row.
        created_again=attempt(store.create_task,title="After deletion",
                              due_date=None,now_ms=TIME+180)
        assert created_again["id"]=="t5"
        assert [t["id"] for t in state()["document"]["tasks"]]==[
            "t1","t2","t4","t5"]
        assert state()["document"]["tasks"][1]==remote_original
        assert state()["document"]["operations"]==[]
        with sqlite3.connect(db) as con:
            assert con.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
            assert con.execute("PRAGMA foreign_key_check").fetchall()==[]
            assert con.execute("PRAGMA user_version").fetchone()[0]==2
        print("M10s SQLite NORMAL CRUD + atomic dates, rollback, stale, recovery: PASS")

run()
