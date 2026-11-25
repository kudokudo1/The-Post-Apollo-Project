#!/usr/bin/env python3
"""FinanceW Simple M3d5b1 source-only pre-dispatch invariants."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
controller=(root/"scripts/finance/simple_m3d5b_protected_controller.mjs").read_text()
writer=(root/"scripts/finance/write_categorized_expense.mjs").read_text()
ui=(root/"widgets/FinanceW.qml").read_text()
draft=(root/"widgets/FinanceTransactionDraftPane.qml").read_text()
preview=(root/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
m3d2=(root/"scripts/finance/simple_m3d2_offline_review.mjs").read_text()

for marker in (
    'createM3d5bNonActivatedController',
    'inspectM3d5bSourceBinding',
    'inspectM3d5bSharedRecovery',
    'prepareOfflineCategorizedReview',
    'recheckOfflineCategorizedReview',
    'readTrustedPrivateFile(',
    'openTrustedDirectory(',
    'timingSafeEqual(',
    'CONFIRM CATEGORY ',
    'requestId=randomBytes(16)',
    'validateCategorizedExpenseCommand({',
    'phase="confirmed-but-dispatch-disabled"',
    'return fail("production-dispatch-hard-hold")',
    'phase="checking-confirmation"',
    'if(ticket!==epoch)return fail("controller-invalidated")',
    'return fail("unresolved-finance-operation")',
    'return fail("write-lock-present")',
    'WRITER_URL="http://127.0.0.1:5006"',
):
    assert marker in controller, marker

# Controller cannot mutate Actual or create a writer process. Every valid
# command is validated and discarded in memory. No UI call site exists.
for forbidden in (
    'spawn(', 'exec(', 'Process {', 'worker.exec', 'addTransactions(',
    '.sync()', '@actual-app/api', 'writeFile(', 'mkdir(', 'open("wx"',
    'write_categorized_expense.mjs', 'FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED',
    'categorized-expense-writes-enabled',
):
    assert forbidden not in controller, forbidden
assert 'simple_m3d5b_protected_controller' not in ui
assert 'simple_m3d5b_protected_controller' not in draft
assert 'simple_m3d5b_protected_controller' not in preview
assert 'write_categorized_expense.mjs' not in ui
assert 'write_categorized_expense.mjs' not in draft
assert 'write_categorized_expense.mjs' not in preview
assert 'if (!reviewed || categoryPreviewArmed' in draft
assert 'if(!transactionDraftPane.categoryPreviewArmed)' in ui
assert 'canSave:false' in m3d2 and 'writeAllowed:false' in m3d2
assert 'FINANCEW_CATEGORIZED_EXPENSE_RESULT ' in writer
assert 'await recordAttempt(cmd);' in (root/"scripts/finance/categorized_expense_guard.mjs").read_text()
print("FinanceW M3d5b1 non-activated confirmation/recovery controller: HOLD PASS")
