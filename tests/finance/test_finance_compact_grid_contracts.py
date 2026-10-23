#!/usr/bin/env python3
"""FinanceW compact spreadsheet UX, safe single-row save, hidden diagnostics."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
ui=(root/"widgets/FinanceW.qml").read_text()
grid=(root/"widgets/FinanceBudgetGrid.qml").read_text()
money=(root/"widgets/FinanceQuickAddPane.qml").read_text()
rules=(root/"services/finance/FinanceSpreadsheetPolicy.js").read_text()
assert 'property bool advancedOpen: false' in ui
assert 'id: quickAddMoney' in ui
assert 'id: quickAddPane' in ui
assert 'id: financeBudgetGrid' in ui
assert 'id: advancedToggle' in ui
assert 'visible: root.advancedOpen' in ui
assert ui.index('id: quickAddMoney') < ui.index('id: reviewFunding')
assert ui.index('id: financeBudgetGrid') < ui.index('id: advancedToggle')
assert ui.index('id: advancedToggle') < ui.index('id: reviewFunding')
assert ui.index('id: reviewFunding') < ui.index('id: newTransactionDraft')
assert 'quickAddPane.clear();' in ui
assert 'financeBudgetGrid.reset();' in ui
assert 'financeFundingWrite.submit(payload);' in ui
assert 'financeAllocationWrite.submit(payload);' in ui
assert 'payload.sourceKey===financeBudget.snapshot.sourceKey' in ui
assert 'payload.month===financeBudget.snapshot.month' in ui
for phrase in (
 'import "../services/finance/FinanceSpreadsheetPolicy.js" as StepRules',
 'import "../services/finance/FinanceAllocationPreview.js" as AllocationRules',
 'property string selectedCategoryId: ""',
 'readonly property var proposal:',
 'AllocationRules.previewAllocation(snapshot,selectedCategoryId,draftText)',
 'proposal.allocationChangeCents!==0',
 '!proposal.exceedsUnallocatedFunds && !proposal.categoryRemainsOverspent',
 'proposal.originalBudgetedCents===selectedCategory.budgetedCents',
 'proposal.originalAvailableCents===selectedCategory.availableCents',
 'proposal.toBudgetBeforeCents===snapshot.toBudgetCents',
 'function saveSelected()',
 'if(!canSave || !selectedCategory)return false;',
 'submitted=true;',
 'action:"set-amount",requestId:id,',
 'signal saveRequested(var payload)',
 'label: grid.submitted ? "SENT" : "SAVE ROW"',
 'onLeftClicked: grid.saveSelected()',
 'FinanceMoneyInput {',
 'StepRules.stepAmount(source,delta,true)',
 'text: "SET (EDIT)"',
 'text: "SPENT"',
 'text: "LEFT"',
 'modelData.spentCents',
 'modelData.availableCents',
 'onSnapshotChanged: reset()',
): assert phrase in grid,phrase
assert grid.count('FinanceMoneyInput {') == 1
assert grid.count('ActionButton {') == 3
assert 'SAVE ALL' not in grid
for phrase in (
 'function submit()',
 'signal saveRequested(var payload)',
 'kind: "income"',
 'mode:"income",requestId:id',
 'StepRules.stepAmount(amountText,delta,false)',
 'FinanceDateInput {',
 'FinanceMoneyInput {',
 'canSubmit',
 'FundingRules.previewFundingSetup(snapshot,"income",accountId,',
 'label: quick.submitted ? "REQUEST SENT"',
 'onLeftClicked: quick.submit()',
 'quick.kind==="opening"',
 'EXISTING BALANCES NEED RECONCILIATION',
 'sourceKey:proposal.sourceKey',
 'amountCents:proposal.amountCents',
 'description:descriptionText.trim()'
): assert phrase in money,phrase
assert money.count('FinanceMoneyInput {') == 1
assert money.count('FinanceDateInput {') == 1
assert "new-account-opening" not in money
assert 'writeAllowed:false' in (root/"services/finance/FinanceFundingSetupPlan.js").read_text()
for content in (money,grid,rules):
 for forbidden in ('Process {','writeFile(','LocalStorage','Settings {',
                   'createAccount(', 'addTransactions(', 'setBudgetAmount(',
                   'funding-writes-enabled','FINANCEW_FUNDING_WRITES_APPROVED',
                   'allocation-writes-enabled','FINANCEW_ALLOCATION_WRITES_APPROVED'):
  assert forbidden not in content,forbidden
print("FinanceW compact budget grid & add money source contracts: PASS")
