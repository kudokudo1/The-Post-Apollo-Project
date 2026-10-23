#!/usr/bin/env python3
"""FinanceW budget control-center section routing & no-write boundaries."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
menu=(root/"widgets/FinanceW.qml").read_text()
tx=(root/"widgets/FinanceTransactionDraftPane.qml").read_text()
accounts=(root/"widgets/FinanceAccountsPane.qml").read_text()
cats=(root/"widgets/FinanceCategoriesPane.qml").read_text()
read=(root/"scripts/finance/actual_readonly.mjs").read_text()

assert 'property string budgetSection: "budget"' in menu
assert 'function selectBudgetSection(section) {' in menu
assert 'budgetScroll.contentY=0;' in menu
assert 'transactionDraftPane.open && section!=="transactions"' in menu
assert 'id: budgetSectionTabs' in menu
for label in ('"BUDGET"','"TRANSACTIONS"','"ACCOUNTS"','"CATEGORIES"'):
    assert label in menu,label
for name in ('budget','transactions','accounts','categories'):
    assert '{key:"'+name+'"' in menu,name
assert 'onLeftClicked: root.selectBudgetSection(modelData.key)' in menu
for name in ('budgetSectionContent','transactionsSectionContent',
             'financeAccountsPane','financeCategoriesPane'):
    assert 'id: '+name in menu,name
for name in ('budget','transactions','accounts','categories'):
    assert 'visible: root.budgetSection==="'+name+'"' in menu,name

assert menu.index('id: budgetSectionTabs') < menu.index('id: quickAddMoney')
assert menu.index('id: financeBudgetGrid') < menu.index('id: advancedToggle')
assert menu.index('id: advancedToggle') < menu.index('id: financeAccountsPane')
assert menu.index('id: financeAccountsPane') < menu.index('id: transactionsSectionContent')
assert menu.index('id: financeCategoriesPane') < menu.index('id: transactionsSectionContent')

# Existing guarded sources and transaction list move, not get duplicated.
assert menu.count('FinanceTransactionDraftPane {') == 1
assert menu.count('id: newTransactionDraft') == 1
assert menu.count('id: editTransaction') == 1
assert 'onLeftClicked: transactionDraftPane.beginEdit(modelData)' in menu
assert 'onLeftClicked: transactionDraftPane.begin()' in menu
assert 'onLeftClicked: transactionDraftPane.beginStored(modelData)' in menu
assert 'onSaveRequested: function(payload) {' in menu
assert 'financeWrite.submit(payload);' in menu
assert 'financeAllocationWrite.submit(payload);' in menu
assert 'financeFundingWrite.submit(payload);' in menu

assert 'signal newTransactionRequested()' in accounts
assert 'snapshot.transactions.filter(' in accounts
assert 'a.id===selectedAccountId' in accounts
assert 'onLeftClicked: accountsPane.newTransactionRequested()' in accounts
assert 'transactionDraftPane.beginForAccount(financeAccountsPane.selectedAccountId);' in menu
assert 'function beginForAccount(selectedAccountId)' in tx
assert 'accountIndex=selected;' in tx
assert 'transactionDraftPane.begin();' in menu

assert 'signal editBudgetRequested(var category)' in cats
assert 'filterText.trim().toLowerCase()' in cats
assert 'onLeftClicked: categoryPane.editBudgetRequested(item.modelData)' in cats
assert 'financeBudgetGrid.choose(category);' in menu
assert 'root.selectBudgetSection("budget");' in menu
assert 'modelData.budgetedCents' in cats
assert 'modelData.availableCents' in cats
assert 'categoryRows.push({' in read
assert 'accountRows = accounts.filter(' in read

for code in (accounts,cats):
    for forbidden in ('Process {','writeFile(', 'LocalStorage', 'Settings {',
                      'createAccount(', 'addTransactions(', 'updateTransaction(',
                      'setBudgetAmount(', 'downloadBudget(', 'api.'):
        assert forbidden not in code,forbidden
assert 'FINANCEW_FUNDING_WRITES_APPROVED' not in menu
assert 'FINANCEW_ALLOCATION_WRITES_APPROVED' not in menu
assert 'FINANCEW_TRANSACTION_WRITES_APPROVED' not in menu
print("FinanceW budget control sections and existing guarded flows: PASS")
