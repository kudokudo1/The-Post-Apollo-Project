#!/usr/bin/env python3
"""CI-only real Actual 26.10.0 rehearsal; production UI/writer untouched."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
test=(root/"scripts/finance/disposable_categorized_expense_roundtrip.mjs").read_text()
workflow=(root/".github/workflows/financew-simple-m3d3-disposable.yml").read_text()
writer=(root/"scripts/finance/write_categorized_expense.mjs").read_text()
menu=(root/"widgets/FinanceW.qml").read_text()
draft=(root/"widgets/FinanceTransactionDraftPane.qml").read_text()
pane=(root/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
for token in (
    'process.env.GITHUB_ACTIONS!=="true"',
    'process.env.CI!=="true"',
    'process.env.FINANCEW_DISPOSABLE_TEST!=="yes"',
    'CI-only-disposable-test',
    'http://127.0.0.1:5006',
    'await assertPortFree()',
    'mkdtemp(join(tmpdir()',
    'HOME:home',
    'blocked:writes-disabled',
    'blocked:budget-source-changed',
    'blocked:stale-budget',
    'blocked:operation-already-attempted',
    'blocked:possible-duplicate',
    'blocked:recovery-needed',
    'status,"committed"',
    'category-persists',
    'no-automatic-add-retry',
    'no-automatic-sync-retry',
    'transaction-writes-enabled',
    'FINANCEW_M3D3_DISPOSABLE_PASS'
):
    assert token in test, token
assert 'node-version: "22"' in workflow
assert '@actual-app/api@26.10.0' in workflow
assert '@actual-app/sync-server@26.10.0' in workflow
assert 'FINANCEW_DISPOSABLE_TEST: "yes"' in workflow
assert 'permissions:\n  contents: read' in workflow
assert 'write_categorized_expense.mjs' not in menu
assert 'write_categorized_expense.mjs' not in draft
assert 'write_categorized_expense.mjs' not in pane
assert 'disposable_categorized_expense_roundtrip.mjs' not in (menu+draft+pane)
assert 'if (!reviewed || categoryPreviewArmed' in draft
assert 'if(!transactionDraftPane.categoryPreviewArmed)' in menu
assert 'categorized-expense-writes-enabled' in writer
print("M3d3 disposable-only CI, production financial writes remain disconnected: PASS")
