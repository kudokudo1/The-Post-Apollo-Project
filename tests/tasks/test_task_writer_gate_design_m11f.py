#!/usr/bin/env python3
"""M11f production stage-gate preflight; static audit ONLY, no desktop writes.

Do not mistake the pure JS mock's host-receipt booleans for an OS lock,
real FileView callback provenance or authority to change production TASKS.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
manifest=json.loads((ROOT/"tests/tasks/fixtures/task_writer_gate_review_m11f.json").read_text())
store=(ROOT/manifest["liveStore"]).read_text()
model=(ROOT/"services/projects/TaskWriterGateMockM11f.js").read_text()
m11e=(ROOT/"services/projects/TaskFileViewGateM11e.qml").read_text()

assert manifest["version"]==1
assert manifest["status"]=="UNMOUNTED_MOCK_NO_ACTIVATION"
assert manifest["liveStore"]=="services/hub/ApolloHubTodoStore.qml"
assert len(manifest["futurePatchSequence"])==10
assert len(manifest["unverifiedGates"])==7
assert manifest["automaticLiveWritesAuthorized"] is False
assert manifest["productionSourcePatchAuthorized"] is False
assert manifest["migrationAuthorized"] is False
assert manifest["sqliteActivationAuthorized"] is False
assert manifest["githubRemoteOperationsAuthorized"] is False
assert manifest["writerEntry"] in store
assert store.count(manifest["fileViewWrite"])==1

# The real source still exposes the original single-writer callback seams,
# and the temporary mock cannot be imported from any existing live surface.
for callback in manifest["observedCallbacks"]:
    assert store.count(callback)==1,callback
assert "readonly property var snapshot:" in store
assert "TodoPolicy.view(storageState, document, errorCode)" in store
assert 'Quickshell.dataDir + "/apollo-hub-todo-v1.json"' in store
assert "watchChanges: false" in store
assert "atomicWrites: true" in store
assert "blockWrites: false" in store
assert "onSaved:" in store and "onSaveFailed:" in store
assert "todo.document = todo.pendingDocument;" in store
assert "todo.pendingDocument = null;" in store
assert "FileView {" in store
assert "TaskWriterGateMockM11f" not in store
assert "TaskFileViewGateM11e" not in store

for relative in manifest["mustRemainUnmodified"]:
    text=(ROOT/relative).read_text()
    assert "TaskWriterGateMockM11f" not in text,relative
    assert "TaskFileViewGateM11e" not in text,relative
for base in ("widgets","services","modules"):
    for file in (ROOT/base).rglob("*.qml"):
        text=file.read_text()
        assert "TaskWriterGateMockM11f" not in text,file

# The mocked protocol must stay free of disk/network/process primitives.
assert model.startswith(".pragma library")
for forbidden in ("FileView {","Process {","Quickshell.","ApolloHubTodoStore",
                  "fetch(","XMLHttpRequest","require(","fs.","setText(",
                  "execDetached(","Qt.openUrlExternally(",
                  "ApolloHubTodoPolicy", "tasks.db"):
    assert forbidden not in model,forbidden
for name in ("state","reviewMockOwner","proposeStage","acceptReservation",
             "onSaved","verifyReadback","acceptSettle","requestFreeze",
             "acceptFreeze","failedCallback","restart"):
    assert re.search(r"\bfunction\s+"+name+r"\s*\(",model),name
for phase in manifest["mockStates"]:
    assert '"'+phase+'"' in model,phase
for property_name in ("productionWriteAuthorized:false",
                      "sqliteWriteAuthorized:false",
                      "migrationAuthorized:false",
                      "remoteWriteAuthorized:false"):
    assert property_name in model,property_name
assert "MOCK_READY" in model and "RECOVERY_REVIEW" in model
assert "fixtureFile.setText(plan.raw)" in m11e
assert "TaskWriterGateMockM11f" not in m11e

# Explicitly fail review if the candidate tries to modify the actual
# TASKS writer instead of providing only an unmounted rehearsal contract.
print("M11f future production gate integration seams and non-activation audit: PASS")
