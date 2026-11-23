#!/usr/bin/env python3
"""M3d0 must add no financial-write path, permission or UI Save bridge."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
source = (root/"scripts/finance/simple_category_handoff_readiness.mjs").read_text()
menu = (root/"widgets/FinanceW.qml").read_text()
draft = (root/"widgets/FinanceTransactionDraftPane.qml").read_text()
pane = (root/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
writer = (root/"scripts/finance/write_categorized_expense.mjs").read_text()
projection = (root/"scripts/finance/actual_readonly.mjs").read_text()
for forbidden in ("addTransactions(", "setBudgetAmount(", "updateTransaction(",
                  "Process {", "LocalStorage", "readFile(", "writeFile(",
                  "categorized-expense-writes-enabled", "FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED"):
    assert forbidden not in source, forbidden
assert 'canSave:false' in source
assert "requiresFreshActualPreflight:true" in source
assert "requiresIndependentSecurityReview:true" in source
assert "category-visibility-unverified" in source
assert "simple_category_handoff_readiness.mjs" not in menu + draft + pane
assert "write_categorized_expense.mjs" not in menu + draft + pane
assert "if (!reviewed || categoryPreviewArmed" in draft
assert 'if(!transactionDraftPane.categoryPreviewArmed)' in menu
assert 'categorized-expense-writes-enabled' in writer
assert 'if (group.is_income) continue;' in projection
assert 'groupRows.push({id:group.id,name:group.name});' in projection
assert 'categoryRows.push({' in projection
print("M3d0 read-only handoff staged, existing Save guard preserved: PASS")
