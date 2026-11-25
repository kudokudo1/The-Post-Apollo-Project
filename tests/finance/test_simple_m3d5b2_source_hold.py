#!/usr/bin/env python3
"""FinanceW M3d5b2: this transport remains disposable, no real dispatch."""
from pathlib import Path
r=Path(__file__).resolve().parents[2]
t=(r/"scripts/finance/simple_m3d5b2_disposable_transport.mjs").read_text()
child=(r/"tests/finance/fixtures/simple_m3d5b2_transport_child.mjs").read_text()
writer=(r/"scripts/finance/write_categorized_expense.mjs").read_text()
root=(r/"widgets/FinanceW.qml").read_text()
controller=(r/"scripts/finance/simple_m3d5b_protected_controller.mjs").read_text()
for marker in [
    'FINANCEW_DISPOSABLE_TEST==="yes"',
    'namePattern.test(basename(root))',
    'process.env.HOME===root',
    'reserveM3d5b2DisposableIntent',
    'validateCategorizedExpenseCommand(command)',
    'inspectM3d5b2StdinFrame',
    'inspectM3d5b2WriterOutcome',
    'readPrivateEntry(dir,name)',
    'openTrustedDirectory(sandboxRoot,{privateLeaf:true})',
    'open(lockPath,"wx",0o600)',
    'await record.sync();',
    'await dir.sync();',
    'releaseLock=true',
    'replay-or-duplicate-intent',
    'reservation-locked-recovery-required',
    'canSave:false,writeAllowed:false',
    'dispatched:false',
]:
    assert marker in t,marker
for forbidden in [
    '@actual-app/api', 'child_process', 'spawn(', 'execFile(', 'Process {',
    'worker.exec', 'addTransactions(', 'write_categorized_expense.mjs',
    'categorized-expense-writes-enabled', 'FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED',
    '.config","financew"', '".local","state","financew"',
]:
    assert forbidden not in t,forbidden
assert 'write_categorized_expense.mjs' not in child
assert 'simple_m3d5b2_disposable_transport' not in root
assert 'simple_m3d5b2_disposable_transport' not in controller
assert 'FINANCEW_CATEGORIZED_EXPENSE_RESULT ' in writer
assert 'if (!reviewed || categoryPreviewArmed' in (
    r/"widgets/FinanceTransactionDraftPane.qml").read_text()
print("FinanceW M3d5b2 disposable transport production HOLD: PASS")
