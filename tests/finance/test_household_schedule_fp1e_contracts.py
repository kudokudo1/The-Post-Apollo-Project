#!/usr/bin/env python3
"""FinanceW FP1e source ownership and no-money-movement invariants."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceHouseholdPlansPane.qml").read_text()
timeline=(root/"widgets/FinanceHouseholdTimelinePane.qml").read_text()
editor=(root/"widgets/FinanceHouseholdSchedulePane.qml").read_text()
bridge=(root/"services/finance/FinanceHouseholdScheduleStore.qml").read_text()
store=(root/"scripts/finance/household_schedule_store.py").read_text()
policy=(root/"widgets/FinanceHouseholdTimelinePolicy.js").read_text()
assert "FinanceHouseholdSchedulePane {" in pane
assert 'visible: plansPane.section==="schedule"' in pane
assert 'contextId: plansPane.contextId' in pane
assert 'scheduleRows: localSchedule.scheduleRows' in pane
assert 'schedulesReady: localSchedule.ready' in pane
assert '["goals","expenses","income","forecast","timeline","schedule"]' in pane
assert "FinanceServices.FinanceHouseholdScheduleStore {" in editor
assert "monitoring: schedules.active" in editor
assert "onLeftClicked: schedules.save()" in editor
assert "onLeftClicked: schedules.requestDelete(scheduleRow.modelData.id)" in editor
assert 'label: schedules.armedDeleteId===scheduleRow.modelData.id' in editor
assert "BILL DUE DAYS REUSE MONTHLY COSTS" in editor
assert "GOAL-LINKED PURCHASES FIRST USE" in editor
assert 'Timeline.project(sourceRows,scheduleRows,startMonth,horizonMonths,contextId)' in timeline
assert "billEvents" in timeline and "purchaseEvents" in timeline
assert "NOT ACTUALLY PAID" in timeline
assert "GOAL_SPENT_EARLIER" in timeline
assert "INCLUDED IN COSTS ONCE" in timeline
assert "SCHEDULE_REFERENCE_MISSING" in policy
assert "futurePurchasesCharged:false" in policy
assert "actualTransfersMade:false" in policy
assert "funding.allocatedCents-=reserved" in policy
assert "funding.completedByPurchase=true" in policy
assert 'source:"LOCAL_MANUAL_TIMELINE_ONLY"' in policy
assert 'source==="LOCAL_OPERATOR_SCHEDULES"' in bridge
assert "store.submittedContext===store.contextId" in bridge
assert "expectedRevision:revision" in bridge
assert "os.O_NOFOLLOW" in store and "fcntl.flock" in store
assert "os.fsync" in store and "STALE_REVISION" in store
for forbidden in ("@actual-app","sqlite3","requests","urllib.request",
                  "subprocess","ACTUAL_PASSWORD","ACTUAL_SYNC_ID","SOCIAL_"):
    assert forbidden not in store,forbidden
for component in (timeline,editor,bridge):
    for forbidden in ("FinanceBudgetReadService","FinanceTransactionWriteService",
                      "FinanceFundingWriteService","ConnectionsBroker",
                      "SocialIdentityStore","FinanceStockHistoryReadService"):
        assert forbidden not in component,forbidden
print("FinanceW FP1e schedule/timeline protected boundaries: PASS")
