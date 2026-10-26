#!/usr/bin/env python3
"""M11j acceptance evidence/prod-separation audit. Only reads repository files.

The native observations were provided by the operator in chat; this test
validates recording discipline and that the audited source still matches the
scope. It CANNOT reproduce or independently certify a native run.
"""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[2]
record=json.loads((ROOT/"tests/tasks/fixtures/task_native_acceptance_m11j.json").read_text())

assert record["schemaVersion"]==1
assert record["milestone"]=="M11j"
assert record["scope"]=="ISOLATED_NATIVE_EVIDENCE_AND_PRODUCTION_PREPARATION_ONLY"
p=record["provenance"]
assert p["source"]=="OPERATOR_PROVIDED_SCREENSHOTS_AND_STATEMENTS_IN_CHAT"
assert p["observedLocalDate"]=="2026-10-26"
assert p["screenshotsRetainedInRepository"] is False
assert p["rawUserFilePathsRetained"] is False
assert p["independentFileHashVerified"] is False
assert p["telemetryExported"] is False
env=record["testedEnvironment"]
assert env["syntheticFixtureOnly"] is True
assert env["productionShellUsed"] is False
assert env["runtimeBuildStringDirectlyVerified"] is False
assert len(record["testSequence"])==5
assert [x["name"] for x in record["testSequence"]]==[
    "initial_host","first_save","second_save","freeze",
    "reopen_existing_authority"]
assert all(x["state"]=="OBSERVED_PASS" for x in record["testSequence"])
required={
    "initial_host":{"JSON_ACTIVE","FILE_READY","CONFIRMED_COUNTER_0"},
    "first_save":{"CONFIRMED_COUNTER_1","FILE_SAVED","FILE_READBACK_OK","HOST_SETTLED"},
    "second_save":{"CONFIRMED_COUNTER_2","OBSERVED_SAVE_CHAINS_2"},
    "freeze":{"FREEZE_REQUESTED","TEST_STAGE_ELIGIBLE_FALSE","CONFIRMED_COUNTER_2"},
    "reopen_existing_authority":{"RECOVERY_REVIEW","HOST_EXITED",
                                  "TEST_STAGE_ELIGIBLE_FALSE",
                                  "CONFIRMED_COUNTER_2"},
}
for result in record["testSequence"]:
    assert required[result["name"]].issubset(set(result["evidence"]))
    assert len(set(result["evidence"]))==len(result["evidence"])
boundary=record["provenanceBoundary"]
assert boundary["passingOutcome"]=="CORE_ISOLATED_NATIVE_SEQUENCE_OBSERVED"
for key in ("nativeFaultInjectionAcceptance","powerLossAcceptance",
            "sourceBytesComparedAfterRestart","allNativePathsAccepted",
            "productionWriterAccepted","productionDatabaseMigrationAccepted"):
    assert boundary[key] is False,key
for gate in ("requiredBeforeRealWriterGate","requiredBeforeSqliteCutover"):
    items=record[gate]
    assert len(items)>=5 and len(set(x["key"] for x in items))==len(items)
    assert all(x["done"] is False for x in items)
for k in ("realTaskSourceEdited","liveQuickshellProcessModifiedByThisMilestone",
          "localMachineActionPerformedByThisMilestone","productionGateInstalled",
          "sqliteWriteActivated","remoteGithubProjectWritePerformed"):
    assert record[k] is False,k
assert record["authoritativeLiveWriter"]=="JSON_FILEVIEW_ONLY"

# Recheck the actual single-writer seam, not just historical notes.
store=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
assert 'Quickshell.dataDir + "/apollo-hub-todo-v1.json"' in store
assert store.count("FileView {")==1
assert store.count("todoFile.setText(")==1
stage=store.split("function stage(result) {",1)[1].split(
    "\n    function addTask(",1)[0]
assert 'pendingDocument = result.document' in stage
assert 'storageState = "saving"' in stage
assert 'todoFile.setText(' in stage
assert stage.index("pendingDocument = result.document") < stage.index(
    "todoFile.setText(")
assert "function reloadFromDisk()" in store
assert "onLoaded:" in store and "onLoadFailed:" in store
assert "onSaved:" in store and "onSaveFailed:" in store
assert "todo.document = todo.pendingDocument;" in store
assert "TaskFileViewHostBridgeM11g" not in store
assert "TaskWriterGateMockM11f" not in store
assert "TaskSqliteSnapshotBridgeM10y" not in store
assert "TaskFileViewHostBridgeM11g" not in (ROOT/"shell.qml").read_text()

# Native isolated bridge still uses the deferred readback, stage token, host
# settlement, guarded freeze, and no-production-authority contract.
bridge=(ROOT/"services/projects/TaskFileViewHostBridgeM11g.qml").read_text()
for s in ('Qt.callLater(function()', 'fixtureFile.reload();',
          'bridge.pendingStageId === savedStageId', 'fixtureFile.setText(pendingRaw);',
          'observeNative("FILE_SAVED")','observeNative("FILE_READBACK_OK")',
          'observeNative("HOST_SETTLED")','observeNative("HOST_FROZEN")',
          'readonly property bool liveWriterAuthorized: false',
          'readonly property bool sqliteWriteAuthorized: false'):
    assert s in bridge,s
window=(ROOT/"TaskFileViewHostHarnessM11g.qml").read_text()
assert "WlrKeyboardFocus.OnDemand" in window
assert re.search(r"\bfocusable\s*:\s*true\b",window)
assert 'bridge.nativeRecent' in window
for relative in record["verifiedRepositoryDependencies"].values():
    assert (ROOT/relative).is_file(),relative

# Evidence record must never include the path/username from screenshots,
# copied JSON content, cloud identifiers, or confidence claims not obtained.
raw=json.dumps(record)
for sensitive in ("/var/home/","/home/","fixture-only.json",
                  "independent_native_certified","AUTOMATIC_SQLITE_ACTIVE"):
    assert sensitive not in raw,sensitive
print("M11j observed native evidence, unresolved gates, and JSON-only production boundaries: PASS")
