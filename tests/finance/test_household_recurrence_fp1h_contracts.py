#!/usr/bin/env python3
"""FinanceW FP1h source-only v4, recurrence, and trust boundary checks."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
store=(root/"scripts/finance/household_schedule_store.py").read_text()
bridge=(root/"services/finance/FinanceHouseholdScheduleStore.qml").read_text()
schedule=(root/"widgets/FinanceHouseholdSchedulePane.qml").read_text()
policy=(root/"widgets/FinanceHouseholdTimelinePolicy.js").read_text()
timeline=(root/"widgets/FinanceHouseholdTimelinePane.qml").read_text()
plans=(root/"widgets/FinanceHouseholdPlansPane.qml").read_text()
assert 'doc["version"] not in (1, 2, 3, 4)' in store
assert 'kind == "bill_cadence"' in store
assert "make_cadence" in store
assert "add_cadence" in store and "update_cadence" in store
assert "INVALID_RECURRENCE_EXCEPTION" in store
assert "STALE_REVISION" in store
assert "os.O_NOFOLLOW" in store and "fcntl.flock" in store
assert "os.fsync" in store and "os.replace" in store
assert "BILL_HAS_EXCEPTIONS" in store
assert "doc.version===4" in bridge
assert 'function addCadence(expenseId,intervalMonths,anchorMonth)' in bridge
assert 'function updateCadence(id,expenseId,intervalMonths,anchorMonth)' in bridge
assert "store.submittedContext===store.contextId" in bridge
assert "QUARTERLY / ANNUAL BILL FREQUENCY" in schedule
assert 'schedules.setKind("cadence")' in schedule
assert "scheduleStore.addCadence(" in schedule
assert "scheduleStore.updateCadence(" in schedule
assert "cadenceIntervalMonths===3" in schedule
assert "cadenceIntervalMonths===12" in schedule
assert "PER CHARGE" in schedule
assert "REMOVE FREQUENCY ENTRY TO RESTORE MONTHLY CHARGES" in schedule
assert "function chargeOccurs(month,cadence)" in policy
assert 'cadenceCount:cadences.length' in policy
assert "DUPLICATE_BILL_CADENCE" in policy
assert "INVALID_RECURRENCE_EXCEPTION" in policy
assert "chargeOccurs(month,cadenceById.get(row.id))" in policy
assert "chargeOccurs(month,cadenceById.get(row.expenseId))" in policy
assert "baseExpenseCents:scheduledCosts" in policy
assert "QUARTERLY" in timeline and "ANNUAL" in timeline
assert "PER OCCURRENCE" in timeline
assert "QUARTERLY_OR_ANNUAL_BILLS_USE_TIMELINE" in plans
assert "!localSchedule.ready" in plans
assert "CashFlow.summarize(savedPlans.rows,forecastMonths)" in plans
for block in (store,policy,schedule,bridge,timeline,plans):
    for forbidden in ("FinanceTransactionWriteService","FinanceFundingWriteService",
                      "ConnectionsBroker","SocialIdentityStore",
                      "FinanceStockHistoryReadService"):
        assert forbidden not in block, forbidden
for forbidden in ("@actual-app","sqlite3","requests","urllib.request",
                  "subprocess","ACTUAL_PASSWORD","ACTUAL_SYNC_ID","SOCIAL_"):
    assert forbidden not in store, forbidden
print("FinanceW FP1h recurrence safety and source isolation: PASS")
