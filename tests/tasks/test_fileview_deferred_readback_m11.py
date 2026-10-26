#!/usr/bin/env python3
"""Regression for Quickshell v0.2.1 FileView post-save callback timing.

Quickshell's FileView emits saved() before clearing its liveOperation.
The subsequent reload() must be deferred to the next QML event turn,
not invoked synchronously inside onSaved. Source-level only; native
acceptance still requires the user's separately launched test window.
"""
from pathlib import Path
import re

root=Path(__file__).resolve().parents[2]
targets=[
    (root/"services/projects/TaskFileViewHostBridgeM11g.qml",
     "bridge.fileState === \"VERIFYING\"",
     "bridge.pendingStageId === savedStageId"),
    (root/"services/projects/TaskFileViewGateM11e.qml",
     "gate.gateState.phase === \"VERIFYING\"",
     "gate.gateState.activeToken === savedToken"),
]

for file, phase_guard, token_guard in targets:
    source=file.read_text()
    assert source.count("FileView {")==1,file
    assert source.count("onSaved:")==1,file
    assert source.count("onSaveFailed:")==1,file
    section=source.split("onSaved:",1)[1].split("onSaveFailed:",1)[0]
    assert "Qt.callLater(function()" in section,file
    assert phase_guard in section,file
    assert token_guard in section,file
    assert "fixtureFile.reload();" in section,file
    assert section.index("Qt.callLater(function()") < section.index("fixtureFile.reload();"),file
    assert re.search(r"Qt\.callLater\(function\(\)\s*\{[\s\S]*?fixtureFile\.reload\(\);",section),file
    assert "Component.onCompleted:" not in source,file
    assert "WlrKeyboardFocus.Exclusive" not in source,file
    assert "Quickshell.dataDir" not in source,file
    assert "ApolloHubTodoStore" not in source,file

host_source=(root/"services/projects/TaskFileViewHostBridgeM11g.qml").read_text()
assert "bridge.observeNative(\"FILE_SAVED\")" in host_source
assert "bridge.observeNative(\"FILE_READBACK_OK\")" in host_source
assert "bridge.observeNative(\"HOST_SETTLED\")" in host_source
assert "fixtureFile.setText(pendingRaw);" in host_source
assert "TaskFileViewHostBridgeM11g" not in (root/"shell.qml").read_text()
print("M11 FileView deferred readback callback and stale-stage fences: PASS")
