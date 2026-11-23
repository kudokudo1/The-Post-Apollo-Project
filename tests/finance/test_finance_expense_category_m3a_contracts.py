#!/usr/bin/env python3
"""FinanceW Simple M3a strict source-only category preview / no-write contract."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
policy=(root/"services/finance/FinanceExpenseCategoryPreview.js").read_text()
menu=(root/"widgets/FinanceW.qml").read_text()
draft=(root/"widgets/FinanceTransactionDraftPane.qml").read_text()
guard=(root/"scripts/finance/transaction_guard.mjs").read_text()

# M3c mounts M3a once but never connects the categorized-expense writer.
# Existing transaction Save still has NO categoryId.
assert menu.count("FinanceExpenseCategoryPreviewPane {") == 1
assert "FinanceExpenseCategoryPreviewPane {" not in draft
assert 'objectName: "expenseCategoryPreviewPane"' in pane
assert 'objectName: "expenseCategoryPicker"' in pane
assert 'objectName: "expenseCategoryPreviewAction"' in pane
assert 'objectName: "expenseCategorySummary"' in pane
assert 'onSnapshotChanged: clear()' in pane
assert 'onCandidateChanged: invalidate()' in pane
assert 'onSelectedCategoryIdChanged: invalidate()' in pane
assert 'function begin(draft)' in pane
assert 'function calculate()' in pane
assert 'function clear()' in pane
assert 'gate.reason!=="SELECT AN EXPENSE ENVELOPE"' in pane
assert 'text: "NOT CONNECTED TO TRANSACTION SAVE"' in pane
assert 'text: "ESTIMATE ONLY // ACTUAL RECALCULATES // NOT SAVED"' in pane

for label in (
    "function previewExpenseCategory(snapshot,candidate,categoryId)",
    "snapshot.schemaVersion!==1",
    'snapshot.source!=="actual-budget"',
    "snapshot.readOnly!==true",
    "snapshot.sourceKey",
    "candidate.sourceKey!==snapshot.sourceKey",
    "candidate.month!==snapshot.month",
    'candidate.action!=="create"',
    'candidate.direction!=="expense"',
    "candidate.amountCents>=0",
    "matches.length!==1",
    "categoryRows.length!==1",
    "groups.length!==1",
    "category.availableCents+candidate.amountCents",
    "category.spentCents+candidate.amountCents",
    "toBudgetAfterCents:null",
    "ok:true,readOnly:true,writeAllowed:false,savesToActual:false",
):
    assert label in policy,label

for source in (pane,policy):
    for forbidden in (
        "Process {","LocalStorage","Settings {","writeFile(","fetch(",
        "api.","setBudgetAmount(","addTransactions(","updateTransaction(",
        "financeWrite.submit(","saveRequested","onSaveRequested",
        "FINANCEW_TRANSACTION_WRITES_APPROVED","openUrlExternally"
    ):
        assert forbidden not in source,forbidden

# The existing transaction editor still does not pretend a category chosen
# in a detached proposal was included in the persistent save command.
assert "categoryId" not in draft
assert '"categoryId"' not in guard
assert 'category: ' not in guard
assert "addTransactions(cmd.accountId" in guard
assert 'saveRequested(payload);' in draft
assert 'financeWrite.submit(payload);' in menu
print("FinanceW Simple M3a/M3c mounted expense preview/no-writer contracts: PASS")
