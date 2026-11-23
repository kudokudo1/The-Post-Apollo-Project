#!/usr/bin/env python3
"""Banking M4i: paired manual transfer writer, pair removal and UI authority."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
a=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
pane=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
shared=(root/"widgets/PostApolloDateStepper.qml").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

for part in (
    "function addManualTransfer(state,fields)",
    "function transferPairs(state)",
    "function removeManualTransfer(state,fields)",
    'state.mode!=="manual"',
    'fields.fromAccountId===fields.toAccountId',
    "state.entries.length>MAX_ENTRIES-2",
    "fields.amountText,false",
    'transferId:pairId,transferSide:"out"',
    'transferId:pairId,transferSide:"in"',
    "amountCents:-cents",
    "amountCents:cents",
    "nextId:state.nextId+2",
    "validState(updated)?{ok:true,state:updated,transfer:",
    "pair.in.accountId===pair.out.accountId",
    "pair.in.date!==pair.out.date",
    "pair.in.description!==pair.out.description",
    "pair.in.amountCents!==-pair.out.amountCents",
    "return resultError(\"PAIRED TRANSFER // REMOVE BOTH FROM BANKING OVERVIEW\")",
    "entries=entries.slice(0,-1);",
    "return validState(updated)?{ok:true,state:updated,removed:selected}",
    "nextId:state.nextId};",
    'entry.transferId)'
):
    assert part in a,part

for part in (
    "function recordManualTransfer()",
    "function removeManualTransferPair(row)",
    'view!=="overview"||session.mode!=="manual"',
    "Accounts.addManualTransfer(session,{",
    "Accounts.removeManualTransfer(session,row)",
    "transferRemoveArmedId=row.transferId;",
    'message="CLICK AGAIN TO REMOVE BOTH MANUAL TRANSFER ENTRIES"',
    'manager.manualTransferArmed=false',
    'manualTransferOpen',
    'property string manualTransferDate: ""',
    'manager.manualTransferDate=Qt.formatDate(new Date(),"yyyy-MM-dd");',
    'manager.review.accounts[manager.transferFromIndex].providerName',
    'manager.review.accounts[manager.transferToIndex].providerName',
    'modelData.fromProviderId.toUpperCase()',
    'modelData.toProviderId.toUpperCase()',
    'PostApolloDateStepper {',
    'dateValue: manager.manualTransferDate',
    'id: manualTransferAmount',
    'id: manualTransferDescription',
    'fromAccountId:from?from.id:""',
    'toAccountId:to?to.id:""',
    'RECORD PAIRED MANUAL TRANSFER // TWO CLICKS',
    'CONFIRM RECORD TWO MANUAL ENTRIES',
    'RECORDED MANUAL TRANSFER PAIRS // REMOVE BOTH SIDES TOGETHER',
    'REMOVE PAIRED MANUAL TRANSFER // TWO CLICKS',
    'CONFIRM REMOVE BOTH MANUAL TRANSFER ENTRIES',
    'MANUAL SESSION BOOKKEEPING ONLY // TWO LINKED ENTRIES // NEVER SENDS MONEY'
):
    assert part in pane,part

for part in (
    "var pairs=Object.create(null)",
    "DUPLICATE MANUAL TRANSFER LEG",
    "INCOMPLETE MANUAL TRANSFER PAIR",
    "transferId:e.transferId||\"\"",
    "transferSide:e.transferSide||\"\"",
    "providerCount!==projection.transactionCount"
):
    assert part in journal,part
for part in (
    'visible: modelData.transferId!==""',
    'PAIRED MANUAL TRANSFER // NOT INCOME OR SPENDING',
    '&&modelData.transferId===""',
    '||row.transferId)return false;',
    'CORRECT / REMOVE THIS MANUAL ENTRY'
):
    assert part in provider,part

assert "TaskFields.TaskDateSegment" in shared
assert 'FinanceBankingAccountsPane {' in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance

for src in (a,pane,provider,journal,shared):
    for forbidden in (
        "Process {","FileView {","FileDialog {","XMLHttpRequest",
        "fetch(","WebSocket","localStorage","FinanceServices.","financeWrite",
        "actual-cli","ACTUAL_PASSWORD","ACTUAL_SYNC","access_token",
        "client_secret","onPaymentSent","openDatabase","writeFile(",
        "paymentExecution","onTraderOrder","Quickshell.Io"
    ):
        assert forbidden not in src,forbidden
assert "Qt.openUrlExternally" not in pane
assert "Qt.openUrlExternally" not in journal
print("Banking M4i: atomic two-legged manual transfer, single-writer UI, fail-closed pair removal and no real payment authority PASS")
