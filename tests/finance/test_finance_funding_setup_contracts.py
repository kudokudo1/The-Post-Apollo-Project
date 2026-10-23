#!/usr/bin/env python3
"""D17 guided funding: source-bound planning only, never saving real money."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
ui=(root/"widgets/FinanceW.qml").read_text()
pane=(root/"widgets/FinanceFundingSetupPane.qml").read_text()
calc=(root/"services/finance/FinanceFundingSetupPlan.js").read_text()
assert 'id: guidedFundingSetup' in ui
assert 'label: guidedFundingPane.expanded' in ui
assert '"HIDE FUNDING SETUP" : "GUIDED FUNDING SETUP"' in ui
assert 'FinanceFundingSetupPane {' in ui
assert 'id: guidedFundingPane' in ui
assert 'snapshot: financeBudget.snapshot' in ui
assert 'guidedFundingPane.begin();' in ui
assert 'guidedFundingPane.clear();' in ui
assert ui.index('id: guidedFundingSetup') < ui.index('id: reviewIncoming')
for phrase in (
  'property string anchoredSource: ""',
  'property string anchoredMonth: ""',
  'function begin()',
  'function chooseMode(nextMode)',
  'function calculate()',
  'onSnapshotChanged:',
  'setup.sourceKey' # replaced below with actual grounded property
):
    if phrase=='setup.sourceKey': continue
    assert phrase in pane,phrase
assert 'snapshot.sourceKey!==anchoredSource' in pane
assert 'snapshot.month!==anchoredMonth' in pane
assert 'FundingRules.previewFundingSetup(snapshot,setupMode' in pane
assert 'label: "OPENING BALANCE"' in pane
assert 'label: "INCOME"' in pane
assert 'label: "PREVIEW SETUP"' in pane
assert 'label: "CLOSE SETUP"' in pane
assert 'NO SAVE / NO WRITES' in pane
assert 'EXISTING ACCOUNTS // REVIEW HISTORY' in pane
assert 'TO BUDGET AFTER // UNKNOWN UNTIL ACTUAL RECONCILES' in pane
assert 'MORE THAN 12 ACCOUNTS' in pane
assert 'NO COMPLETE INCOME CATEGORY LIST' in pane
assert pane.count('trackLabelGlowLocally: true') >= 5
assert 'openingBalanceVerified:false' in calc
assert 'writeAllowed:false,saveAvailable:false' in calc
assert 'toBudgetAfterCents:null' in calc
assert 'RECONCILE_EXISTING_ACCOUNT' in calc
assert 'REVIEW_NEW_INCOME_ENTRY' in calc
for content in (pane,calc):
    for forbidden in (
      'Process {','writeFile(','addTransactions(',
      'updateTransaction(','setBudgetAmount(','allocation-writes-enabled',
      'transaction-writes-enabled','createAccount(','Qt.openUrlExternally'
    ):
        assert forbidden not in content,forbidden
print("FinanceW D17 guided funding non-mutating UI contracts: PASS")
