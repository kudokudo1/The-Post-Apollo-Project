#!/usr/bin/env python3
"""M11i source-only isolated Quickshell callback evidence surface test.

This is NOT a native QML launch. Operator permission is required before
using the standalone FileView harness with a real disposable directory.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
RECORDER=ROOT/"services/projects/TaskFileViewNativeEvidenceM11i.js"
BRIDGE=ROOT/"services/projects/TaskFileViewHostBridgeM11g.qml"
WINDOW=ROOT/"TaskFileViewHostHarnessM11g.qml"
script=RECORDER.read_text()
bridge=BRIDGE.read_text()
panel=WINDOW.read_text()

assert script.startswith(".pragma library")
assert "OBSERVATION_ONLY_NOT_NATIVE_ACCEPTED" in script
assert "LIMIT=32" in script
assert "function append(" in script
assert "function summarize(" in script
assert "function recent(" in script
assert "current.events.slice()" in script
for forbidden in ("FileView {", "Quickshell.", "Process {", "setText(",
                  "os.", "fetch(", "Qt.openUrl", "ApolloHubTodoStore",
                  "console.log(", "taskDescription", "fixturePath", "writerId",
                  "pendingRaw", "JSON.stringify(current)"):
    assert forbidden not in script, forbidden

assert 'import "TaskFileViewNativeEvidenceM11i.js" as NativeEvidence' in bridge
assert "property var nativeEvidence: NativeEvidence.empty()" in bridge
assert "readonly property var nativeSummary:" in bridge
assert "readonly property string nativeRecent:" in bridge
assert "NativeEvidence.append(nativeEvidence, kind, phase)" in bridge
assert bridge.count('observeNative("HOST_ADMIT")')==1
assert bridge.count('observeNative("HOST_SETTLED")')==1
assert bridge.count('observeNative("FILE_SAVED")')==1
assert bridge.count('observeNative("FILE_READBACK_OK")')==1
assert bridge.count('observeNative("HOST_FROZEN")')==1
assert bridge.count('observeNative("HOST_EXIT")')==1
assert bridge.count('observeNative("RECOVERY_REVIEW")')==1
assert "TaskFileViewNativeEvidenceM11i" not in (ROOT/"shell.qml").read_text()
for parent in ("widgets","modules","services"):
    for filename in (ROOT/parent).rglob("*.qml"):
        if filename==BRIDGE:
            continue
        text=filename.read_text()
        assert "TaskFileViewNativeEvidenceM11i" not in text,filename
        assert "TaskFileViewHostHarnessM11g" not in text,filename

assert 'bridge.nativeSummary.label' in panel
assert 'bridge.nativeSummary.saveChains' in panel
assert 'bridge.nativeSummary.recoveryObserved' in panel
assert 'bridge.nativeRecent' in panel
assert "PRODUCTION AUTHORITY // FALSE // NO MIGRATION" in panel
assert "TaskFileViewHostBridgeM11g {" in panel
assert 'model: ["NEW TEST","EXISTING","INCREMENT","FREEZE","STOP"]' in panel
for forbidden in ("FileView {", "Process {", "Quickshell.dataDir",
                  "ApolloHubTodoStore", "Component.onCompleted:",
                  "TaskWriterGateMockM11f"):
    assert forbidden not in panel,forbidden

# Read-only data model. No private payloads in records or implicit file writes.
source=script[script.index("function append("):script.index("function summarize(")]
assert "updated.push({seq:" in source
assert "tag:tag,phase:safePhase" in source
assert "path:" not in source
assert re.search(r"\bwrite\s*\(",source) is None
print("M11i unmounted native callback visibility, privacy and production exclusion: PASS")
