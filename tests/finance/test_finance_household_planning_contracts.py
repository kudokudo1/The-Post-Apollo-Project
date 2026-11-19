#!/usr/bin/env python3
"""FP1a Strategies pane and sensitive-data separation."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
ui=(root/"widgets/FinanceW.qml").read_text()
pane=(root/"widgets/FinanceHouseholdPlanningPane.qml").read_text()
policy=(root/"widgets/FinanceHouseholdPlanningPolicy.js").read_text()
assert 'id: "strategies"' in ui
assert 'FinanceHouseholdPlanningPane {' in ui
assert 'visible: root.selectedMainMode === "strategies"' in ui
assert '&& root.selectedMainMode !== "strategies"' in ui
assert 'embeddedComponent: marketPaneComponent' in ui
assert 'showEmbedded: root.selectedMainMode === "market"' in ui
assert 'import "FinanceHouseholdPlanningPolicy.js" as Planning' in pane
assert 'NeonScrollPaneV2 {' in pane
assert 'FinanceMoneyInput {' in pane
assert 'onLeftClicked: planner.chooseContext(modelData.id)' in pane
assert 'onLeftClicked: planner.calculate()' in pane
assert 'activeContextId=id;' in pane and 'resetExample();' in pane
assert 'onUpfrontTextChanged: preview=null' in pane
for phrase in ("SIMULATION ONLY","NOT AUTHENTICATED","NOT BANK BALANCES",
               "NOTHING SAVED","NO ACCOUNTS OR HOUSEHOLDS ARE CONNECTED"):
    assert phrase in pane
for forbidden in ("Process {","FileView {","Timer {","Sqlite",
                  "ConnectionsBroker","SocialIdentityStore",
                  "FinanceBudgetReadService","FinanceTransactionWriteService",
                  "FinanceFundingWriteService"):
    assert forbidden not in pane
for forbidden in ("fetch(","XMLHttpRequest","readFile","writeFile",
                  "api.","ConnectionsBroker","SocialIdentityStore"):
    assert forbidden not in policy
assert "accountsReferenced:0" in policy
assert "bankDataUsed:false" in policy
assert "persisted:false" in policy
print("FinanceW FP1a Strategies/UI source isolation: PASS")
