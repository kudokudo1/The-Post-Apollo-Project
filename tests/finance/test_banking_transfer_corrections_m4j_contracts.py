#!/usr/bin/env python3
"""Banking M4j: atomic transfer pair correction and native UI authority."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
policy=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
accounts=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
shared=(root/"widgets/PostApolloDateStepper.qml").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

for phrase in (
    "function correctManualTransfer(state,fields)",
    'if(!validState(state)||state.mode!=="manual")',
    'typeof fields.transferId!=="string"',
    "list.rows.find(function(p){return p.transferId===fields.transferId;})",
    "selected.fromAccountId!==fields.fromAccountId",
    "selected.toAccountId!==fields.toAccountId",
    "selected.date!==fields.expectedDate",
    "selected.description!==fields.expectedDescription",
    "selected.amountCents!==fields.expectedAmountCents",
    "STALE MANUAL TRANSFER // RESELECT BEFORE CORRECTION",
    "dateValid(fields.date)",
    "parseCents(fields.amountText,false)",
    'fields.description===""?"MANUAL TRANSFER"',
    "var changedCount=0,entries=state.entries.map(function(e)",
    "if(e.transferId!==selected.transferId)return e;",
    "changedCount++;",
    "id:e.id,accountId:e.accountId",
    'amountCents:e.transferSide==="out"?-cents:cents',
    'origin:"manual",transferId:e.transferId,transferSide:e.transferSide',
    "if(changedCount!==2)",
    "entries:entries,nextId:state.nextId",
    "validState(updated)?{ok:true,state:updated,corrected:{",
    "CORRECTION EXCEEDS SESSION AMOUNT LIMIT",
    "function removeManualTransfer(state,fields)",
    "function transferPairs(state)",
    "if(entry.transferId)",
):
    assert phrase in policy,phrase

# The new policy accepts normal numeric M3 transfer IDs, rather than literal
# escaped \d text. Keep the existing pair validator as the canonical identity gate.
assert r"!/^transfer-[1-9]\d*$/.test(fields.transferId)" in policy

for phrase in (
    "property var transferCorrectionCandidate: null",
    "property bool transferCorrectionArmed: false",
    'property string transferCorrectionDate: ""',
    "onTransferCorrectionDateChanged: transferCorrectionArmed=false",
    "function chooseManualTransferCorrection(row)",
    "function cancelManualTransferCorrection()",
    "function saveManualTransferCorrection()",
    "pairedTransfers.rows.some(function(p)",
    "transferCorrectionCandidate={",
    "transferCorrectionAmount.text=(row.amountCents/100).toFixed(2)",
    "transferCorrectionDescription.text=row.description",
    'view!=="overview"||session.mode!=="manual"',
    "transferCorrectionArmed=true;",
    "transferCorrectionArmed=false;",
    "Accounts.correctManualTransfer(session,{",
    "fromAccountId:original.fromAccountId",
    "toAccountId:original.toAccountId",
    "expectedDate:original.date",
    "expectedDescription:original.description",
    "expectedAmountCents:original.amountCents",
    "date:transferCorrectionDate",
    "amountText:transferCorrectionAmount.text",
    "description:transferCorrectionDescription.text",
    "session=result.state;",
    "cancelManualTransferCorrection();",
    "CORRECT PAIRED MANUAL TRANSFER // BOTH LEGS // ACCOUNT ENDPOINTS LOCKED",
    "CORRECT DATE // MONTH / DAY / YEAR",
    'dateValue: manager.transferCorrectionDate',
    'allowClear: false',
    'id: transferCorrectionAmount',
    'id: transferCorrectionDescription',
    'onTextChanged: manager.transferCorrectionArmed=false',
    "SAVE PAIRED MANUAL TRANSFER CORRECTION // TWO CLICKS",
    "CONFIRM CORRECT BOTH TRANSFER ENTRIES",
    "CANCEL PAIRED TRANSFER CORRECTION",
    "CORRECT BOTH MANUAL TRANSFER ENTRIES",
    "onLeftClicked: manager.chooseManualTransferCorrection(modelData)",
    "onLeftClicked: manager.saveManualTransferCorrection()",
    "onLeftClicked: manager.cancelManualTransferCorrection()",
    "manager.transferCorrectionCandidate!==null",
    "BOTH MANUAL TRANSFER LEGS CORRECTED // NO BANK ACTION",
    "function removeManualTransferPair(row)",
):
    assert phrase in accounts,phrase
assert accounts.count('id: transferCorrectionAmount')==1
assert accounts.count('id: transferCorrectionDescription')==1
assert accounts.count('PostApolloDateStepper {')==2
assert "TaskFields.TaskDateSegment" in shared
assert 'FinanceBankingAccountsPane {' in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance
assert "matchedTransferCount:matchedTransferCount" in journal
assert 'PAIRED MANUAL TRANSFER // NOT INCOME OR SPENDING' in provider

for source in (policy,accounts):
    for forbidden in (
        "Process {","FileDialog {","FileView {","XMLHttpRequest",
        "fetch(","WebSocket","localStorage","FinanceServices.","financeWrite",
        "actual-cli","ACTUAL_PASSWORD","ACTUAL_SYNC","access_token",
        "client_secret","onPaymentSent","openDatabase","writeFile(",
        "paymentExecution","onTraderOrder","Quickshell.Io"
    ):
        assert forbidden not in source,forbidden
assert "Qt.openUrlExternally" not in accounts
print("Banking M4j: immutable pair IDs, stale-original correction gates, two-click editor, Tasks date component and no-payment source isolation PASS")
