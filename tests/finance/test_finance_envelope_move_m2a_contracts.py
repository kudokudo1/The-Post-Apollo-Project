#!/usr/bin/env python3
"""FinanceW Simple M2a/M2c envelope move preview authority contract."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceEnvelopeMovePreviewPane.qml").read_text()
rules=(root/"services/finance/FinanceEnvelopeMovePlan.js").read_text()
main=(root/"widgets/FinanceW.qml").read_text()
writer=(root/"scripts/finance/write_allocation.mjs").read_text()

# M2c mounts the same M2a view-only preview once, still without a writer.
assert main.count("FinanceEnvelopeMovePreviewPane {") == 1
assert 'import "../services/finance/FinanceEnvelopeMovePlan.js" as MoveRules' in pane
assert "MoveRules.previewEnvelopeMove(snapshot,fromCategoryId," in pane
assert 'objectName: "envelopeMovePreviewPane"' in pane
assert 'objectName: "moveFromPicker"' in pane
assert 'objectName: "moveToPicker"' in pane
assert 'objectName: "movePreviewAction"' in pane
assert 'objectName: "movePreviewSummary"' in pane
assert 'function calculate()' in pane
assert 'function clear()' in pane
assert "onSnapshotChanged: clear()" in pane
assert "onFromCategoryIdChanged: invalidatePreview()" in pane
assert "onToCategoryIdChanged: invalidatePreview()" in pane
assert "onAmountTextChanged: invalidatePreview()" in pane
assert "PREVIEW ONLY // NO CHANGES SAVED // WRITER NOT CONNECTED" in pane
assert "NOT A BANK TRANSFER" in pane
assert "signal saveRequested" not in pane
assert "signal moveRequested" not in pane
assert "onSaveRequested" not in pane
assert "onMoveRequested" not in pane

# Pure two-sided arithmetic and stable month/source binding. At most one
# matching category per side; source cannot be overdrawn by a preview.
for marker in (
    "function previewEnvelopeMove(snapshot,fromId,toId,amountText)",
    "snapshot.schemaVersion!==1",
    'snapshot.source!=="actual-budget"',
    "snapshot.readOnly!==true",
    "snapshot.sourceKey",
    "snapshot.month",
    "fromRows.length!==1 || toRows.length!==1",
    "if(fromId===toId)",
    "if(cents>from.availableCents)",
    "if(cents>from.budgetedCents)",
    "from.budgetedCents-cents",
    "to.budgetedCents+cents",
    "from.availableCents-cents",
    "to.availableCents+cents",
    "toBudgetAfterCents:snapshot.toBudgetCents",
    "savesToActual:false,requiresAtomicWriter:true",
    "destinationRemainsOverspent:toAvailableAfter<0",
):
    assert marker in rules,marker

for code in (pane,rules):
    for forbidden in (
        "Process {","LocalStorage","Settings {","writeFile(", "fetch(",
        "Qt.openUrlExternally", "downloadBudget(", "setBudgetAmount(",
        "financeAllocationWrite.submit(", "financeWrite.submit(",
        "FINANCEW_ALLOCATION_WRITES_APPROVED", "createTransfer(",
        "sendPayment(", "api.sync(", "api."
    ):
        assert forbidden not in code,forbidden

# Existing allocation writer still implements a SINGLE category command
# and must never be invoked twice as an unsafe substitute for atomic move.
assert 'action:"allocation:set-amount"' in writer
assert 'executeAllocation({' in writer
assert 'setBudgetAmount(' not in pane
print("FinanceW Simple M2a/M2c mounted preview/no-writer contracts: PASS")
