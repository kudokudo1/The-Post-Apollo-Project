#!/usr/bin/env python3
"""FinanceW D16 income preview is read-only and source-bound."""
from pathlib import Path
base=Path(__file__).resolve().parents[2]
src=(base/"scripts/finance/actual_readonly.mjs").read_text()
policy=(base/"scripts/finance/income_categorization_preview.mjs").read_text()
bridge=(base/"services/finance/FinanceBudgetReadService.qml").read_text()
menu=(base/"widgets/FinanceW.qml").read_text()
pane=(base/"widgets/FinanceIncomeCategorizationPane.qml").read_text()
assert 'incomeReview: summarizeIncomeCandidates({month,budget,accounts,transactionSets})' in src
assert 'payload.incomeReview.month !== payload.month' in bridge
assert 'payload.incomeReview.candidateCount!==payload.funding.positiveUncategorizedCount' in bridge
assert 'payload.incomeReview.candidates.length>12' in bridge
assert 'payload.incomeReview.truncated !== (payload.incomeReview.candidateCount>12)' in bridge
assert 'id: reviewIncoming' in menu
assert 'label: incomeCategoryPane.expanded' in menu
assert 'id: incomeCategoryPane' in menu
assert 'snapshot: financeBudget.snapshot' in menu
assert 'FinanceIncomeCategorizationPane {' in menu
assert 'onSnapshotChanged: clear()' in pane
assert 'function openReview()' in pane
assert 'function selectCandidate(item)' in pane
assert 'function previewCategory(item)' in pane
assert 'review.month===snapshot.month' in pane
assert 'proposalReady' in pane
assert 'PREVIEW ONLY // NO WRITE // TO BUDGET NOT RECALCULATED' in pane
assert 'POSITIVE IS NOT PROOF OF INCOME' in pane
assert 'REVIEW REMAINING ITEMS IN ACTUAL' in pane
assert 'UNCATEGORIZED → ' in pane
assert 'const maxCandidates=12' in policy
assert 'const maxCategories=24' in policy
assert 'categorizationVerified:false' in policy
assert 'toBudgetAfterCents:null' in policy
assert 'writeAllowed:false' in policy
for content in (pane,policy):
    for forbidden in ("setBudgetAmount(","updateTransaction(","addTransactions(",
                      "allocation-writes-enabled","transaction-writes-enabled",
                      "QUICK_WRITE","FINANCEW_ALLOCATION_RESULT"):
        assert forbidden not in content,forbidden
assert 'Process {' not in pane
assert 'saveRequested' not in pane
assert 'Qt.openUrlExternally' not in pane
print("FinanceW D16 read-only income category preview contracts: PASS")
