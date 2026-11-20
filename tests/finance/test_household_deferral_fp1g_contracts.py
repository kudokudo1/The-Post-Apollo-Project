#!/usr/bin/env python3
"""FP1g source contracts for explicit planned deferrals."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
store=(root/"scripts/finance/household_schedule_store.py").read_text()
bridge=(root/"services/finance/FinanceHouseholdScheduleStore.qml").read_text()
ui=(root/"widgets/FinanceHouseholdSchedulePane.qml").read_text()
policy=(root/"widgets/FinanceHouseholdTimelinePolicy.js").read_text()
timeline=(root/"widgets/FinanceHouseholdTimelinePane.qml").read_text()
assert "make_defer" in store
assert "doc[\"version\"] not in (1, 2, 3)" in store
assert "add_defer" in store and "update_defer" in store
assert "BILL_HAS_EXCEPTIONS" in store
assert "STALE_REVISION" in store
assert "doc[\"version\"] in (2, 3)" in store
assert "sourceMonth" in store
assert 'doc.version===2 || doc.version===3' in bridge
assert 'function addDeferral(expenseId,sourceMonth,targetDate)' in bridge
assert 'function updateDeferral(id,expenseId,sourceMonth,targetDate)' in bridge
assert 'store.submittedContext===store.contextId' in bridge
assert "DEFER ONE BILL TO A LATER DATE" in ui
assert "scheduleStore.addDeferral(" in ui
assert "scheduleStore.updateDeferral(" in ui
assert "onLeftClicked: schedules.beginEdit(scheduleRow.modelData)" in ui
assert "MODELED ONLY" in ui
assert "MUST BE A LATER MONTH" in ui
assert "deferredPaymentCount:deferrals.length" in policy
assert "movedPaymentCents:movedPaymentCents" in policy
assert "income-currentCosts-contributions-purchaseNewCash-movedPaymentCents" in policy
assert "CONFLICTING_BILL_EXCEPTION" in policy
assert "DUPLICATE_BILL_DEFERRAL" in policy
assert "SCHEDULE_REFERENCE_MISSING" in policy
assert "monthCard.modelData.movedToEvents" in timeline
assert "monthCard.modelData.movedFromEvents" in timeline
assert "PLUS CURRENT ORDINARY BILL" in timeline
for source in (ui,bridge,timeline):
    for forbidden in ("FinanceTransactionWriteService","FinanceFundingWriteService",
                      "ConnectionsBroker","SocialIdentityStore",
                      "FinanceStockHistoryReadService"):
        assert forbidden not in source, forbidden
for forbidden in ("@actual-app","sqlite3","requests","urllib.request",
                  "subprocess","ACTUAL_PASSWORD","ACTUAL_SYNC_ID","SOCIAL_"):
    assert forbidden not in store, forbidden
print("FinanceW FP1g explicit deferral ownership and source boundaries: PASS")
