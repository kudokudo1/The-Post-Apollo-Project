#!/usr/bin/env python3
"""M3d2 is a pure, unmounted dry-run contract. No write authority."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
module=(root/"scripts/finance/simple_m3d2_offline_review.mjs").read_text()
writer=(root/"scripts/finance/write_categorized_expense.mjs").read_text()
menu=(root/"widgets/FinanceW.qml").read_text()
draft=(root/"widgets/FinanceTransactionDraftPane.qml").read_text()
pane=(root/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
for forbidden in (
    "Process {", "spawn(", "exec(", "fetch(", "addTransactions(",
    "setBudgetAmount(", "updateTransaction(", "readFile(", "writeFile(",
    "createHash(", "Math.random(", "LocalStorage", "requestId:",
    "action:\"create-categorized-expense\"", "FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED",
    "categorized-expense-writes-enabled"
):
    assert forbidden not in module, forbidden
assert "inspectCategoryHandoff" in module
assert "canSave:false" in module
assert "writeAllowed:false" in module
assert 'selectedCategoryId!==proposal.categoryId' in module
assert 'requiresFreshActualPreflight:true' in module
assert 'requiresIndependentSecurityReview:true' in module
for live in (menu,draft,pane):
    assert "simple_m3d2_offline_review.mjs" not in live
    assert "write_categorized_expense.mjs" not in live
assert "if (!reviewed || categoryPreviewArmed" in draft
assert "if(!transactionDraftPane.categoryPreviewArmed)" in menu
assert 'categorized-expense-writes-enabled' in writer
print("M3d2 offline review only; M3c Save blocked; M3b writer dormant: PASS")
