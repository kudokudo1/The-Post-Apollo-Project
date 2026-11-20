#!/usr/bin/env python3
"""FP1f source ownership and schedule edit/exception UI contracts."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceHouseholdSchedulePane.qml").read_text()
bridge=(root/"services/finance/FinanceHouseholdScheduleStore.qml").read_text()
policy=(root/"widgets/FinanceHouseholdTimelinePolicy.js").read_text()
timeline=(root/"widgets/FinanceHouseholdTimelinePane.qml").read_text()
store=(root/"scripts/finance/household_schedule_store.py").read_text()
assert "onScheduleUpdated: schedules.clearEditor()" in pane
assert 'property int editingRevision: -1' in pane
assert 'scheduleStore.updateBill(' in pane
assert 'scheduleStore.updatePurchase(' in pane
assert 'scheduleStore.updateSkip(' in pane
assert 'scheduleStore.addSkip(' in pane
assert 'schedules.editingStale' in pane
assert "EDIT STALE // CANCEL" in pane
assert 'onLeftClicked: schedules.beginEdit(scheduleRow.modelData)' in pane
assert "ONE-MONTH BILL EXCLUSION" in pane
assert "NOT A WAIVER OR PAYMENT" in pane
assert 'doc.version===2' in bridge
assert 'function updateBill(id,expenseId,dueDay)' in bridge
assert 'function updatePurchase(id,title,date,amountText,fundingGoalId)' in bridge
assert 'function addSkip(expenseId,month)' in bridge
assert 'function updateSkip(id,expenseId,month)' in bridge
assert 'store.submittedContext===store.contextId' in bridge
assert "function coverage(rows,schedules)" in policy
assert 'allObligationsKnown:false' in policy
assert "DUPLICATE_BILL_EXCEPTION" in policy
assert "SCHEDULE_REFERENCE_MISSING" in policy
assert 'income-currentCosts-contributions-purchaseNewCash' in policy
assert "exceptionEvents:exceptionEvents" in policy
assert 'Timeline.coverage(sourceRows,scheduleRows)' in timeline
assert "MISSING DUE DAYS" in timeline
assert "NOT CONFIRMED WAIVED OR PAID" in timeline
assert "upgrade_in_memory" in store
assert 'return upgrade_in_memory(doc), False' in store
assert 'BILL_HAS_EXCEPTIONS' in store
assert 'STALE_REVISION' in store
for block in (pane,bridge,timeline):
    for forbidden in ("FinanceBudgetReadService","FinanceTransactionWriteService",
                      "FinanceFundingWriteService","ConnectionsBroker",
                      "SocialIdentityStore","FinanceStockHistoryReadService"):
        assert forbidden not in block,forbidden
for forbidden in ("@actual-app","sqlite3","requests","urllib.request",
                  "subprocess","ACTUAL_PASSWORD","ACTUAL_SYNC_ID","SOCIAL_"):
    assert forbidden not in store,forbidden
print("FinanceW FP1f schedule editor and coverage isolation: PASS")
