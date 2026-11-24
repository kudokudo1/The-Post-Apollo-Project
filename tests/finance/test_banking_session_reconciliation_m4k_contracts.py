#!/usr/bin/env python3
"""Banking M4k: session-level paired/unlinked cash movements, no bank authority."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
policy=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
pane=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

for item in (
    "if(!validState(state))return resultError(\"INVALID SESSION STATE\");",
    "var transferIds=Object.create(null),transferLegCount=0;",
    "var transferInCents=0,transferOutCents=0;",
    "var unlinkedCount=0,unlinkedInCents=0,unlinkedOutCents=0;",
    "if(e.transferId) {",
    "transferIds[e.transferId]=true;",
    "transferLegCount++;",
    "transferOutCents+=-e.amountCents;",
    "transferInCents+=e.amountCents;",
    "unlinkedCount++;",
    "unlinkedOutCents+=-e.amountCents;",
    "unlinkedInCents+=e.amountCents;",
    "var transferPairCount=Object.keys(transferIds).length;",
    "transferLegCount!==transferPairCount*2",
    "transferInCents!==transferOutCents",
    "transferInCents+unlinkedInCents!==credits",
    "transferOutCents+unlinkedOutCents!==debits",
    "transferLegCount+unlinkedCount!==state.entries.length",
    "transferPairCount:transferPairCount,",
    "transferLegCount:transferLegCount,",
    "transferVolumeCents:transferInCents,",
    "transferNetCents:transferInCents-transferOutCents,",
    "unlinkedCount:unlinkedCount,",
    "unlinkedInCents:unlinkedInCents,",
    "unlinkedOutCents:unlinkedOutCents,",
    "unlinkedNetCents:unlinkedInCents-unlinkedOutCents,",
    'movementScope:"ALL CURRENT MANUAL/DEMO SESSION ACCOUNTS // NOT VERIFIED INCOME OR SPENDING"',
    "combinedBalanceCents:unknown===0&&rows.length>0?total:null",
    "connected:false,persisted:false",
    "function correctManualTransfer(state,fields)",
    "function removeManualTransfer(state,fields)",
):
    assert item in policy,item

for item in (
    '"SESSION TRANSFER RECONCILIATION // ALL MANUAL ACCOUNTS"',
    "manager.review.transferPairCount",
    "manager.review.transferLegCount",
    "manager.review.transferVolumeCents",
    "manager.review.transferNetCents",
    "manager.review.unlinkedCount",
    "manager.review.unlinkedInCents",
    "manager.review.unlinkedOutCents",
    "manager.review.unlinkedNetCents",
    "DECLARED TRANSFERS CANCEL ONLY ACROSS THE COMPLETE SESSION",
    "UNLINKED IS NOT VERIFIED INCOME OR SPENDING",
    'MANUAL USD ACCOUNTS // NO BANK CONNECTION // CHANGES NOT SAVED AUTOMATICALLY',
    'Accounts.snapshot(session)',
    "Accounts.addManualTransfer(session,{",
    "Accounts.correctManualTransfer(session,{",
    "Accounts.removeManualTransfer(session,row)",
):
    assert item in pane,item

assert "matchedTransferCount:matchedTransferCount" in journal
assert "matchedUnlinkedCount:matchCount-matchedTransferCount" in journal
assert 'DECLARED TRANSFERS ARE NOT NEW INCOME OR SPENDING' in provider
assert 'FinanceBankingAccountsPane {' in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance
assert pane.count("SESSION TRANSFER RECONCILIATION // ALL MANUAL ACCOUNTS")==1
for source in (policy,pane):
    for unsafe in (
        "Process {","FileDialog {","FileView {","XMLHttpRequest",
        "fetch(","WebSocket","localStorage","FinanceServices.","financeWrite",
        "actual-cli","ACTUAL_PASSWORD","ACTUAL_SYNC","access_token",
        "client_secret","onPaymentSent","openDatabase","writeFile(",
        "paymentExecution","onTraderOrder","Quickshell.Io"
    ):
        assert unsafe not in source,unsafe
assert "Qt.openUrlExternally" not in pane
print("Banking M4k: session-wide transfer cancellation, unlinked totals, unknown balance guard and no provider authorization PASS")
