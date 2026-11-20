#!/usr/bin/env python3
"""FP1c protected-source boundary and UI contracts."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceHouseholdPlansPane.qml").read_text()
bridge=(root/"services/finance/FinanceHouseholdPlanStore.qml").read_text()
store=(root/"scripts/finance/household_plan_store.py").read_text()
policy=(root/"widgets/FinanceHouseholdCashFlowPolicy.js").read_text()
assert 'property string editingId: ""' in pane
assert 'savedPlans.update(' in pane
assert 'onEntryUpdated: plansPane.clearEditor()' in pane
assert 'onLeftClicked: plansPane.beginEdit(entryRow.modelData)' in pane
assert 'savedPlans.state==="ready"' in pane
assert 'selected: plansPane.section==="forecast"' in pane
assert 'FinanceHouseholdCashFlowPolicy.js' in pane
assert 'ADD_MANUAL_MONTHLY_INCOME' in policy
assert 'source:"LOCAL_MANUAL_PLAN_ONLY"' in policy
assert 'verifiedBankBalance:false' in policy
assert 'function update(id,kind,title,targetText,savedText,monthlyText,deadlineMonth)' in bridge
assert 'doc.version===2' in bridge
assert 'store.submittedContext===store.contextId' in bridge
assert 'upgrade_in_memory' in store
assert 'return upgrade_in_memory(doc), False' in store
assert 'KIND_CHANGE_REFUSED' in store
for forbidden in ('@actual-app','sqlite3','requests','urllib.request',
                  'subprocess','ACTUAL_PASSWORD','ACTUAL_SYNC_ID','SOCIAL_'):
    assert forbidden not in store,forbidden
for forbidden in ('FinanceBudgetReadService','FinanceTransactionWriteService',
                  'FinanceFundingWriteService','ConnectionsBroker',
                  'SocialIdentityStore','FinanceStockHistoryReadService'):
    assert forbidden not in pane and forbidden not in bridge
print("FinanceW FP1c source isolation and migration: PASS")
