#!/usr/bin/env python3
"""M3c real-root integration contract: category preview never goes to Save."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
menu=(root/"widgets/FinanceW.qml").read_text()
draft=(root/"widgets/FinanceTransactionDraftPane.qml").read_text()
pane=(root/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
guard=(root/"scripts/finance/transaction_guard.mjs").read_text()
new_writer=(root/"scripts/finance/write_categorized_expense.mjs").read_text()

# The M3a proposal is mounted once, shares the existing single read-only
# budget feed and stays separate from either protected finance writer.
assert menu.count("FinanceExpenseCategoryPreviewPane {")==1
assert menu.count('FinanceServices.FinanceBudgetReadService {')==1
assert menu.count('FinanceTransactionDraftPane {')==1
assert 'id: expenseCategoryPreviewPane' in menu
assert 'objectName: "financeBudgetExpenseCategoryPreview"' in menu
assert 'snapshot: financeBudget.snapshot' in menu
assert 'write_categorized_expense.mjs' not in menu
assert 'write_categorized_expense.mjs' not in draft
assert 'write_categorized_expense.mjs' not in pane
assert 'categorized-expense-writes-enabled' not in menu
assert 'FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED' not in menu

# User interaction is an isolated new-expense-only proposal signal.
for phrase in (
    'signal categoryPreviewRequested(var candidate)',
    'property bool allowCategoryPreview: false',
    'property bool categoryPreviewArmed: false',
    'function requestCategoryPreview()',
    'categoryPreviewRequested({',
    'action:"create",direction:"expense",editing:false,',
    'description:payeeText.trim(),amountCents:signedAmountCents',
    'function discardCategoryPreview()',
    'categoryPreviewArmed = false;',
    'objectName: "draftCategoryPreviewLauncher"',
    'label: "CATEGORY // PREVIEW ONLY"',
    'objectName: "draftDiscardCategoryPlan"',
    'label: "DISCARD CATEGORY PLAN // UNCATEGORIZED"',
    'objectName: "draftCategoryPreviewWarning"',
    'CATEGORY PLAN NOT SAVED // CONFIRM SAVE BLOCKED',
    'EXISTING CONFIRM SAVE WRITES AN UNCATEGORIZED EXPENSE',
):
    assert phrase in draft,phrase
assert 'visible: draft.allowCategoryPreview && !draft.editing' in draft
assert 'draft.direction === "expense"' in draft
assert 'saveRequested(payload);' in draft
assert 'categoryId' not in draft
assert '"categoryId"' not in guard
assert "category: " not in guard

# Once a category proposal is opened, the old CONFIRM SAVE and local draft
# actions are blocked even if the proposal is CANCELLED. Re-enabling Save
# requires explicitly DISCARD CATEGORY PLAN and a new PREVIEW review.
assert 'if (!reviewed || categoryPreviewArmed || validationError !== ""' in draft
assert 'if (editing || categoryPreviewArmed || draftStoreState !== "ready"' in draft
assert '!draft.categoryPreviewArmed' in draft
assert 'categoryPreviewArmed = false;' in draft.split('function clear()',1)[1].split('onSelectedMonthChanged:',1)[0]
assert 'reviewed = false;' in draft.split('function discardCategoryPreview()',1)[1].split('function beginForAccount(',1)[0]

# Source and account binding: same Budget snapshot, Simple presentation, no
# new money service or pass-through to the separately-permitted M3b CLI.
assert 'allowCategoryPreview: root.budgetExperienceMode==="simple"' in menu
assert 'onCategoryPreviewRequested: function(candidate)' in menu
assert 'root.budgetSection==="transactions"' in menu
assert 'candidate.sourceKey===financeBudget.snapshot.sourceKey' in menu
assert 'candidate.month===financeBudget.snapshot.month' in menu
assert 'expenseCategoryPreviewPane.begin(candidate)' in menu
assert 'transactionDraftPane.categoryPreviewArmed=true;' in menu
assert 'if(!transactionDraftPane.categoryPreviewArmed)' in menu
assert 'financeWrite.submit(payload);' in menu
assert menu.index('id: transactionDraftPane') < menu.index(
    'id: expenseCategoryPreviewPane') < menu.index('id: reloadDrafts')

# Open source or input changes invalidate the proposal. Nothing in the child
# has an action to save, persist, provision or call an Actual API.
for marker in (
    'function onDateTextChanged() { expenseCategoryPreviewPane.clear(); }',
    'function onPayeeTextChanged() { expenseCategoryPreviewPane.clear(); }',
    'function onAmountTextChanged() { expenseCategoryPreviewPane.clear(); }',
    'function onDirectionChanged() { expenseCategoryPreviewPane.clear(); }',
    'function onAccountIndexChanged() { expenseCategoryPreviewPane.clear(); }',
    'function onCategoryPreviewArmedChanged()',
    'expenseCategoryPreviewPane.clear();',
):
    assert marker in menu,marker
assert 'onSnapshotChanged: clear()' in pane
assert 'onCandidateChanged: invalidate()' in pane
assert 'onSelectedCategoryIdChanged: invalidate()' in pane
assert 'signal saveRequested' not in pane
assert 'signal moveRequested' not in pane
for source in (draft,pane):
    for forbidden in ('Process {','setBudgetAmount(','addTransactions(',
                      'updateTransaction(','fetch(','LocalStorage',
                      'FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED'):
        assert forbidden not in source,forbidden

# Source writer remains a distinct, unused operator authority.
assert 'join(config,"categorized-expense-writes-enabled")' in new_writer
assert 'executeCategorizedExpense({' in new_writer
print("FinanceW M3c Simple category selection is UI-only and cannot silently save: PASS")
