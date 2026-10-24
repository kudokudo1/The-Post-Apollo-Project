#!/usr/bin/env python3
"""M10p disposable SQLite+flock admission-gate and crash/restart tests."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
FIX=ROOT/"tests/tasks/fixtures/TaskSqliteWriterAuthorityFixture.py"
spec=importlib.util.spec_from_file_location("tasks_m10p_fixture",FIX)
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

WRITER="quickshell-writer-generation-0008"
ANOTHER="different-writer-generation-0010"
TASK=b'{ "version":3,"nextId":2,"nextProjectId":1,"projects":[],"tasks":[] }\n'
SHA=hashlib.sha256(TASK).hexdigest()
serial=0

def denied(fn,expected):
    try:
        fn()
    except guard.AdmissionError as e:
        assert expected in str(e),(expected,str(e))
        return
    raise AssertionError("expected refusal: "+expected)

def root_at(base):
    global serial
    serial+=1
    parent=base/str(serial)
    parent.mkdir(mode=0o700)
    return parent/"handoff-test.db"

# Fresh Python processes must genuinely contend for the same flock.
child_code=r'''
import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("fixture",sys.argv[1])
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
try:
    with m.Authority(Path(sys.argv[2]),"other-process-generation-22"):
        print("UNEXPECTED_ACCESS")
        sys.exit(8)
except m.AdmissionError as e:
    print(str(e))
    sys.exit(0 if str(e)=="OTHER_PROCESS_OWNS_HANDOFF" else 9)
'''
# A child dies without running close(); OS must drop flock. SQLite state
# from the prior process must never authorize new stages after restart.
crash_code=r'''
import importlib.util,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("fixture",sys.argv[1])
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
db=Path(sys.argv[2])
a=m.Authority(db,"crashed-writer-generation-31",bootstrap=True)
if sys.argv[3]=="pending":
    a.admit_stage("save-while-crashing-001")
    a.freeze(0)
print("READY",flush=True)
os._exit(0)
'''

with tempfile.TemporaryDirectory(prefix="pa-m10p-fixtures-") as dirname:
    base=Path(dirname)
    db=root_at(base)
    with guard.Authority(db,WRITER,bootstrap=True) as authority:
        first=authority.snapshot()
        assert first["phase"]=="JSON_ACTIVE"
        assert first["epoch"]==0
        assert first["simulatedJsonStagePermitted"] is True
        assert first["sqliteWriteAuthorized"] is False
        assert first["liveChangePerformed"] is False

        contender=subprocess.run([sys.executable,"-B",child_code,str(FIX),str(db)],
             capture_output=True,text=True,timeout=10)
        assert contender.returncode==0,(contender.stdout,contender.stderr)
        assert "OTHER_PROCESS_OWNS_HANDOFF" in contender.stdout
        assert authority.snapshot()["phase"]=="JSON_ACTIVE"

        allowed=authority.admit_stage("save-token-00000001")
        assert allowed["admitted"] is True
        assert allowed["sqliteWriteAuthorized"] is False
        denied(lambda:authority.admit_stage("save-token-00000002"),"SAVE_IN_FLIGHT")
        denied(lambda:authority.freeze(9),"STALE_EPOCH")
        freeze=authority.freeze(0)
        assert freeze["phase"]=="FREEZE_REQUESTED"
        assert freeze["pendingStage"]=="save-token-00000001"
        assert authority.snapshot()["simulatedJsonStagePermitted"] is False
        denied(lambda:authority.admit_stage("save-token-00000003"),
               "LEGACY_STAGE_FROZEN")
        denied(lambda:authority.record_quiescence(TASK,TASK),"SAVE_NOT_DRAINED")
        denied(lambda:authority.settle_stage("save-token-99999999",saved=True),
               "STALE_SAVE_CALLBACK")
        settled=authority.settle_stage("save-token-00000001",saved=True)
        assert settled["phase"]=="FREEZE_REQUESTED"
        denied(lambda:authority.settle_stage("save-token-00000001",saved=True),
               "STALE_SAVE_CALLBACK")
        denied(lambda:authority.record_quiescence(TASK,TASK+b"changed"),
               "SOURCE_READBACK_MISMATCH")
        quiet=authority.record_quiescence(TASK,TASK)
        assert quiet["phase"]=="JSON_QUIESCED"
        assert quiet["sourceHash"]==SHA
        assert authority.snapshot()["sourceHash"]==SHA
        assert authority.snapshot()["sqliteWriteAuthorized"] is False
        denied(lambda:authority.admit_stage("save-token-00000004"),
               "LEGACY_STAGE_FROZEN")
        denied(lambda:authority.freeze(2),"UNEXPECTED_PHASE")

    # Merely reopening a previously clean handoff DB in a new owner
    # never recreates its earlier JSON_ACTIVE or QUIESCED admission.
    denied(lambda:authority.admit_stage("save-token-00000005"),"CLOSED_AUTHORITY")
    with guard.Authority(db,ANOTHER) as recovered:
        x=recovered.snapshot()
        assert x["phase"]=="RECOVERY_REVIEW"
        assert x["reason"]=="NEW_PROCESS_MUST_REVIEW"
        assert x["simulatedJsonStagePermitted"] is False
        assert x["sqliteWriteAuthorized"] is False
        denied(lambda:recovered.admit_stage("save-token-00000006"),
               "LEGACY_STAGE_FROZEN")
        denied(lambda:recovered.freeze(x["epoch"]),"UNEXPECTED_PHASE")

    # Explicitly failing FileView-like callback must persist RECOVERY_REVIEW.
    db=root_at(base)
    with guard.Authority(db,WRITER,bootstrap=True) as a:
        a.admit_stage("failed-stage-token-00001")
        a.freeze(0)
        failed=a.settle_stage("failed-stage-token-00001",saved=False)
        assert failed["callback"]=="FAILED"
        assert a.snapshot()["phase"]=="RECOVERY_REVIEW"
        assert a.snapshot()["reason"]=="LEGACY_SAVE_FAILED"
        denied(lambda:a.record_quiescence(TASK,TASK),"SAVE_NOT_DRAINED"
               if a.snapshot()["pendingStage"] else "UNEXPECTED_PHASE")
    with guard.Authority(db,ANOTHER) as a:
        assert a.snapshot()["phase"]=="RECOVERY_REVIEW"
        denied(lambda:a.admit_stage("new-stage-token-0007"),"LEGACY_STAGE_FROZEN")

    # Full JSON-active crash and pending-save/freeze crash, separate OS
    # process with os._exit(). Persistent SQLite gate reopens fail closed.
    for scenario in ("idle","pending"):
        db=root_at(base)
        child=subprocess.run([sys.executable,"-B",crash_code,str(FIX),
                              str(db),scenario],
                             capture_output=True,text=True,timeout=10)
        assert child.returncode==0,(scenario,child.stderr)
        assert "READY" in child.stdout
        with guard.Authority(db,ANOTHER) as reopened:
            state=reopened.snapshot()
            assert state["phase"]=="RECOVERY_REVIEW",scenario
            assert state["sqliteWriteAuthorized"] is False,scenario
            assert state["simulatedJsonStagePermitted"] is False,scenario
            if scenario=="pending":
                assert state["pendingStage"]=="save-while-crashing-001"
            denied(lambda:reopened.admit_stage("new-stage-token-0014"),
                   "LEGACY_STAGE_FROZEN")

    # Invalid/missing/unsafe paths do not initialize a live file.
    missing=root_at(base)
    denied(lambda:guard.Authority(missing,ANOTHER),"TEST_DB_MISSING")
    assert not missing.exists()
    denied(lambda:guard.Authority(base/"tasks.db",ANOTHER,bootstrap=True),
           "EXPLICIT_TEST_DB_REQUIRED")
    not_private=base/"unsafe"
    not_private.mkdir(mode=0o755)
    denied(lambda:guard.Authority(not_private/"handoff-test.db",
                                  ANOTHER,bootstrap=True),"UNSAFE_TEST_DIRECTORY")
    symlink_path=root_at(base)
    target=root_at(base)
    symlink_path.symlink_to(target)
    denied(lambda:guard.Authority(symlink_path,ANOTHER,bootstrap=True),
           "UNSAFE_DATABASE_LINK")
    assert not (base/"tasks.db").exists()
    # This fixture must never open TASKS's actual SQLite schema or expose
    # a remote/production write mechanism.
    assert not hasattr(guard,"activate_sqlite")
    assert not hasattr(guard,"migrate_live_tasks")
    assert not hasattr(guard,"send_remote")
print("TASKS M10p disposable flock plus durable admission gate and restart fencing: PASS")
