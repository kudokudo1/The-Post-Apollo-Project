#!/usr/bin/env python3
"""M11b test-only flock + actual disposable JSON source + restart fencing."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
FIX=ROOT/"tests/tasks/fixtures/TaskWriterCoordinationM11b.py"
spec=importlib.util.spec_from_file_location("m11b_coordination",FIX)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SOURCE=b'{"version":3,"nextId":2,"nextProjectId":1,"projects":[],"tasks":[]}\n'
OWNER="quickshell-fixture-owner-004"
OTHER="quickshell-fixture-owner-005"


def denied(fn, code):
    try:
        fn()
    except m.AdmissionError as exc:
        assert code in str(exc), (code, str(exc))
        return
    raise AssertionError("Expected "+code)


def fixture(base, label):
    parent=base/label
    parent.mkdir(mode=0o700)
    source=parent/"legacy-test.json"
    fd=os.open(source, os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as stream:
        stream.write(SOURCE)
        stream.flush()
        os.fsync(stream.fileno())
    return parent/"handoff-test.db",source


child=r'''
import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("m11b_other",sys.argv[1])
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
try:
    with m.Coordinator(Path(sys.argv[2]),"other-process-fixture-999"):
        print("UNEXPECTED")
        sys.exit(4)
except m.AdmissionError as exc:
    print(str(exc))
    sys.exit(0 if str(exc)=="OTHER_PROCESS_OWNS_HANDOFF" else 5)
'''

with tempfile.TemporaryDirectory(prefix="pa-m11b-coordination-") as folder:
    base=Path(folder)
    db,source=fixture(base,"normal")
    with m.Coordinator(db,OWNER,bootstrap=True) as coordinator:
        state=coordinator.inspect()
        assert state["phase"]=="JSON_ACTIVE"
        assert state["simulatedJsonStagePermitted"] is True
        assert state["legacyWriterEnforced"] is False
        assert state["sqliteWriteAuthorized"] is False
        assert state["remoteWriteAuthorized"] is False
        assert state["liveChangePerformed"] is False

        # An actual other OS process may NOT claim the test fixture while
        # its first owner's persistent flock remains held.
        p=subprocess.run([sys.executable,"-B","-c",child,str(FIX),str(db)],
                         capture_output=True,text=True,timeout=10)
        assert p.returncode==0,(p.stdout,p.stderr)
        assert "OTHER_PROCESS_OWNS_HANDOFF" in p.stdout
        assert source.read_bytes()==SOURCE

        denied(lambda:coordinator.review_source_drain(),"FREEZE_NOT_REQUESTED")
        coordinator.simulated_stage("first-save-token-001")
        denied(lambda:coordinator.simulated_stage("another-save-token-002"),
               "SAVE_IN_FLIGHT")
        denied(lambda:coordinator.freeze(1),"STALE_EPOCH")
        frozen=coordinator.freeze(0)
        assert frozen["phase"]=="FREEZE_REQUESTED"
        assert frozen["pendingStage"]=="first-save-token-001"
        assert frozen["simulatedJsonStagePermitted"] is False
        denied(lambda:coordinator.simulated_stage("third-save-token-003"),
               "LEGACY_STAGE_FROZEN")
        denied(lambda:coordinator.review_source_drain(),"SAVE_NOT_DRAINED")
        denied(lambda:coordinator.simulated_callback("wrong-callback-004",True),
               "STALE_SAVE_CALLBACK")
        coordinator.simulated_callback("first-save-token-001",True)
        denied(lambda:coordinator.simulated_callback("first-save-token-001",True),
               "STALE_SAVE_CALLBACK")
        saved=coordinator.review_source_drain()
        assert saved["phase"]=="JSON_QUIESCED"
        assert saved["pendingStage"] is None
        assert saved["sourceHash"]==hashlib.sha256(SOURCE).hexdigest()
        assert saved["sqliteWriteAuthorized"] is False
        assert source.read_bytes()==SOURCE
        denied(lambda:coordinator.simulated_stage("late-stage-token-005"),
               "LEGACY_STAGE_FROZEN")

    # Reopening the same durable fixture never silently reauthorizes JSON
    # admission, even after an entirely clean test-only drain.
    with m.Coordinator(db,OTHER) as restart:
        snapshot=restart.inspect()
        assert snapshot["phase"]=="RECOVERY_REVIEW"
        assert snapshot["epoch"]>saved["epoch"]
        assert snapshot["simulatedJsonStagePermitted"] is False
        assert snapshot["sqliteWriteAuthorized"] is False
        denied(lambda:restart.simulated_stage("rebooted-stage-token"),
               "LEGACY_STAGE_FROZEN")
        denied(lambda:restart.review_source_drain(),"FREEZE_NOT_REQUESTED")

    # A second source read catches an external synthetic change and refuses
    # to persist the JSON_QUIESCED phase or imply any writer safety.
    db,source=fixture(base,"racing-source")
    with m.Coordinator(db,OWNER,bootstrap=True) as race:
        race.freeze(0)
        def mutate():
            source.write_bytes(SOURCE+b' \n')
        denied(lambda:race.review_source_drain(between_reads=mutate),
               "SOURCE_READBACK_MISMATCH")
        assert race.inspect()["phase"]=="FREEZE_REQUESTED"
        assert race.inspect()["sourceHash"] is None
        assert race.inspect()["sqliteWriteAuthorized"] is False

    # An unsuccessful save callback persists RECOVERY_REVIEW.
    db,source=fixture(base,"save-failed")
    with m.Coordinator(db,OWNER,bootstrap=True) as failed:
        failed.simulated_stage("failed-save-token-009")
        failed.freeze(0)
        observation=failed.simulated_callback("failed-save-token-009",False)
        assert observation["phase"]=="RECOVERY_REVIEW"
        assert observation["sqliteWriteAuthorized"] is False
        denied(lambda:failed.review_source_drain(),"FREEZE_NOT_REQUESTED")

    # Bad/missing/private paths, symlinks and unsafe modes refuse opening.
    db,source=fixture(base,"bad-mode")
    source.chmod(0o644)
    denied(lambda:m.Coordinator(db,OWNER,bootstrap=True),"UNSAFE_TEST_SOURCE")
    assert not db.exists()
    db,source=fixture(base,"symlink")
    source.unlink()
    source.symlink_to(base/"normal"/"legacy-test.json")
    denied(lambda:m.Coordinator(db,OWNER,bootstrap=True),"UNSAFE_TEST_SOURCE")
    assert not db.exists()
    db,source=fixture(base,"missing")
    source.unlink()
    denied(lambda:m.Coordinator(db,OWNER,bootstrap=True),"TEST_SOURCE_MISSING")
    assert not db.exists()
    denied(lambda:m.Coordinator(base/"tasks.db",OWNER,bootstrap=True),
           "EXPLICIT_TEST_DB_REQUIRED")
    assert not (base/"tasks.db").exists()

    # The test-only coordinator exposes no executable production authority.
    assert not hasattr(m.Coordinator,"activate_sqlite")
    assert not hasattr(m.Coordinator,"rearm_live_writer")
    assert not hasattr(m.Coordinator,"write_json")
    assert not hasattr(m.Coordinator,"send_github")
    assert not hasattr(m.Coordinator,"migrate")
print("M11b OS flock, source-read freeze/drain, restart and fail-closed ownership: PASS")
