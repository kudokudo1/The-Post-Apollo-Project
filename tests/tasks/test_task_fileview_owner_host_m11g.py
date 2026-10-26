#!/usr/bin/env python3
"""M11g real subprocess/OS-flock/test-file simulation and QML source boundary.

The CI runner does not launch Quickshell: it simulates FileView's atomic
rename and callback by writing ONLY an isolated synthetic fixture. Actual
native Process/FileView event interleavings remain an on-device test gate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
HOST=ROOT/"tests/tasks/fixtures/TaskFileViewOwnerHostM11g.py"
INIT=ROOT/"tests/tasks/fixtures/m11e_fileview_fixture.py"
BRIDGE=ROOT/"services/projects/TaskFileViewHostBridgeM11g.qml"
HARNESS=ROOT/"TaskFileViewHostHarnessM11g.qml"
WRITER="m11g-fixture-owner-1000"
OTHER="m11g-fixture-owner-2000"


def read(p):
    raw=p.stdout.readline()
    assert raw,(p.poll(),p.stderr.read())
    ans=json.loads(raw)
    assert ans["protocol"]==1
    assert ans["liveWriterAuthorized"] is False
    assert ans["sqliteWriteAuthorized"] is False
    assert ans["remoteWriteAuthorized"] is False
    assert ans["migrationAuthorized"] is False
    assert len(ans)==13
    return ans


def start(db,*,bootstrap=False,owner=WRITER):
    cmd=[sys.executable,"-B","-I",str(HOST),
         "--db",str(db),"--writer-id",owner]
    if bootstrap: cmd.append("--bootstrap-fixture")
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,text=True,bufsize=1)
    return p,read(p)


def ask(p,n,kind,**params):
    p.stdin.write(json.dumps({"requestId":n,"kind":kind,**params},
                             separators=(",",":"))+"\n")
    p.stdin.flush()
    result=read(p)
    assert result["requestId"]==n and result["kind"]==kind,result
    return result


def close(p,*,expected=0):
    if p.stdin and not p.stdin.closed: p.stdin.close()
    p.wait(timeout=15)
    assert p.returncode==expected,(p.returncode,p.stderr.read())


def new_fixture(root,label):
    folder=root/label/"m11e-fileview-test"
    folder.mkdir(parents=True,mode=0o700)
    file=folder/"fixture-only.json"
    result=subprocess.run([sys.executable,"-B","-I",str(INIT),
                           "--file",str(file)],capture_output=True,
                          text=True,timeout=15)
    assert result.returncode==0,(result.stdout,result.stderr)
    return folder/"handoff-test.db",file


def synthetic_write(file,content):
    assert file.name=="fixture-only.json"
    temp=file.parent/"fixture-in-flight.tmp"
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as fh:
        fh.write(content.encode("utf-8"))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp,file)


with tempfile.TemporaryDirectory(prefix="pa-m11g-owned-fileview-") as td:
    base=Path(td)
    db,file=new_fixture(base,"normal")
    old=file.read_bytes()
    host,hello=start(db,bootstrap=True)
    assert hello["ok"] is True and hello["kind"]=="hello"
    assert hello["phase"]=="JSON_ACTIVE" and hello["epoch"]==0
    assert file.read_bytes()==old

    competitor,unavailable=start(db,owner=OTHER)
    assert not unavailable["ok"]
    assert unavailable["status"]=="TEST_HOST_UNAVAILABLE"
    close(competitor,expected=2)

    stage=ask(host,1,"admit",stageId="m11g-stage-0001")
    assert stage["ok"] is True and stage["pending"] is True
    assert stage["phase"]=="JSON_ACTIVE"
    expected=stage["payload"]
    assert json.loads(expected)["counter"]==1
    assert file.read_bytes()==old # Host does NOT itself write synthetic source.
    busy=ask(host,2,"admit",stageId="m11g-stage-0002")
    assert not busy["ok"] and busy["status"]=="STAGE_ALREADY_OWNED"
    wrong=ask(host,3,"verify",stageId="m11g-wrong-0003")
    assert not wrong["ok"] and wrong["status"]=="STALE_STAGE_CALLBACK"
    synthetic_write(file,expected)
    saved=ask(host,4,"verify",stageId="m11g-stage-0001")
    assert saved["ok"] is True and not saved["pending"]
    assert saved["payload"] is None
    assert json.loads(file.read_bytes())["revision"]==1
    repeated=ask(host,5,"verify",stageId="m11g-stage-0001")
    assert not repeated["ok"]
    assert repeated["status"]=="STALE_STAGE_CALLBACK"

    # Freeze is persisted in the durable fixture. A new stage cannot
    # be admitted, even though the test FileView still has valid bytes.
    frozen=ask(host,6,"freeze",expectedEpoch=0)
    assert frozen["ok"] is True
    assert frozen["phase"]=="FREEZE_REQUESTED"
    assert frozen["epoch"]==1
    denied=ask(host,7,"admit",stageId="m11g-stage-0004")
    assert denied["status"]=="LEGACY_STAGE_FROZEN"
    close(host)
    with open(file,"rb") as content:
        assert json.loads(content.read())["counter"]==1

    # Fresh owner must first enter RECOVERY_REVIEW; no default rearm.
    next_host,hello=start(db,owner=OTHER)
    assert hello["ok"] is True and hello["phase"]=="RECOVERY_REVIEW"
    assert hello["epoch"]==2
    assert not ask(next_host,1,"admit",stageId="m11g-restart-0001")["ok"]
    close(next_host)

    # A QML-reported successful save isn't accepted without matching
    # safe disk readback. A mismatch permanently fences the authority.
    db,file=new_fixture(base,"wrong-readback")
    host,hello=start(db,bootstrap=True)
    stage=ask(host,1,"admit",stageId="m11g-mismatch-0001")
    synthetic_write(file,stage["payload"].replace('"counter":1','"counter":0'))
    bad=ask(host,2,"verify",stageId="m11g-mismatch-0001")
    assert not bad["ok"] and bad["status"] in (
        "HOST_READBACK_MISMATCH","INVALID_SYNTHETIC_DOCUMENT")
    assert bad["phase"]=="RECOVERY_REVIEW"
    assert not ask(host,3,"admit",stageId="m11g-second-0003")["ok"]
    close(host)

    # Explicit FileView failure fences new requests durably.
    db,file=new_fixture(base,"failed-callback")
    host,hello=start(db,bootstrap=True)
    ask(host,1,"admit",stageId="m11g-failure-0001")
    failed=ask(host,2,"fail",stageId="m11g-failure-0001")
    assert failed["ok"] and failed["phase"]=="RECOVERY_REVIEW"
    assert failed["pending"] is True
    close(host)

    # Freeze with an in-flight stage leaves it pending and blocks new
    # stages; the earlier admitted save may settle by exact readback.
    db,file=new_fixture(base,"freeze-pending")
    host,hello=start(db,bootstrap=True)
    pending=ask(host,1,"admit",stageId="m11g-frozen-pending-01")
    freeze=ask(host,2,"freeze",expectedEpoch=0)
    assert freeze["ok"] and freeze["pending"] and freeze["epoch"]==1
    assert not ask(host,3,"admit",stageId="m11g-frozen-next-0002")["ok"]
    synthetic_write(file,pending["payload"])
    done=ask(host,4,"verify",stageId="m11g-frozen-pending-01")
    assert done["ok"] and not done["pending"]
    assert done["phase"]=="FREEZE_REQUESTED"
    close(host)

    # Crash after reservation retains pending state on disk; a later
    # owner refuses stage admission regardless of current file bytes.
    db,file=new_fixture(base,"killed-owner")
    host,hello=start(db,bootstrap=True)
    ask(host,1,"admit",stageId="m11g-crash-pending-01")
    host.kill()
    host.wait(timeout=10)
    revived,hello=start(db,owner=OTHER)
    assert hello["ok"] and hello["phase"]=="RECOVERY_REVIEW"
    assert hello["pending"] is True
    assert not ask(revived,1,"admit",stageId="m11g-crash-next-0001")["ok"]
    close(revived)

    # A changed source before any host-owned stage is never silently
    # adopted as the new baseline.
    db,file=new_fixture(base,"external-drift")
    host,hello=start(db,bootstrap=True)
    doc=json.loads(file.read_text())
    doc["revision"]=1
    doc["counter"]=1
    synthetic_write(file,json.dumps(doc,separators=(",",":"))+"\n")
    drift=ask(host,1,"admit",stageId="m11g-external-stage-1")
    assert not drift["ok"] and drift["status"]=="EXTERNAL_FIXTURE_CHANGE"
    close(host)

    # Even an otherwise valid JSON fixture with the SAME revision is a
    # changed source if its bytes were rewritten outside the owner.
    db,file=new_fixture(base,"same-revision-drift")
    host,hello=start(db,bootstrap=True)
    synthetic_write(file,file.read_text()+"\\n")
    drift=ask(host,1,"admit",stageId="m11g-same-counter-0001")
    assert not drift["ok"] and drift["status"]=="EXTERNAL_FIXTURE_CHANGE"
    close(host)

    # Host rejects live-style paths and never creates them.
    outside=base/"tasks.db"
    host,hello=start(outside,bootstrap=True)
    assert not hello["ok"] and hello["status"]=="TEST_HOST_UNAVAILABLE"
    close(host,expected=2)
    assert not outside.exists()

# Static QML invariants: real FileView and subprocess coexist ONLY in new
# isolated component; no live singleton, task paths, network or auto-start.
source=BRIDGE.read_text()
panel=HARNESS.read_text()
for marker in (
    "Scope {","Process {","FileView {","SplitParser {",
    "stdinEnabled: true","host.write(JSON.stringify(request)",
    "onSaved:","onSaveFailed:","onLoaded:","onLoadFailed:",
    "onExited:","fixtureFile.reload()","fixtureFile.setText(pendingRaw)",
    "function startTestSession()", "function incrementSynthetic()",
    "function freezeTest()","function stopTest()",
    "--bootstrap-fixture","m11e-fileview-test",
    "readonly property bool liveWriterAuthorized: false",
    "readonly property bool sqliteWriteAuthorized: false",
    "readonly property bool remoteWriteAuthorized: false",
    "readonly property bool migrationAuthorized: false"):
    assert marker in source,marker
for forbidden in ("Quickshell.dataDir","ApolloHubTodoStore",
                  "Component.onCompleted:","Timer {",
                  "function migrate(", "function activate(", "execDetached("):
    assert forbidden not in source,forbidden
assert "TaskFileViewHostBridgeM11g {" in panel
assert 'model: ["NEW TEST","EXISTING","INCREMENT","FREEZE","STOP"]' in panel
assert "TaskFileViewHostBridgeM11g" not in (ROOT/"shell.qml").read_text()
for root in ("widgets","modules","services"):
    for file in (ROOT/root).rglob("*.qml"):
        if file==BRIDGE: continue
        assert "TaskFileViewHostBridgeM11g" not in file.read_text(),file

print("M11g owned synthetic FileView host, disk readback, freeze and restart: PASS")
