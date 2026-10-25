#!/usr/bin/env python3
"""M11c disposable clean-quiescence restart evidence, never executable rearm."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/tasks/fixtures/TaskWriterRecoveryM11c.py"
spec = importlib.util.spec_from_file_location("m11c_recovery", FIXTURE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SOURCE = b'{"version":3,"nextId":2,"nextProjectId":1,"projects":[],"tasks":[]}\n'
OWNER = "original-quickshell-owner-001"
NEW = "restart-quickshell-owner-0002"


def db_for(base, name):
    parent = base / name
    parent.mkdir(mode=0o700)
    f = parent / "legacy-test.json"
    fd = os.open(f, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(SOURCE)
        stream.flush()
        os.fsync(stream.fileno())
    return parent / "handoff-test.db", f


def denied(fn, reason):
    try:
        fn()
    except m.AdmissionError as exc:
        assert reason in str(exc), (reason, str(exc))
        return
    raise AssertionError("Expected " + reason)


def assert_non_authorizing(result):
    assert result["simulatedJsonStagePermitted"] is False
    assert result["legacyWriterEnforced"] is False
    assert result["sqliteWriteAuthorized"] is False
    assert result["remoteWriteAuthorized"] is False
    assert result["liveChangePerformed"] is False
    assert result["rearmPerformed"] is False


def drain(c):
    c.simulated_stage("stage-before-freeze-001")
    c.freeze(0)
    c.simulated_callback("stage-before-freeze-001", True)
    x=c.review_source_drain()
    assert x["phase"]=="JSON_QUIESCED"
    assert x["sourceHash"]==hashlib.sha256(SOURCE).hexdigest()


def full_checkpoint(c):
    drain(c)
    marker=c.mark_quiescent_close()
    assert marker["status"]=="BLOCKED"  # marker is NOT writer authority
    assert marker["reason"]=="QUIESCENCE_CHECKPOINT_SAVED"
    assert_non_authorizing(marker)
    denied(c.mark_quiescent_close, "CHECKPOINT_ALREADY_WRITTEN")


with tempfile.TemporaryDirectory(prefix="pa-m11c-recovery-") as dirname:
    base = Path(dirname)

    # Cleanly drained and checkpointed: new process still RECOVERY_REVIEW,
    # but the one-time inspection can distinguish it from an unknown crash.
    db,source=db_for(base,"clean")
    with m.RecoveryCoordinator(db, OWNER, bootstrap=True) as original:
        denied(original.mark_quiescent_close, "SOURCE_NOT_QUIESCED")
        full_checkpoint(original)
        assert original.inspect()["simulatedJsonStagePermitted"] is False
    with m.RecoveryCoordinator(db, NEW) as restarted:
        assert restarted.inspect()["phase"]=="RECOVERY_REVIEW"
        assert restarted.inspect()["simulatedJsonStagePermitted"] is False
        reviewed=restarted.inspect_restart()
        assert reviewed["status"]=="REVIEW_CANDIDATE"
        assert reviewed["reason"]=="QUIESCENT_CHECKPOINT_MATCHED_FOR_REVIEW"
        assert reviewed["reviewable"] is True
        assert_non_authorizing(reviewed)
        assert restarted.inspect()["phase"]=="RECOVERY_REVIEW"
        denied(lambda:restarted.simulated_stage("cannot-write-again-001"),
               "LEGACY_STAGE_FROZEN")
        repeated=restarted.inspect_restart()
        assert repeated["status"]=="BLOCKED"
        assert repeated["reason"]=="CHECKPOINT_ALREADY_CONSUMED"
        assert_non_authorizing(repeated)
    # A second ordinary process restart cannot replay the old marker.
    with m.RecoveryCoordinator(db, "third-owner-quickshell-0003") as third:
        stale=third.inspect_restart()
        assert stale["reason"]=="CHECKPOINT_ALREADY_CONSUMED"
        assert_non_authorizing(stale)

    # M10p still owns the OS lock. A real competing Python process cannot
    # inspect/rearm the fixture while the new owner owns its flock.
    db,source=db_for(base,"contested")
    with m.RecoveryCoordinator(db, OWNER, bootstrap=True) as first:
        child=r'''
import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("fixture",sys.argv[1])
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
try:
    with m.RecoveryCoordinator(Path(sys.argv[2]),"rival-owner-process-004"):
        print("UNEXPECTED_OWNER")
        sys.exit(3)
except m.AdmissionError as e:
    print(str(e))
    sys.exit(0 if str(e)=="OTHER_PROCESS_OWNS_HANDOFF" else 4)
'''
        rival=subprocess.run([sys.executable,"-B","-c",child,str(FIXTURE),str(db)],
                             capture_output=True,text=True,timeout=10)
        assert rival.returncode==0,(rival.stdout,rival.stderr)
        assert "OTHER_PROCESS_OWNS_HANDOFF" in rival.stdout

    # A restart without any durable clean marker cannot become eligible,
    # even though the source bytes happen to look stable.
    db,source=db_for(base,"unclean-idle")
    with m.RecoveryCoordinator(db, OWNER, bootstrap=True) as c:
        assert c.inspect()["phase"]=="JSON_ACTIVE"
    with m.RecoveryCoordinator(db, NEW) as c:
        unknown=c.inspect_restart()
        assert unknown["reason"]=="NO_VERIFIABLE_CHECKPOINT"
        assert unknown["reviewable"] is False
        assert_non_authorizing(unknown)

    # A save in flight at process death always blocks. This records neither
    # a clean checkpoint nor an accepted source hash.
    db,source=db_for(base,"pending-save")
    with m.RecoveryCoordinator(db,OWNER,bootstrap=True) as c:
        c.simulated_stage("pending-save-stage-005")
        c.freeze(0)
        denied(c.mark_quiescent_close,"SOURCE_NOT_QUIESCED")
    with m.RecoveryCoordinator(db,NEW) as c:
        assert c.inspect()["pendingStage"]=="pending-save-stage-005"
        unsafe=c.inspect_restart()
        assert unsafe["reviewable"] is False
        assert_non_authorizing(unsafe)

    # Failed save callback must not fabricate a clean close marker.
    db,source=db_for(base,"failed-callback")
    with m.RecoveryCoordinator(db,OWNER,bootstrap=True) as c:
        c.simulated_stage("save-failure-token-006")
        c.freeze(0)
        c.simulated_callback("save-failure-token-006",False)
        denied(c.mark_quiescent_close,"SOURCE_NOT_QUIESCED")
    with m.RecoveryCoordinator(db,NEW) as c:
        assert c.inspect_restart()["reviewable"] is False

    # Source mutated after a genuinely clean checkpoint: permanently
    # consume this candidate as BLOCKED, without accepting later repairs.
    db,source=db_for(base,"drift")
    with m.RecoveryCoordinator(db,OWNER,bootstrap=True) as c:
        full_checkpoint(c)
    with source.open("ab") as f:
        f.write(b"changed")
    with m.RecoveryCoordinator(db,NEW) as c:
        changed=c.inspect_restart()
        assert changed["reason"]=="SOURCE_MISMATCH_ON_RESTART"
        assert_non_authorizing(changed)
        source.write_bytes(SOURCE)  # synthetic repair does not restore eligibility
        assert c.inspect_restart()["reason"]=="CHECKPOINT_ALREADY_CONSUMED"

    # Mutation between the two live reads must also remain blocked.
    db,source=db_for(base,"race")
    with m.RecoveryCoordinator(db,OWNER,bootstrap=True) as c:
        full_checkpoint(c)
    with m.RecoveryCoordinator(db,NEW) as c:
        def mutation():
            source.write_bytes(SOURCE+b" ")
        race=c.inspect_restart(between_reads=mutation)
        assert race["reason"]=="SOURCE_MISMATCH_ON_RESTART"
        assert_non_authorizing(race)

    # Interrupted process after a clean checkpoint is indistinguishable
    # from a clean exit at this layer: review CANDIDATE, not write permission.
    db,source=db_for(base,"post-checkpoint-crash")
    crashed=r'''
import importlib.util,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("fixture",sys.argv[1])
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
c=m.RecoveryCoordinator(Path(sys.argv[2]),"crashed-owner-generation-007",bootstrap=True)
c.simulated_stage("before-fault-stage-007")
c.freeze(0)
c.simulated_callback("before-fault-stage-007",True)
c.review_source_drain()
c.mark_quiescent_close()
print("CHECKPOINTED",flush=True)
os._exit(0)
'''
    abrupt=subprocess.run([sys.executable,"-B","-c",crashed,
                           str(FIXTURE),str(db)],
                          capture_output=True,text=True,timeout=10)
    assert abrupt.returncode==0,(abrupt.stdout,abrupt.stderr)
    assert "CHECKPOINTED" in abrupt.stdout
    with m.RecoveryCoordinator(db,NEW) as c:
        crash=c.inspect_restart()
        assert crash["reviewable"] is True
        assert_non_authorizing(crash)
        denied(lambda:c.simulated_stage("stale-stage-after-crash-008"),
               "LEGACY_STAGE_FROZEN")

    # Pre-checkpoint crash with unsettled callback is never reviewable.
    db,source=db_for(base,"before-checkpoint-crash")
    crashed_pending=r'''
import importlib.util,os,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("fixture",sys.argv[1])
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
c=m.RecoveryCoordinator(Path(sys.argv[2]),"crashed-pending-generation-009",bootstrap=True)
c.simulated_stage("pending-at-crash-token-009")
print("PENDING",flush=True)
os._exit(0)
'''
    proc=subprocess.run([sys.executable,"-B","-c",crashed_pending,
                         str(FIXTURE),str(db)],
                        capture_output=True,text=True,timeout=10)
    assert proc.returncode==0
    with m.RecoveryCoordinator(db,NEW) as c:
        unsafe=c.inspect_restart()
        assert unsafe["reviewable"] is False
        assert_non_authorizing(unsafe)

    # Corrupt durable marker must not lead to rearm. One-time consumption
    # remains persisted and no user data is changed.
    db,source=db_for(base,"marker-tamper")
    with m.RecoveryCoordinator(db,OWNER,bootstrap=True) as c:
        full_checkpoint(c)
    with sqlite3.connect(db) as con:
        con.execute("UPDATE restart_review SET source_hash='bad' WHERE singleton=1")
    with m.RecoveryCoordinator(db,NEW) as c:
        bad=c.inspect_restart()
        assert bad["reason"]=="NO_VERIFIABLE_CHECKPOINT"
        assert_non_authorizing(bad)

    # Confine all test access to a private explicit directory and filename.
    denied(lambda:m.RecoveryCoordinator(base/"tasks.db",OWNER,bootstrap=True),
           "EXPLICIT_TEST_DB_REQUIRED")
    assert not (base/"tasks.db").exists()
    assert not hasattr(m.RecoveryCoordinator,"activate_sqlite")
    assert not hasattr(m.RecoveryCoordinator,"rearm_live")
    assert not hasattr(m.RecoveryCoordinator,"send_github")

print("M11c durable one-use restart review, drift, crash and strict no-rearm: PASS")
