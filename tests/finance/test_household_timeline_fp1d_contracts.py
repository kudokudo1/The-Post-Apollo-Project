#!/usr/bin/env python3
"""FP1d timeline is view-only, context-scoped, without new private-data paths."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceHouseholdPlansPane.qml").read_text()
timeline=(root/"widgets/FinanceHouseholdTimelinePane.qml").read_text()
policy=(root/"widgets/FinanceHouseholdTimelinePolicy.js").read_text()
assert 'import "FinanceHouseholdTimelinePolicy.js" as Timeline' in timeline
assert 'FinanceHouseholdTimelinePane {' in pane
assert 'visible: plansPane.section==="timeline"' in pane
assert 'active: savedPlans.state==="ready"' in pane
assert 'sourceRows: savedPlans.rows' in pane
assert 'contextId: plansPane.contextId' in pane
assert 'startMonth: plansPane.currentMonth' in pane
assert 'onHorizonRequested: function(months)' in pane
# FP1e adds SCHEDULE without displacing the original TIMELINE page.
assert ('"timeline"].indexOf(next)' in pane or
        '"timeline","schedule"].indexOf(next)' in pane)
assert 'forecastMonths=12;' in pane
assert 'timelineMonths=6;' in pane
assert 'NeonScrollPaneV2 {' in pane
assert 'ActionButton {' in timeline
assert 'NOT AVAILABLE CASH' in timeline
assert 'NOT A PURCHASE PAYMENT' in timeline
assert 'ESTIMATES ONLY:' in timeline
assert 'source:"LOCAL_MANUAL_TIMELINE_ONLY"' in policy
assert 'futurePurchasesCharged:false' in policy
assert 'actualTransfersMade:false' in policy
assert 'missingCostsPossible:true' in policy
assert 'contribution=Math.min(outstanding,goal.plannedMonthlyCents)' in policy
for forbidden in ('Process {','FileView {','Timer {','FinanceBudgetReadService',
                  'FinanceTransactionWriteService','FinanceFundingWriteService',
                  'ConnectionsBroker','SocialIdentityStore','HttpRequest'):
    assert forbidden not in timeline,forbidden
for forbidden in ('fetch(','XMLHttpRequest','readFile','writeFile','Process',
                  'ConnectionsBroker','@actual-app'):
    assert forbidden not in policy,forbidden
print("FinanceW FP1d timeline integration and isolation: PASS")
