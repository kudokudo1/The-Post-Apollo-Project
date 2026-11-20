#!/usr/bin/env python3
"""FinanceW FP1b: planned local records stay separate from Actual and Social."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
ui=(root/"widgets/FinanceW.qml").read_text()
base=(root/"widgets/FinanceHouseholdPlanningPane.qml").read_text()
pane=(root/"widgets/FinanceHouseholdPlansPane.qml").read_text()
bridge=(root/"services/finance/FinanceHouseholdPlanStore.qml").read_text()
cli=(root/"scripts/finance/household_plan_store.py").read_text()
assert 'FinanceHouseholdPlansPane {' in base
assert 'visible: planner.planningView==="plans"' in base
assert 'active: planner.active && planner.planningView==="plans"' in base
assert 'monitoring: plansPane.active' in pane
assert 'contextId: plansPane.contextId' in pane
assert 'onContextIdChanged:' in bridge
assert 'rows=[];' in bridge
assert 'submittedContext===store.contextId' in bridge
assert 'pendingReload=true;' in bridge
assert 'expectedRevision:revision' in bridge
assert 'onLeftClicked: plansPane.requestDelete(entryRow.modelData.id)' in pane
assert 'label: plansPane.armedDeleteId===entryRow.modelData.id' in pane
assert 'NeonScrollPaneV2 {' in pane
assert 'FinanceMoneyInput {' in pane
assert 'NO HOUSEHOLD ACCESS GRANT' in pane
assert 'NOT BANK VERIFIED' in pane
assert 'monitoring: root.menuOpen' in ui
assert 'active: root.menuOpen && root.selectedMainMode==="strategies"' in ui
assert 'embeddedComponent: marketPaneComponent' in ui
for forbidden in ('FinanceBudgetReadService','FinanceTransactionWriteService',
                  'FinanceFundingWriteService','ConnectionsBroker',
                  'SocialIdentityStore','FinanceStockHistoryReadService'):
    assert forbidden not in bridge and forbidden not in pane
for forbidden in ('@actual-app','sqlite3','requests','urllib.request',
                  'subprocess','SOCIAL_','ACTUAL_PASSWORD','ACTUAL_SYNC_ID'):
    assert forbidden not in cli
assert 'os.O_NOFOLLOW' in cli
assert 'os.fsync' in cli
assert 'fcntl.flock' in cli
assert 'STALE_REVISION' in cli
assert 'VALID' not in bridge or 'LOCAL_OPERATOR_PLANS' in bridge
print("FinanceW FP1b local-plan UI/source isolation: PASS")
