#!/usr/bin/env python3
"""M10q: test-only JSONL host + static unmounted Quickshell Process seam."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "tests/tasks/fixtures/TaskSqliteHandoffHost.py"
QML = ROOT / "services/projects/TaskSqliteAdmissionRehearsal.qml"
WRITER = "qs-session-fixture-owner-002"
SECOND = "qs-session-other-owner-003"


def launch(path, *, bootstrap=False, writer=WRITER):
    cmd = [sys.executable, "-B", "-I", str(HOST),
           "--db", str(path), "--writer-id", writer]
    if bootstrap:
        cmd.append("--bootstrap-fixture")
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, bufsize=1)
    hello = json.loads(p.stdout.readline())
    return p, hello


def request(p, rid, kind, **fields):
    payload = {"requestId": rid, "kind": kind, **fields}
    p.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
    p.stdin.flush()
    return json.loads(p.stdout.readline())


def check(response, *, rid, kind, ok, phase=None, status=None):
    assert response["protocol"] == 1, response
    assert response["requestId"] == rid, response
    assert response["kind"] == kind, response
    assert response["ok"] is ok, response
    if phase is not None:
        assert response["phase"] == phase, response
    if status is not None:
        assert response["status"] == status, response
    assert response["sqliteWriteAuthorized"] is False, response
    assert response["liveChangePerformed"] is False, response
    assert len(response) == 11, response
    assert "task" not in response and "path" not in response
    return response


def finish(p):
    p.stdin.close()
    p.wait(timeout=10)
    assert p.returncode in (0, 2)
    return p.returncode


with tempfile.TemporaryDirectory(prefix="pa-m10q-host-") as home:
    root=Path(home)
    path=root/"handoff-test.db"
    p,hello=launch(path,bootstrap=True)
    check(hello,rid=0,kind="hello",ok=True,phase="JSON_ACTIVE")
    assert hello["simulatedAdmission"] is True
    assert hello["epoch"] == 0
    assert path.exists()

    # Actual separate process is prevented from using the same flock
    # until the original persistent worker releases ownership.
    other, unavailable=launch(path,writer=SECOND)
    check(unavailable,rid=0,kind="hello",ok=False,status="AUTHORITY_UNAVAILABLE")
    assert finish(other)==2

    c=check(request(p,1,"status"),rid=1,kind="status",ok=True,
            phase="JSON_ACTIVE")
    assert c["pending"] is False and c["simulatedAdmission"] is True
    c=check(request(p,2,"admit",stageId="synthetic-stage-0001"),
            rid=2,kind="admit",ok=True,phase="JSON_ACTIVE")
    assert c["pending"] is True and c["simulatedAdmission"] is False
    c=check(request(p,3,"admit",stageId="synthetic-stage-0002"),
            rid=3,kind="admit",ok=False,status="SAVE_IN_FLIGHT")
    assert c["pending"] is True
    c=check(request(p,4,"freeze",expectedEpoch=0),
            rid=4,kind="freeze",ok=True,phase="FREEZE_REQUESTED")
    assert c["epoch"] == 1 and c["pending"] is True
    check(request(p,5,"admit",stageId="synthetic-stage-0003"),
          rid=5,kind="admit",ok=False,status="LEGACY_STAGE_FROZEN")
    check(request(p,6,"settle",stageId="incorrect-callback-111",saved=True),
          rid=6,kind="settle",ok=False,status="STALE_SAVE_CALLBACK")
    c=check(request(p,7,"settle",stageId="synthetic-stage-0001",saved=True),
          rid=7,kind="settle",ok=True,phase="FREEZE_REQUESTED")
    assert c["pending"] is False
    check(request(p,8,"settle",stageId="synthetic-stage-0001",saved=True),
          rid=8,kind="settle",ok=False,status="STALE_SAVE_CALLBACK")
    check(request(p,9,"freeze",expectedEpoch=1),
          rid=9,kind="freeze",ok=False,status="UNEXPECTED_PHASE")
    assert finish(p)==0

    # New host after normal stop must fence old writer, not reactivate it.
    restart,hello=launch(path,writer=SECOND)
    check(hello,rid=0,kind="hello",ok=True,phase="RECOVERY_REVIEW")
    assert hello["simulatedAdmission"] is False and hello["epoch"]==2
    check(request(restart,1,"admit",stageId="synthetic-stage-444"),
          rid=1,kind="admit",ok=False,status="LEGACY_STAGE_FROZEN")
    check(request(restart,2,"status"),
          rid=2,kind="status",ok=True,phase="RECOVERY_REVIEW")
    assert finish(restart)==0

    # A failed save is persisted as RECOVERY_REVIEW, not reported SAVED.
    fail_dir=root/"failure"
    fail_dir.mkdir(mode=0o700)
    fail_db=fail_dir/"handoff-test.db"
    p,hello=launch(fail_db,bootstrap=True)
    check(hello,rid=0,kind="hello",ok=True)
    check(request(p,1,"admit",stageId="simulated-failing-stage-002"),
          rid=1,kind="admit",ok=True)
    c=check(request(p,2,"settle",
                    stageId="simulated-failing-stage-002",saved=False),
            rid=2,kind="settle",ok=True,phase="RECOVERY_REVIEW")
    assert c["pending"] is True
    check(request(p,3,"admit",stageId="simulated-stage-003"),
          rid=3,kind="admit",ok=False,status="LEGACY_STAGE_FROZEN")
    assert finish(p)==0

    # Unknown instructions, forged activation, and incorrect input shapes
    # must never grant a SQLite writer or change stage authority.
    malformed_dir=root/"malformed"
    malformed_dir.mkdir(mode=0o700)
    malformed=malformed_dir/"handoff-test.db"
    p,hello=launch(malformed,bootstrap=True)
    check(hello,rid=0,kind="hello",ok=True)
    check(request(p,1,"activate",operatorApproved=True),
          rid=1,kind="activate",ok=False,status="UNSUPPORTED_COMMAND")
    check(request(p,2,"admit",stageId="bad",sqliteWriteAuthorized=True),
          rid=2,kind="admit",ok=False,status="UNSUPPORTED_COMMAND")
    check(request(p,3,"freeze",expectedEpoch=True),
          rid=3,kind="freeze",ok=False,status="STALE_EPOCH")
    check(request(p,4,"settle",stageId="bad",saved="yes"),
          rid=4,kind="settle",ok=False,status="INVALID_CALLBACK")
    check(request(p,5,"status"),
          rid=5,kind="status",ok=True,phase="JSON_ACTIVE")
    assert finish(p)==0

    # Replayed message ids terminate the connection and cannot be used to
    # smuggle a second mutation into the same owner generation.
    replay_dir=root/"replay"
    replay_dir.mkdir(mode=0o700)
    replay_db=replay_dir/"handoff-test.db"
    p,hello=launch(replay_db,bootstrap=True)
    check(hello,rid=0,kind="hello",ok=True)
    check(request(p,1,"status"),rid=1,kind="status",ok=True)
    replay=request(p,1,"admit",stageId="replay-save-token-0001")
    check(replay,rid=None,kind="protocol",ok=False,
          status="INVALID_OR_REPLAYED_REQUEST")
    assert finish(p)==2
    p,hello=launch(replay_db)
    check(hello,rid=0,kind="hello",ok=True,phase="RECOVERY_REVIEW")
    assert hello["pending"] is False
    assert finish(p)==0

    # No auto-bootstrap after ordinary QS restart. Missing private path
    # remains untouched; live tasks.db cannot be passed as fixture.
    absent_dir=root/"absent"
    absent_dir.mkdir(mode=0o700)
    absent=absent_dir/"handoff-test.db"
    p,hello=launch(absent)
    check(hello,rid=0,kind="hello",ok=False,status="AUTHORITY_UNAVAILABLE")
    assert finish(p)==2 and not absent.exists()
    wrong_db=root/"tasks.db"
    p,hello=launch(wrong_db,bootstrap=True)
    check(hello,rid=0,kind="hello",ok=False,status="EXPLICIT_TEST_DB_REQUIRED")
    assert finish(p)==2 and not wrong_db.exists()
    # Repeated initialization never overwrites an existing authority DB.
    p,hello=launch(path,bootstrap=True)
    check(hello,rid=0,kind="hello",ok=False,status="AUTHORITY_UNAVAILABLE")
    assert finish(p)==2

qml=QML.read_text()
assert "Scope {" in qml and "Process {" in qml and "SplitParser {" in qml
assert "stdinEnabled: true" in qml and "host.write(" in qml
assert '["python3", "-B", "-I"' in qml
assert "function beginRehearsal()" in qml
assert "function simulateStage(" in qml
assert "function simulateFreeze()" in qml
assert "function simulateSaveCallback(" in qml
assert "function stopRehearsal()" in qml
assert "readonly property bool writeReady: false" in qml
assert "readonly property bool sqliteWriteAuthorized: false" in qml
assert "readonly property bool liveChangePerformed: false" in qml
assert '--bootstrap-fixture' not in qml
for forbidden in ("FileView {", "setText(", "onCompleted:",
                  "Timer {", "running: true", "manageLifetime: false",
                  "Quickshell.dataDir", "function activate(", "startDetached("):
    assert forbidden not in qml, forbidden
# Prove the rehearsal bridge is unmounted in production widgets and services.
for file in list((ROOT/"services").rglob("*.qml")) + list((ROOT/"widgets").rglob("*.qml")):
    if file == QML:
        continue
    assert "TaskSqliteAdmissionRehearsal" not in file.read_text(), file
assert "TaskSqliteAdmissionRehearsal" not in (ROOT/"shell.qml").read_text()
print("TASKS M10q persistent read-only QML rehearsal and disposable authority protocol: PASS")
