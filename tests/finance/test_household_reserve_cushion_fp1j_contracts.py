#!/usr/bin/env python3
"""FinanceW FP1j manual reserve scenario controls and IO isolation."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
reserve=(root/"widgets/FinanceHouseholdReservePolicy.js").read_text()
ui=(root/"widgets/FinanceHouseholdTimelinePane.qml").read_text()
timeline=(root/"widgets/FinanceHouseholdTimelinePolicy.js").read_text()
schedule=(root/"services/finance/FinanceHouseholdScheduleStore.qml").read_text()
store=(root/"scripts/finance/household_schedule_store.py").read_text()

assert "function annotate(rows,schedules,projection,marginPercent)" in reserve
assert "if(marginPercent===undefined)marginPercent=100" in reserve
assert "[100,110,125].indexOf(marginPercent)<0" in reserve
assert "return refuse(\"INVALID_RESERVE_CUSHION\")" in reserve
assert "fund.bufferTargetCents-fund.bufferHeldCents" in reserve
assert "var bufferAdded=Math.min(bufferPlan" in reserve
assert "fund.coreHeldCents+=baseDeposit" in reserve
assert "fund.bufferHeldCents+=bufferAdded" in reserve
assert "var used=coreUsed+bufferUsed" in reserve
assert "source.changeCents-added+applied" in reserve
assert "cumulativeAvailable!==source.cumulativeChangeCents-held" in reserve
assert "reserveMarginPercent:marginPercent" in reserve
assert "scenarioOnly:true,persisted:false" in reserve
assert "actualTransfersMade:false" in reserve
assert "startingReserveKnown:false" in reserve

assert "property int reserveMarginPercent: 100" in ui
# FP1k extends context switching with a persisted local preference read.
# The immediate fail-safe reset remains 100 until the matching result loads.
assert ('onContextIdChanged: reserveMarginPercent=100' in ui or
        ('onContextIdChanged: {' in ui and
         'reserveMarginPercent=100;' in ui and
         'armedPreferenceReset=false;' in ui))
assert "Reserves.annotate(sourceRows,scheduleRows,projection,reserveMarginPercent)" in ui
assert "QUARTERLY/ANNUAL" in ui
for token in ("100% // BASE","110% // +10%","125% // +25%",
              'onLeftClicked: timeline.reserveMarginPercent=modelData.percent',
              "NOT SAVED","BUFFER ADDED","BUFFER HELD",
              "EXTRA BUFFER IS CAPPED","UNRESERVED CHANGE IS NOT SPENDABLE CASH"):
    assert token in ui,token

assert "function project(rows,schedules,startMonth,horizonMonths,contextId)" in timeline
assert "doc.version===4" in schedule
assert 'doc["version"] not in (1, 2, 3, 4)' in store

# Scenario work must not touch separate finance, identity or banking writers.
for source in (reserve,ui):
    for forbidden in ("FinanceTransactionWriteService","FinanceFundingWriteService",
                      "ConnectionsBroker","SocialIdentityStore",
                      "FinanceHouseholdScheduleStore {","XMLHttpRequest",
                      "fetch(","Qt.openUrlExternally","FileView {","Process {"):
        assert forbidden not in source,forbidden
for forbidden in ("fs.","os.","localStorage","writeFile","readFile",
                  "ACTUAL_PASSWORD","authorizationToken"):
    assert forbidden not in reserve,forbidden
print("FinanceW FP1j reserve-cushion scenario and source isolation: PASS")
