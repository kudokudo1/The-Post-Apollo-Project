#!/usr/bin/env python3
"""M11k source-only contract check. Never reads live task data."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
record = json.loads((root / "tests/tasks/fixtures/task_production_gate_review_m11k.json").read_text())
store = (root / "services/hub/ApolloHubTodoStore.qml").read_text()
policy = (root / "services/hub/ApolloHubTodoPolicy.js").read_text()
document = (root / "docs/tasks-production-writer-gate-m11k.md").read_text()

assert record["milestone"] == "M11k"
assert record["classification"] == "PROPOSED_PRODUCTION_JSON_GATE_CONTRACT_ONLY"
assert record["existingBehavior"]["activeWriter"] == "JSON_FILEVIEW_ONLY"
assert record["supportedSourceVersions"] == [1, 2, 3]
assert all(value is False for value in record["activation"].values())
assert all(value is False for key, value in record["approval"].items()
           if key != "m11kContractReviewRequested")
assert record["sourceSnapshotPolicy"]["lastConfirmedDocumentPreservedOnFailure"]
assert len(record["orderedProposedSteps"]) == 11
assert len(record["requiredFailureCases"]) >= 14

assert 'Quickshell.dataDir + "/apollo-hub-todo-v1.json"' in store
assert store.count("FileView {") == 1
assert store.count("todoFile.setText(") == 1
assert "function stage(result) {" in store
assert "onSaved:" in store and "onSaveFailed:" in store
assert "onLoaded:" in store and "onLoadFailed:" in store
assert "TaskFileViewHostBridgeM11g" not in store
assert "TaskSqliteSnapshotBridgeM10y" not in store

for state in record["existingBehavior"]["snapshotStates"]:
    assert '"' + state + '"' in policy
assert "function view(storageState, doc, issue)" in policy
for heading in ("IMPLEMENTATION", "HOW TO USE", "VERIFY", "WATCH OUT FOR",
                "CHECKLIST", "NEXT", "DECISIONS"):
    assert "## " + heading in document
assert "PROPOSAL ONLY" in document
print("M11k review-only gate contract: PASS")
