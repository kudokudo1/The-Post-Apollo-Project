#!/usr/bin/env python3
"""D14 funding review: source-derived, bounded and non-mutating."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
ui=(root/"widgets/FinanceW.qml").read_text()
snapshot=(root/"scripts/finance/actual_readonly.mjs").read_text()
funding=(root/"scripts/finance/funding_reconciliation.mjs").read_text()
bridge=(root/"services/finance/FinanceBudgetReadService.qml").read_text()
assert 'summarizeFunding' in snapshot
assert 'funding: summarizeFunding({month,budget,accounts,balances,transactionSets})' in snapshot
assert 'payload.funding.month !== payload.month' in bridge
assert 'payload.funding.toBudgetCents !== payload.toBudgetCents' in bridge
assert 'payload.funding.completeness !== "monthly-review-only"' in bridge
assert 'payload.funding.openingBalancesVerified !== false' in bridge
assert 'Number.isSafeInteger(payload.funding.positiveUncategorizedCents)' in bridge
assert 'property bool fundingReviewOpen: false' in ui
assert 'onSnapshotChanged: root.fundingReviewOpen = false' in ui
assert 'id: reviewFunding' in ui
assert 'label: root.fundingReviewOpen ? "HIDE FUNDING REVIEW" : "REVIEW FUNDING"' in ui
assert 'onLeftClicked: root.fundingReviewOpen = !root.fundingReviewOpen' in ui
assert 'visible: root.fundingReviewOpen && financeBudget.state === "ready"' in ui
assert 'financeBudget.snapshot.funding.incomeCategoryActivityCents' in ui
assert 'financeBudget.snapshot.funding.reportedIncomeCents' in ui
assert 'NOT REPORTED BY ACTUAL' in ui
assert 'MONTHLY INCOME (ACTUAL)' in ui
assert 'financeBudget.snapshot.funding.positiveUncategorizedCount' in ui
assert 'financeBudget.snapshot.funding.positiveUncategorizedCents' in ui
assert 'OPENING BALANCES // NOT VERIFIED FROM THIS MONTH' in ui
assert 'ACCOUNT BALANCE IS NOT THE SAME AS TO BUDGET' in ui
assert 'THEY MAY BE REFUNDS OR TRANSFERS, NOT INCOME' in ui
assert 'category.spent' in funding
assert 'if(row.category || row.category_id)continue;' in funding
assert 'openingBalancesVerified:false' in funding
assert 'incomeCategoryDetailAvailable=false' in funding
assert 'incomeCategoryActivityCents:incomeCategoryDetailAvailable' in funding
assert 'completeness:"monthly-review-only"' in funding
for bad in ('Process {','setBudgetAmount(', 'createAccount(', 'addTransactions(', 'writeFile(', 'exec('):
    assert bad not in funding,bad
print("FinanceW D14 funding read-only source/UI contracts: PASS")
