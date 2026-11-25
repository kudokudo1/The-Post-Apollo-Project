#!/usr/bin/env python3
"""FinanceW M3d5b4 is a disposable confirmed-ID fixture, NEVER live transport."""
from pathlib import Path
r=Path(__file__).resolve().parents[2]
src=(r/"scripts/finance/simple_m3d5b4_disposable_confirmation.mjs").read_text()
ui=(r/"widgets/FinanceW.qml").read_text()
draft=(r/"widgets/FinanceTransactionDraftPane.qml").read_text()
category=(r/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
m3b=(r/"scripts/finance/write_categorized_expense.mjs").read_text()
m3d5b1=(r/"scripts/finance/simple_m3d5b_protected_controller.mjs").read_text()
m3d5b3=(r/"scripts/finance/simple_m3d5b3_bridge_contract.mjs").read_text()
for required in [
    'createM3d5b4DisposableCustodian',
    'inspectM3d5b4DisposableReceipt',
    'FINANCEW_DISPOSABLE_TEST==="yes"',
    'process.env.HOME===sandboxRoot',
    'testRootPattern.test(basename(sandboxRoot))',
    'openTrustedDirectory(sandboxRoot,{privateLeaf:true})',
    'readPrivateEntry(dir,name)',
    'open(lockPath,"wx",0o600)',
    'await handle.sync();',
    'await dir.sync();',
    'recheckOfflineCategorizedReview(',
    'prepareOfflineCategorizedReview(',
    'inspectM3d5b3SourceCompatibility(',
    'validateCategorizedExpenseCommand({',
    'receiptId=randomBytes(16).toString("hex")',
    'requestId=randomBytes(16).toString("hex")',
    'confirmation-in-progress-or-recovery-required',
    'receipt-financial-details-changed',
    'confirmed-held-no-dispatch',
    'production-dispatch-hard-hold',
    'dispatched:false',
    'canRetry:false',
]:
    assert required in src,required
for forbidden in [
    '@actual-app/api', 'child_process','spawn(', 'execFile(',
    'worker.exec(', 'Process {', 'addTransactions(', 'api.sync(',
    'write_categorized_expense.mjs',
    'FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED',
    'categorized-expense-writes-enabled',
    '".local","state","financew"',
    '".config","financew"',
]:
    assert forbidden not in src,forbidden
for file in [ui,draft,category,m3b,m3d5b1,m3d5b3]:
    assert 'simple_m3d5b4_disposable_confirmation' not in file
assert 'if (!reviewed || categoryPreviewArmed' in draft
assert 'if(!transactionDraftPane.categoryPreviewArmed)' in ui
assert 'return fail("production-dispatch-hard-hold")' in m3d5b1
print("FinanceW M3d5b4 NON-ACTIVATED custody production HARD HOLD PASS")
