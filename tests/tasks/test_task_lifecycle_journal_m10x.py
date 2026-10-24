#!/usr/bin/env python3
"""M10x PRIVATE lifecycle-test.db persistence, dependency and crash tests.

Uses synthetic data and isolated temp files. Never opens the TASKS database,
calls Quickshell, contacts GitHub or authorizes remote lifecycle operations.
"""
from __future__ import annotations

import copy
import importlib.util
import os
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "m10x_fixture", ROOT / "services/projects/ExperimentalTaskLifecycleJournalM10x.py")
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)
proposal = store.review
TIME = 1700000000000
REMOTE = {"projectItemNodeId":"PVTI_unverified",
          "contentKind":"DRAFT_ISSUE","contentNodeId":None}


def project(pid, name, family):
    return {"id":pid,"name":name,"family":family,
            "remote":None if family=="normal" else {
                "provider":"github","owner":"kudokudo1",
                "projectNodeId":"PVT_unverified_"+pid,"projectNumber":14},
            "fields":[],"createdAtMs":TIME,"updatedAtMs":TIME}


def task(tid, pid, title, remote=None):
    return {"id":tid,"title":title,"done":False,"priority":"medium",
            "description":"Private description "+tid,"dueDate":"2026-10-24",
            "projectId":pid,"remote":copy.deepcopy(remote),"values":{},
            "createdAtMs":TIME,"updatedAtMs":TIME}


def model():
    return {"version":2,"revision":0,"nextId":5,"nextProjectId":4,
            "nextOperationId":1,
            "projects":[project("p1","Home","normal"),
                        project("p2","Remote A","git"),
                        project("p3","Remote B","git")],
            "tasks":[task("t1","p1","Home task"),
                     task("t2","p2","Create candidate"),
                     task("t3","p2","Move/delete candidate",REMOTE),
                     task("t4","p2","Other task",REMOTE)],
            "operations":[]}


CREATE = {"kind":"CREATE_GIT_TASK","taskId":"t2"}
MOVE = {"kind":"MOVE_GIT_TASK","taskId":"t3","targetProjectId":"p3"}
DELETE = {"kind":"DELETE_GIT_TASK","taskId":"t3","confirmed":True}
DELETE_OTHER = {"kind":"DELETE_GIT_TASK","taskId":"t4","confirmed":True}


def denied(fn, expected):
    try:
        fn()
    except (store.StoreError, sqlite3.Error) as exc:
        assert expected in str(exc), (expected, str(exc))
        return
    raise AssertionError("Expected " + expected)


with tempfile.TemporaryDirectory(prefix="pa-m10x-lifecycle-") as td:
    base = Path(td)
    source = model()
    original = copy.deepcopy(source)
    proposals = {kind:proposal.propose(source,req) for kind,req in (
        ("create",CREATE),("move",MOVE),("delete",DELETE),
        ("other",DELETE_OTHER))}
    db = base / "lifecycle-test.db"
    assert store.read(db) == {"status":"ABSENT","available":False}
    assert not db.exists()
    denied(lambda:store.append_held(
        db,expected_revision=0,expected_head=store.ZERO_HASH,
        source_model=source,request=CREATE,reviewed_preview=proposals["create"]),
        "FIXTURE_ABSENT")
    assert not db.exists()
    initial = store.initialize(db)
    assert initial["status"] == "TEST_FIXTURE_INITIALIZED"
    assert initial["remoteWriteAuthorized"] is False
    assert not hasattr(store, "send_github")
    assert not hasattr(store, "enable_sync")
    assert not hasattr(store, "activate_live")
    assert store.read(db)["fixtureVersion"] == 3
    assert store.read(db)["headHash"] == store.ZERO_HASH
    assert store.read(db)["intents"] == []
    assert (db.stat().st_mode & 0o777) == 0o600
    try:
        store.initialize(db)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Second initialization must never replace data")

    def append(req, preview, *, file=db, depends=(), **extra):
        current=store.read(file)
        return store.append_held(
            file,expected_revision=current["revision"],
            expected_head=current["headHash"],source_model=source,
            request=req,reviewed_preview=preview,depends_on=depends,**extra)

    # Stable independent lx IDs avoid falsely reserving the v2 opN namespace.
    create=append(CREATE,proposals["create"])
    assert create["status"]=="HELD_REVIEW_SAVED"
    assert create["id"]=="lx1"
    assert create["journalWriteAuthorized"] is False
    assert create["remoteWriteAuthorized"] is False
    assert create["remoteSent"] is False
    assert source==original
    assert store.read(db)["revision"]==1

    # Append an independent GIT move; then require an explicit dependency
    # before a later DELETE proposal may be retained for the same task.
    moved=append(MOVE,proposals["move"])
    assert moved["id"]=="lx2"
    frozen=store.read(db)
    denied(lambda:append(DELETE,proposals["delete"]),
           "TASK_DEPENDENCY_REQUIRED")
    assert store.read(db)==frozen
    deleted=append(DELETE,proposals["delete"],depends=("lx2",))
    assert deleted["id"]=="lx3"
    status=store.read(db)
    assert status["revision"]==3 and status["nextId"]==4
    assert [item["id"] for item in status["intents"]]==["lx1","lx2","lx3"]
    assert [item["state"] for item in status["intents"]]==["HELD"]*3
    assert status["intents"][2]["dependencies"]==["lx2"]
    assert status["intents"][2]["tombstone"]==original["tasks"][2]
    assert status["remoteWriteAuthorized"] is False
    assert status["remoteAcknowledged"] is False
    assert source==original
    assert status["intents"][2]["sourceRevision"]==0
    assert status["intents"][2]["sourceHash"]==proposal.records._hash(source)
    with sqlite3.connect(db) as sql:
        assert sql.execute("SELECT COUNT(*) FROM tombstones").fetchone()[0]==1
        assert sql.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        assert sql.execute("PRAGMA foreign_key_check").fetchall()==[]

    # Once deletion is proposed no further move can be appended for that
    # same task. The entire chain stays HELD and cannot be dispatched.
    denied(lambda:append(MOVE,proposals["move"],depends=("lx2","lx3")),
           "DELETION_ALREADY_PROPOSED")
    denied(lambda:append(DELETE_OTHER,proposals["other"],depends=("lx99",)),
           "UNKNOWN_DEPENDENCY")
    denied(lambda:append(DELETE_OTHER,proposals["other"],depends=("lx2","lx2")),
           "INVALID_INTENT_DEPENDENCIES")
    denied(lambda:append(DELETE_OTHER,proposals["other"],depends=("lx5",)),
           "UNKNOWN_DEPENDENCY")
    assert store.read(db)==status

    # No stale revision or hash can append. No fake source, preview, or
    # unexpected request shape bypasses M10w's exact re-derivation.
    denied(lambda:store.append_held(
        db,expected_revision=0,expected_head=store.ZERO_HASH,
        source_model=source,request=DELETE_OTHER,
        reviewed_preview=proposals["other"]), "STALE_FIXTURE_BASELINE")
    altered=copy.deepcopy(proposals["other"])
    altered["proposedOperationId"]="op99"
    denied(lambda:append(DELETE_OTHER,altered),"PREVIEW_INVALID_OR_STALE")
    changed=copy.deepcopy(source)
    changed["tasks"][3]["title"]="Edited"
    changed["revision"]+=1
    denied(lambda:store.append_held(
        db,expected_revision=3,expected_head=status["headHash"],
        source_model=changed,request=DELETE_OTHER,
        reviewed_preview=proposals["other"]), "PREVIEW_INVALID_OR_STALE")

    # Simulated precommit crashes leave intent, tombstone and metadata
    # unchanged. A postcommit injected failure has a complete saved review
    # but requires fresh-read reconciliation, not a blind replay.
    phases=("before_intent_insert","after_intent_insert",
            "after_tombstone_insert","before_commit","after_commit")
    for num,phase in enumerate(phases,1):
        root=base/("fault"+str(num))
        root.mkdir(mode=0o700)
        file=root/"lifecycle-test.db"
        store.initialize(file)
        before=store.read(file)
        try:
            append(DELETE_OTHER,proposals["other"],file=file,stop_at=phase)
        except store.InterruptedCommit as exc:
            assert phase in str(exc),(phase,str(exc))
        else:
            raise AssertionError("Expected injected phase "+phase)
        after=store.read(file)
        if phase=="after_commit":
            assert after["revision"]==1
            assert after["intents"][0]["tombstone"]==original["tasks"][3]
            assert after["intents"][0]["state"]=="HELD"
            denied(lambda:store.append_held(
                file,expected_revision=before["revision"],
                expected_head=before["headHash"],source_model=source,
                request=DELETE_OTHER,reviewed_preview=proposals["other"]),
                "STALE_FIXTURE_BASELINE")
        else:
            assert after==before, phase
        with sqlite3.connect(file) as sql:
            assert sql.execute("SELECT COUNT(*) FROM tombstones").fetchone()[0]==(
                1 if phase=="after_commit" else 0)
            assert sql.execute("PRAGMA foreign_key_check").fetchall()==[]

    # Fresh read detects an unverified tampered tombstone rather than
    # silently dropping it. An unrelated test DB is used for corruption.
    corrupt_root=base/"tamper"
    corrupt_root.mkdir(mode=0o700)
    corrupt=corrupt_root/"lifecycle-test.db"
    store.initialize(corrupt)
    append(DELETE_OTHER,proposals["other"],file=corrupt)
    with sqlite3.connect(corrupt) as sql:
        sql.execute("UPDATE tombstones SET task_json=? WHERE intent_id='lx1'",
                    ('{"id":"t4","title":"replaced"}',))
    denied(lambda:store.read(corrupt),"TOMBSTONE_MISMATCH")

    # Files in the user's live TASKS path cannot be guessed or opened.
    denied(lambda:store.initialize(base/"tasks.db"),
           "EXPLICIT_TEST_DB_PATH_REQUIRED")
    denied(lambda:store.initialize(Path("lifecycle-test.db")),
           "EXPLICIT_TEST_DB_PATH_REQUIRED")
    missing=base/"no-such-parent"/"lifecycle-test.db"
    denied(lambda:store.initialize(missing),"PRIVATE_TEST_DIRECTORY_REQUIRED")
    assert not missing.parent.exists()
    symlink=base/"linked"
    symlink.symlink_to(db)
    denied(lambda:store.read(symlink),"EXPLICIT_TEST_DB_PATH_REQUIRED")
    assert source==original
    print("M10x isolated lifecycle HELD journal, dependencies, tombstones and crash recovery: PASS")
