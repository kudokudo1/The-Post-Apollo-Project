#!/usr/bin/env python3
"""M3d4 is a disposable CI process-crash test, not a production writer change."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
harness=(root/"scripts/finance/disposable_categorized_expense_sigkill.mjs").read_text()
loader=(root/"tests/finance/fixtures/simple_m3d4_sigkill_loader.mjs").read_text()
workflow=(root/".github/workflows/financew-simple-m3d4-sigkill.yml").read_text()
writer=(root/"scripts/finance/write_categorized_expense.mjs").read_text()
menu=(root/"widgets/FinanceW.qml").read_text()
draft=(root/"widgets/FinanceTransactionDraftPane.qml").read_text()
preview=(root/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
for fragment in (
    'process.env.GITHUB_ACTIONS!=="true"',
    'process.env.CI!=="true"',
    'process.env.FINANCEW_DISPOSABLE_TEST!=="yes"',
    'CI-only-disposable-test',
    'await portFree();',
    '127.0.0.1:5006',
    'mkdtemp(join(tmpdir()',
    'HOME:fixture.home',
    'NODE_OPTIONS:""',
    '"--experimental-loader",loader,writer',
    'child.kill("SIGKILL")',
    'after-attempt',
    'after-add',
    'assert.equal(receipt.status,"attempted")',
    'SIGKILL-preserved-attempted-journal',
    'SIGKILL-preserved-stale-lock',
    'write-in-progress-or-recovery-needed',
    'recovery-needed',
    'assert.equal(existsSync(markers.journal),true',
    'FINANCEW_M3D4_SIGKILL_PASS',
):
    assert fragment in harness, fragment
for fragment in (
    'const target="/scripts/finance/categorized_expense_guard.mjs"',
    'await recordAttempt(cmd);',
    'await api.sync();',
    'm3d4-CI-only-loader',
    'm3d4-expected-single-policy-checkpoint',
    'm3d4-disposable-checkpoint-mismatch',
    'setInterval(() => {}, 1000)',
):
    assert fragment in loader, fragment
for fragment in (
    'node-version: "22"',
    '@actual-app/api@26.10.0',
    '@actual-app/sync-server@26.10.0',
    'FINANCEW_DISPOSABLE_TEST: "yes"',
    'permissions:\n  contents: read',
):
    assert fragment in workflow, fragment
for live in (menu,draft,preview,writer):
    assert 'disposable_categorized_expense_sigkill.mjs' not in live
    assert 'simple_m3d4_sigkill_loader.mjs' not in live
for live in (menu,draft,preview):
    assert 'write_categorized_expense.mjs' not in live
assert 'if (!reviewed || categoryPreviewArmed' in draft
assert 'if(!transactionDraftPane.categoryPreviewArmed)' in menu
assert 'categorized-expense-writes-enabled' in writer
print("M3d4 CI-only process SIGKILL; production write HOLD preserved: PASS")
