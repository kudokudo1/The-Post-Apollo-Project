#!/usr/bin/env python3
"""M3b dormant categorization writer: independent authority and recovery."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
writer=(root/"scripts/finance/write_categorized_expense.mjs").read_text()
guard=(root/"scripts/finance/categorized_expense_guard.mjs").read_text()
old=(root/"scripts/finance/write_transaction.mjs").read_text()
menu=(root/"widgets/FinanceW.qml").read_text()
draft=(root/"widgets/FinanceTransactionDraftPane.qml").read_text()
pane=(root/"widgets/FinanceExpenseCategoryPreviewPane.qml").read_text()
package=(root/"scripts/finance/package.json").read_text()

assert '"@actual-app/api": "26.10.0"' in package
# New authority cannot leak into existing FinanceW editor, category preview
# or the older uncategorized transaction writer.
for qml in (menu,draft,pane):
    assert "write_categorized_expense.mjs" not in qml
    assert "FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED" not in qml
    assert "categorized-expense-writes-enabled" not in qml
    assert "Process {" not in pane
    assert "addTransactions(" not in qml
assert "categoryId" not in draft
assert '"categoryId"' not in (root/"scripts/finance/transaction_guard.mjs").read_text()
assert "transaction-writes-enabled" in old
assert "categorized-expense-writes-enabled" not in old

# A private new operator permit. This file is NEVER provisioned in this PR.
assert 'join(config,"categorized-expense-writes-enabled")' in writer
assert 'permit!=="FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED"' in writer
assert "transaction-writes-enabled" not in writer
assert "allocation-writes-enabled" not in writer
assert "envelope-moves-enabled" not in writer
assert 'FINANCEW_CATEGORIZED_EXPENSE_RESULT ' in writer
assert 'validateCategorizedExpenseCommand(command)' in writer
assert 'executeCategorizedExpense({' in writer
assert '"categorized-expense-"+command.requestId+".json"' in writer
assert 'action:"transaction:create-categorized-expense"' in writer

# Identical cross-writer lock/journal and fail-closed UNCERTAIN path.
for code in (writer,old):
    assert 'join(homedir(),".local","state","financew","operations")' in code or (
        'join(homedir(), ".local", "state", "financew", "operations")' in code)
    assert 'join(' in code and '".write-lock"' in code
    assert '"wx",0o600' in code
    assert "recovery-needed" in code
    assert 'status!=="committed"' in code or 'status !== "committed"' in code
assert "await file.sync();" in writer
assert "await fsyncDirectory(journalDir);" in writer
assert 'attempted=true;' in writer
assert 'if(attempted)return "uncertain";' in writer
assert "priorNames.some(name=>name.endsWith(" in writer
assert '"-"+command.requestId+".json"' in writer
assert 'readActualServerURL()' in writer
assert '"http://127.0.0.1:5006"' in writer
assert '.update(serverURL+"\\0"+syncId)' in writer
assert 'if(command.sourceKey!==expectedKey)' in writer

# The one new transaction MUST contain category in its initial write.
# No second update or sync of an uncategorized transaction is allowed.
for marker in (
    "export function validateCategorizedExpenseCommand(input)",
    "export function preflightCategorizedExpense(input,{accounts,budget,rows})",
    "export async function executeCategorizedExpense({api,input,recordAttempt})",
    'input.action!=="create-categorized-expense"',
    "input.amountCents>=0",
    "cat.spent!==cmd.expectedCategorySpentCents",
    "cat.balance!==cmd.expectedCategoryAvailableCents",
    "cat.budgeted!==cmd.expectedCategoryBudgetedCents",
    "budget.toBudget!==cmd.expectedToBudgetCents",
    "if(matches.length!==1)",
    'if(group.is_income)continue;',
    "await recordAttempt(cmd);",
    "await api.addTransactions(cmd.accountId,[{",
    "category:cmd.categoryId",
    "imported_id:checked.importedId",
    "runTransfers:false,learnCategories:false",
    "await api.sync();",
    "found[0].category!==cmd.categoryId",
    'refuse("uncertain-write")',
):
    assert marker in guard,marker
assert guard.count("await api.addTransactions(")==1
assert "updateTransaction(" not in guard
assert "setBudgetAmount(" not in guard
assert "writeFile(" not in guard
assert guard.index("await recordAttempt(cmd);") < guard.index(
    "await api.addTransactions(cmd.accountId")
assert guard.index("await api.sync();") < guard.index(
    "const after=await api.getTransactions")
print("FinanceW Simple M3b dormant category-bound transaction writer: PASS")
