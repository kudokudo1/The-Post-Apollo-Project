#!/usr/bin/env python3
"""M11e source-level QML boundary and private synthetic fixture tests.

DOES NOT launch Quickshell or modify live TASKS. Native callback behavior
requires explicit on-device acceptance after review/authorization.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
GATE=ROOT/"services/projects/TaskFileViewGateM11e.qml"
POLICY=ROOT/"services/projects/TaskFileViewGatePolicyM11e.js"
PANEL=ROOT/"TaskFileViewGateHarnessM11e.qml"
GENERATOR=ROOT/"tests/tasks/fixtures/m11e_fileview_fixture.py"

qml=GATE.read_text()
panel=PANEL.read_text()
policy=POLICY.read_text()
shell=(ROOT/"shell.qml").read_text()
for needed in (
    "import Quickshell.Io",
    'import "TaskFileViewGatePolicyM11e.js" as GatePolicy',
    "function attachTestFile()", "function stageSyntheticIncrement()",
    "function freezeTestAdmission()", "function reloadTestFile()",
    "if (attached || gateState.phase !== \"UNARMED\") return false;",
    "m11e-fileview-test", "fixture-only",
    "gate.attached ? gate.activePath : \"\"",
    "FileView {", "atomicWrites: true", "blockWrites: false",
    "watchChanges: false", "printErrors: false",
    "GatePolicy.requestStage(gateState)",
    "GatePolicy.onSaved(gate.gateState)",
    "GatePolicy.onSaveFailed(gate.gateState)",
    "GatePolicy.onLoaded(gate.gateState,",
    "GatePolicy.onLoadFailed(gate.gateState)",
    "if (gate.gateState.phase === \"VERIFYING\")",
    "fixtureFile.reload()", "fixtureFile.setText(plan.raw)",
    "readonly property bool liveWriterAuthorized: false",
    "readonly property bool sqliteWriterAuthorized: false",
    "readonly property bool remoteWriteAuthorized: false",
    "readonly property bool productionActivation: false"
):
    assert needed in qml,needed
for forbidden in ("ApolloHubTodoStore", "Quickshell.dataDir",
                  "SqliteRecordsV2","TaskSqliteHandoffHost",
                  "Process {","execDetached(", "Component.onCompleted:",
                  "Timer {","watchChanges: true"):
    assert forbidden not in qml,forbidden
assert qml.count("FileView {")==1
assert qml.count("fixtureFile.setText(plan.raw)")==1
assert qml.count("onSaved:")==1 and qml.count("onSaveFailed:")==1
assert qml.count("onLoaded:")==1 and qml.count("onLoadFailed:")==1

for needed in ("TaskFileViewGateM11e {","PanelWindow {",
               'model: ["ATTACH","INCREMENT","FREEZE","RELOAD"]',
               "gate.stageSyntheticIncrement()","gate.freezeTestAdmission()",
               "gate.reloadTestFile()", "gate.attachTestFile()"):
    assert needed in panel,needed
for forbidden in ("ApolloHubTodoStore","Quickshell.dataDir","FileView {",
                  "Process {","onCompleted:","Qt.openUrlExternally",
                  "execDetached("):
    assert forbidden not in panel,forbidden
assert "TaskFileViewGateHarnessM11e" not in shell
assert "TaskFileViewGateM11e" not in shell
assert "TaskFileViewGatePolicyM11e" not in shell
# No existing QML widget or live project service may mount either test type.
for root in ("widgets","modules","services"):
    for f in (ROOT/root).rglob("*.qml"):
        if f==GATE: continue
        source=f.read_text()
        assert "TaskFileViewGateM11e" not in source,f
        assert "TaskFileViewGateHarnessM11e" not in source,f

for needed in ("function onSaved(s)","function onSaveFailed(s)",
               "function onLoaded(s, raw)","function requestStage(s)",
               "function requestFreeze(s)","function requestReload(s)",
               "POST_SAVE_READBACK_MISMATCH",
               "RELOAD_SOURCE_DRIFT","RECOVERY_REVIEW"):
    assert needed in policy,needed
assert "M11E_SYNTHETIC_ONLY" in policy
assert "apollo-hub-todo-v1.json" not in policy
assert "fetch(" not in policy and "setText(" not in policy

def generate(file):
    return subprocess.run([sys.executable,"-B","-I",str(GENERATOR),
                           "--file",str(file)],capture_output=True,text=True,
                          timeout=15)

with tempfile.TemporaryDirectory(prefix="pa-m11e-fileview-") as td:
    base=Path(td)
    folder=base/"m11e-fileview-test"
    folder.mkdir(mode=0o700)
    file=folder/"fixture-only.json"
    first=generate(file)
    assert first.returncode==0,(first.stdout,first.stderr)
    value=json.loads(file.read_text())
    assert value=={"fixture":"M11E_SYNTHETIC_ONLY","revision":0,
                   "counter":0,"marker":"sample"}
    assert (file.stat().st_mode & 0o777)==0o600
    second=generate(file)
    assert second.returncode!=0
    assert json.loads(file.read_text())==value
    wrong=base/"apollo-hub-todo-v1.json"
    assert generate(wrong).returncode!=0
    assert not wrong.exists()
    absent=base/"missing"/"m11e-fileview-test"/"fixture-only.json"
    assert generate(absent).returncode!=0
    assert not absent.parent.exists()
    insecure=base/"insecure"/"m11e-fileview-test"
    insecure.mkdir(mode=0o755,parents=True)
    denied=insecure/"fixture-only.json"
    assert generate(denied).returncode!=0
    assert not denied.exists()
    linked=base/"symlinked"/"m11e-fileview-test"
    linked.mkdir(mode=0o700,parents=True)
    target=linked/"fixture-only.json"
    target.symlink_to(file)
    assert generate(target).returncode!=0
    assert target.is_symlink()
    assert json.loads(file.read_text())==value

print("M11e unmounted FileView QML boundary and disposable fixture tests: PASS")
