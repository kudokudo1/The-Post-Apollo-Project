#!/usr/bin/env python3
"""D12d allocation save confirmation and permission boundary contracts."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceCategoryAllocationPane.qml").read_text()
service=(root/"services/finance/FinanceAllocationWriteService.qml").read_text()
menu=(root/"widgets/FinanceW.qml").read_text()
writer=(root/"scripts/finance/write_allocation.mjs").read_text()
for item in (
    "signal saveRequested(var payload)",
    "property bool approvalArmed: false",
    "property bool submitted: false",
    "readonly property bool proposalEligible:",
    "&& proposal.allocationChangeCents !== 0",
    "&& !proposal.exceedsUnallocatedFunds",
    "&& !proposal.categoryRemainsOverspent",
    "proposal.sourceKey === snapshot.sourceKey",
    "proposal.originalBudgetedCents === category.budgetedCents",
    "proposal.originalAvailableCents === category.availableCents",
    "proposal.toBudgetBeforeCents === snapshot.toBudgetCents",
    "function requestSave()",
    "if (!open || !proposalEligible || !approvalArmed",
    "submitted = true;",
    'action:"set-amount",requestId:requestId,',
    "onSnapshotChanged: clear()",
    "onTargetTextChanged:",
    "approvalArmed = false;",
    "label: allocation.submitted ? \"REQUEST SUBMITTED\"",
    '"CONFIRM SAVE" : "ARM SAVE"',
    "onLeftClicked: {",
    "allocation.requestSave();",
    "saveRequested({",
):
    assert item in pane,item
assert pane.count('ActionButton {')==3
assert pane.count("trackLabelGlowLocally: true")==3
assert "onLeftClicked: allocation.requestSave()" not in pane
assert 'signal saved()' in service
assert 'if (state === "pending" || state === "uncertain"' in service
assert 'if (bridge.inputFrame)' in service
assert 'stdinEnabled: true' in service
assert 'Quickshell.shellPath("scripts/finance/write_allocation.mjs")' in service
assert "FINANCEW_ALLOCATION_RESULT" in service
assert 'bridge.state="uncertain";' in service
assert 'bridge.message="UNCERTAIN // CHECK ACTUAL AND JOURNAL. DO NOT RETRY.";' in service
assert 'FINANCEW_ALLOCATION_RESULT committed' not in pane
assert 'FINANCEW_ALLOCATION_RESULT' not in menu
assert 'FinanceServices.FinanceAllocationWriteService {' in menu
assert 'id: financeAllocationWrite' in menu
assert 'financeAllocationWrite.submit(payload);' in menu
assert 'writeState: financeAllocationWrite.state' in menu
assert 'writeMessage: financeAllocationWrite.message' in menu
assert 'onSaveRequested: function(payload)' in menu
assert 'onSaved: {' in menu
assert 'allocationPreviewPane.clear();' in menu
assert 'financeBudget.refresh();' in menu
assert 'financeAllocationWrite.state !== "uncertain"' in menu
assert 'financeAllocationWrite.state !== "pending"' in menu
for forbidden in ("Process {","LocalStorage","Settings {","fetch(",
                  "writeFile(","setBudgetAmount(","api.","exec(",
                  "allocation-writes-enabled","ACTUAL_PASSWORD"):
    assert forbidden not in pane,forbidden
for forbidden in ("allocation-writes-enabled","FINANCEW_ALLOCATION_WRITES_APPROVED",
                  "writeFile(","Qt.openUrlExternally","LocalStorage","Settings {"):
    assert forbidden not in service,forbidden
assert 'privateFile(join(config,"allocation-writes-enabled"))' in writer
assert 'FINANCEW_ALLOCATION_WRITES_APPROVED' in writer
assert '"operations"' in writer
assert '".write-lock"' in writer
print("FinanceW D12d separately locked confirmation UI contracts: PASS")
