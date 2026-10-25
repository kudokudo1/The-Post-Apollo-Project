#!/usr/bin/env python3
"""M10z source/runtime-host test contract. Does NOT launch Quickshell.

Exercises real synthetic fixture initialization + Python subprocess reload
and verifies the separate QML panel is not imported by production.
Callback interleavings are exercised in companion Node source-policy tests.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
BRIDGE=ROOT/"services/projects/TaskSqliteSnapshotBridgeM10y.qml"
LIFECYCLE=ROOT/"services/projects/TaskSqliteSnapshotLifecycleM10z.js"
HARNESS=ROOT/"TaskSqliteSnapshotHarnessM10z.qml"
GENERATOR=ROOT/"tests/tasks/fixtures/m10z_snapshot_fixture.py"
PROBE=ROOT/"services/projects/TaskSqliteSnapshotProbeM10y.py"
HOST=ROOT/"widgets/TasksW.qml"
SHELL=ROOT/"shell.qml"

bridge=BRIDGE.read_text()
lifecycle=LIFECYCLE.read_text()
harness=HARNESS.read_text()
host=HOST.read_text()
shell=SHELL.read_text()

for required in (
    'import "TaskSqliteSnapshotLifecycleM10z.js" as Lifecycle',
    "function cancelSnapshot()", "function clearSnapshot()",
    "Lifecycle.outcome(flight)", "Lifecycle.settle(flight)",
    "Lifecycle.cancel(flight)", "Lifecycle.onExit(",
    "Lifecycle.onStreamFinished(", "if (busy || worker.running) return false;",
    "worker.running = false;", 'status = "CANCEL_REQUESTED"',
    'status = "CANCELLED"', 'if (joined.kind !== "response")',
    'snapshot = safeView;', 'safeView.writable = false;',
    "function requestSnapshot()",
    'Quickshell.shellPath("services/projects/TaskSqliteSnapshotProbeM10y.py")',
):
    assert required in bridge,required
for required in ("function begin(old)", "function cancel(old)", "function outcome(old)",
                 "function onExit(old, code)", "function onStreamFinished(old, text)",
                 "function settle(old)", "if (old.cancelled)",
                 'return {kind:"waiting"}'):
    assert required in lifecycle,required

for required in (
    'import "./services/projects"',
    "TaskSqliteSnapshotBridgeM10y {",
    "PanelWindow {",
    'model: ["READ","CANCEL","CLEAR"]',
    "snapshotProbe.requestSnapshot()",
    "snapshotProbe.cancelSnapshot()",
    "snapshotProbe.clearSnapshot()",
    "snapshotProbe.snapshot.writable",
):
    assert required in harness,required
for forbidden in ("FileView {","Process {","ApolloHubTodoStore",
                  "GitHubProjectsService", "onCompleted:",
                  "Quickshell.execDetached(","Qt.openUrlExternally("):
    assert forbidden not in harness,forbidden
assert "TaskSqliteSnapshotHarnessM10z" not in shell
assert "TaskSqliteSnapshotHarnessM10z" not in host
assert "TaskSqliteSnapshotBridgeM10y" not in shell
assert "TaskSqliteSnapshotBridgeM10y" not in host
assert "TaskSqliteSnapshotLifecycleM10z" not in shell
assert "TaskSqliteSnapshotLifecycleM10z" not in host

with tempfile.TemporaryDirectory(prefix="pa-m10z-runtime-host-") as temp:
    directory=Path(temp)/"m10y-snapshot-test"
    directory.mkdir(mode=0o700)
    db=directory/"tasks.db"
    absent=subprocess.run(
        [sys.executable,"-B","-I",str(PROBE),"--db",str(db)],
        capture_output=True,text=True,check=True,timeout=15)
    assert json.loads(absent.stdout)["status"]=="ABSENT"
    assert not db.exists()

    generated=subprocess.run(
        [sys.executable,"-B","-I",str(GENERATOR),"--db",str(db)],
        capture_output=True,text=True,check=True,timeout=15)
    assert "synthetic fixture" in generated.stdout
    assert db.exists()
    assert (db.stat().st_mode & 0o777)==0o600
    saved=None
    for i in range(3):
        response=subprocess.run(
            [sys.executable,"-B","-I",str(PROBE),"--db",str(db)],
            capture_output=True,text=True,check=True,timeout=15)
        content=json.loads(response.stdout)
        assert content["status"]=="READY"
        assert content["writeReady"] is False
        assert content["remoteWriteAuthorized"] is False
        assert len(content["document"]["tasks"])==2
        assert content["document"]["tasks"][0]["title"]=="M10z disposable example task"
        if saved is not None: assert content==saved
        saved=content
    again=subprocess.run(
        [sys.executable,"-B","-I",str(GENERATOR),"--db",str(db)],
        capture_output=True,text=True,timeout=15)
    assert again.returncode != 0, "Never overwrite a preexisting fixture"

    # A bogus unrelated tasks.db path must not be created by the generator.
    unrelated=Path(temp)/"tasks.db"
    rejected=subprocess.run(
        [sys.executable,"-B","-I",str(GENERATOR),"--db",str(unrelated)],
        capture_output=True,text=True,timeout=15)
    assert rejected.returncode!=0
    assert not unrelated.exists()
print("M10z disposable fixture and subprocess reload plus QML no-mount contract: PASS")
