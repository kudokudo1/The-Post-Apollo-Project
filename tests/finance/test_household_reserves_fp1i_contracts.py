#!/usr/bin/env python3
"""FP1i read-only reserve estimate, UI isolation and no-storage contracts."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
policy=(root/"widgets/FinanceHouseholdReservePolicy.js").read_text()
timeline=(root/"widgets/FinanceHouseholdTimelinePane.qml").read_text()
month=(root/"widgets/FinanceHouseholdTimelinePolicy.js").read_text()
store=(root/"scripts/finance/household_schedule_store.py").read_text()
# FP1j extends the optional parameter; FP1i's 3-argument runtime behavior
# remains tested with a real JS call and equal-output assertion.
assert ('function annotate(rows,schedules,projection)' in policy or
        'function annotate(rows,schedules,projection,marginPercent)' in policy)
assert 'function depositFor(fund,month)' in policy
assert 'source:"LOCAL_MANUAL_RESERVE_ESTIMATE"' in policy
assert "notAvailableCash:true" in policy
assert "actualTransfersMade:false" in policy
assert "simulatedStartingReserveCents:0" in policy
assert 'reservePolicy:"EARMARK_ONLY_NO_DUPLICATE_EXPENSE"' in policy
assert "source.changeCents-added+applied" in policy
assert "cumulativeAvailable!==source.cumulativeChangeCents-held" in policy
assert "byExpense.get(fund.expenseId)||0" in policy
assert 'Math.floor(fund.amountCents/fund.intervalMonths)' in policy
assert "if(offset<1-fund.intervalMonths)return 0;" in policy
assert 'idx(projection.startMonth)===null' in policy
assert 'projection.bankVerified!==false' in policy
assert 'import "FinanceHouseholdReservePolicy.js" as Reserves' in timeline
assert ('Reserves.annotate(sourceRows,scheduleRows,projection)' in timeline or
        'Reserves.annotate(sourceRows,scheduleRows,projection,reserveMarginPercent)' in timeline)
assert "timeline.reserves.byMonth[modelData.month]" in timeline
assert "SINKING FUNDS" in timeline
assert "NOT AN EXTRA EXPENSE OR A BANK TRANSFER" in timeline
assert "PERIODIC BILL EARMARK" in timeline
assert "CUMULATIVE UNRESERVED CHANGE" in timeline
assert "MODEL SHORTFALL" in timeline
assert "UNRESERVED CHANGE IS NOT SPENDABLE CASH" in timeline
assert "function project(rows,schedules,startMonth,horizonMonths,contextId)" in month
assert 'row.kind==="bill_cadence"' in month
assert "os.O_NOFOLLOW" in store
for forbidden in ("Qt.openUrlExternally","Process {","FileView {",
                  "XMLHttpRequest","fetch(","ConnectionsBroker",
                  "FinanceTransactionWriteService","FinanceFundingWriteService",
                  "SocialIdentityStore","writeFile","readFile"):
    assert forbidden not in policy, forbidden
for forbidden in ("FinanceTransactionWriteService","FinanceFundingWriteService",
                  "ConnectionsBroker","SocialIdentityStore"):
    assert forbidden not in timeline, forbidden
print("FinanceW FP1i sinking funds UI and policy isolation: PASS")
