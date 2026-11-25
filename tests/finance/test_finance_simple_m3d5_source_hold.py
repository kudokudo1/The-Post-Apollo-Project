#!/usr/bin/env python3
"""FinanceW M3d5a source-only stage; no activation or financial mutation."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
draft=(root/"widgets/FinanceTransactionDraftPane.qml").read_text()
window=(root/"widgets/FinanceW.qml").read_text()
qml=(root/"services/finance/FinanceCategorizedSaveReview.js").read_text()
module=(root/"scripts/finance/simple_m3d2_offline_review.mjs").read_text()
m3d0=(root/"scripts/finance/simple_category_handoff_readiness.mjs").read_text()
for token in (
    'FinanceCategorizedSaveReview.js',
    'property var saveReview: null',
    'function reviewForSave()',
    'SaveReview.prepareOfflineCategorizedReview(input)',
    'SaveReview.recheckOfflineCategorizedReview({',
    'saveReview=result;',
    'CHECK CATEGORY SAVE READINESS',
    'REVIEW MATCHED // CATEGORY SAVE DISABLED',
    'PROTECTED CATEGORY SAVE // HOLD // NO WRITE PERMIT',
):
    assert token in pane, token
for token in (
    'function prepareOfflineCategorizedReview(args)',
    'function recheckOfflineCategorizedReview(args)',
    'canSave:false', 'writeAllowed:false',
    'requiresFreshActualPreflight:true',
    'requiresIndependentSecurityReview:true',
    'review-only-no-write-authority',
):
    assert token in qml, token
assert "export function prepareOfflineCategorizedReview" in module
assert "export function inspectCategoryHandoff" in m3d0
for code in (pane,qml):
    for forbidden in (
        'Quickshell.Io','Process {','worker.exec(', 'addTransactions(',
        'write_categorized_expense.mjs','FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED'
    ):
        assert forbidden not in code, forbidden
assert 'if (!reviewed || categoryPreviewArmed' in draft
assert 'if(!transactionDraftPane.categoryPreviewArmed)' in window
assert 'FinanceCategorizedExpenseWriteService' not in window
assert 'write_categorized_expense.mjs' not in window
assert 'write_categorized_expense.mjs' not in draft
assert 'saveRequested(' not in pane
assert 'categoryPreviewArmed = false' not in pane
print("M3d5a category Save readiness QML review isolated; production HOLD: PASS")
