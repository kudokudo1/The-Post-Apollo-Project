#!/usr/bin/env python3
"""FinanceW M3d5b3 bridge contract is pure, non-authorizing and unmounted."""
from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"scripts/finance/simple_m3d5b3_bridge_contract.mjs").read_text()
controller=(r/"scripts/finance/simple_m3d5b_protected_controller.mjs").read_text()
transport=(r/"scripts/finance/simple_m3d5b2_disposable_transport.mjs").read_text()
writer=(r/"scripts/finance/write_categorized_expense.mjs").read_text()
root=(r/"widgets/FinanceW.qml").read_text()
draft=(r/"widgets/FinanceTransactionDraftPane.qml").read_text()
preview=(r/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
for positive in [
    'inspectM3d5b3SourceCompatibility',
    'inspectM3d5b3PreDispatch',
    'classifyM3d5b3SyntheticRecovery',
    'prepareOfflineCategorizedReview(',
    'recheckOfflineCategorizedReview(',
    'inspectM3d5b2WriterOutcome(',
    'readerEndpoint!==writerEndpoint',
    'writerEndpoint!==pinnedWriterEndpoint',
    'readerSourceKey!==writerSourceKey',
    'request-identity-issued-and-discarded',
    'durable-request-id-not-exported',
    'requestIssued:false',
    'dispatchAllowed:false',
    'canRetry:false',
    'productionWrite:false',
    'syntheticOnly:true',
]:
    assert positive in c,positive
for forbidden in [
    '@actual-app/api', 'write_categorized_expense.mjs',
    'spawn(', 'exec(', 'child_process', 'Process {', 'worker.exec',
    'addTransactions(', 'writeFile(', 'mkdir(', 'open("wx"',
    'readTrustedPrivateFile(', 'readActualServerURL(', 'FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED',
    'categorized-expense-writes-enabled', 'fs/promises',
]:
    assert forbidden not in c,forbidden
for mounted in (root,draft,preview,controller,writer):
    assert 'simple_m3d5b3_bridge_contract' not in mounted
assert 'if (!reviewed || categoryPreviewArmed' in draft
assert 'if(!transactionDraftPane.categoryPreviewArmed)' in root
assert 'return fail("production-dispatch-hard-hold")' in controller
assert 'dispatched:false' in transport
print("FinanceW M3d5b3 pure protected bridge: FINANCIAL WRITES HARD HOLD PASS")
