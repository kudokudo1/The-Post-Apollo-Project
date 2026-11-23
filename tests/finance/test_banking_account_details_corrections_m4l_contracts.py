#!/usr/bin/env python3
"""FinanceW Banking M4l: manual account details correction source/authority contracts."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
policy=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
pane=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

for phrase in (
    'function correctAccountDetails(state,fields)',
    'if(!validState(state)||state.mode!=="manual")',
    'typeof fields.accountId!=="string"',
    'var original=state.accounts.find(function(a){return a.id===fields.accountId;})',
    'original.origin!=="manual"',
    'original.providerId!==fields.expectedProviderId',
    'original.productId!==fields.expectedProductId',
    'original.nickname!==fields.expectedNickname',
    'original.openingCents!==fields.expectedOpeningCents',
    'STALE MANUAL ACCOUNT // RESELECT BEFORE CORRECTION',
    'var nickname=safeText(fields.nickname,42);',
    'a.id!==original.id',
    'a.providerId===original.providerId',
    'a.nickname.toLowerCase()===nickname.toLowerCase()',
    'NICKNAME ALREADY USED FOR THIS PROVIDER',
    'typeof fields.openingText!=="string"',
    'if(fields.openingText.trim()!=="")',
    'opening=parseCents(fields.openingText,true)',
    'OPENING BALANCE FORMAT INVALID',
    'id:original.id,providerId:original.providerId',
    'productId:original.productId,nickname:nickname',
    'openingCents:opening,origin:"manual"',
    'var accounts=state.accounts.map(function(a)',
    'return a.id===original.id?changed:a;',
    'entries:state.entries.slice(),nextId:state.nextId',
    'validState(updated)?{ok:true,state:updated,account:changed}',
    'CORRECTION EXCEEDS ACCOUNT BALANCE/AMOUNT LIMIT',
    'function addManualTransfer(state,fields)',
    'function correctManualTransfer(state,fields)',
    'function snapshot(state)',
    'combinedBalanceCents:unknown===0&&rows.length>0?total:null',
):
    assert phrase in policy,phrase

for phrase in (
    'property var accountCorrectionCandidate: null',
    'property bool accountCorrectionArmed: false',
    'onSessionChanged: {',
    'onViewChanged: {',
    'onSelectedIdChanged: {',
    'accountCorrectionCandidate=null;',
    'accountCorrectionArmed=false;',
    'function chooseAccountCorrection()',
    'function cancelAccountCorrection()',
    'function saveAccountCorrection()',
    'view!=="detail"||session.mode!=="manual"',
    'selected.origin!=="manual"',
    'accountId:selected.id,providerId:selected.providerId',
    'productId:selected.productId,nickname:selected.nickname',
    'openingCents:selected.openingCents',
    'accountCorrectionNickname.text=selected.nickname;',
    'accountCorrectionOpening.text=selected.openingCents===null?""',
    'accountCorrectionArmed=true;',
    'Accounts.correctAccountDetails(session,{',
    'expectedProviderId:original.providerId',
    'expectedProductId:original.productId',
    'expectedNickname:original.nickname',
    'expectedOpeningCents:original.openingCents',
    'nickname:accountCorrectionNickname.text',
    'openingText:accountCorrectionOpening.text',
    'session=res.state;',
    'cancelAccountCorrection();',
    'CORRECT MANUAL ACCOUNT LABEL / OPENING ESTIMATE',
    'ACCOUNT ID, PROVIDER, PRODUCT AND EXISTING TRANSACTIONS STAY LOCKED',
    'CORRECT ACCOUNT NICKNAME // MAX 42',
    'CORRECT OPENING USD ESTIMATE // BLANK MEANS UNKNOWN, ZERO IS 0.00',
    'OPENING ESTIMATE IS USER-ENTERED // NOT A BANK STATEMENT OR NEW TRANSACTION',
    'id: accountCorrectionNickname',
    'id: accountCorrectionOpening',
    'maximumLength: 42',
    'onTextChanged: manager.accountCorrectionArmed=false',
    'SAVE ACCOUNT CORRECTION // TWO CLICKS',
    'CONFIRM MANUAL ACCOUNT CORRECTION',
    'CANCEL MANUAL ACCOUNT CORRECTION',
    'onLeftClicked: manager.saveAccountCorrection()',
    'onLeftClicked: manager.cancelAccountCorrection()',
    'function removeCurrent()',
    'function addTransaction()',
):
    assert phrase in pane,phrase

assert pane.count("id: accountCorrectionNickname")==1
assert pane.count("id: accountCorrectionOpening")==1
assert pane.count('onTextChanged: manager.accountCorrectionArmed=false')==2
assert "Accounts.correctEntry(session,draft)" in pane
assert "Accounts.deleteEntry(session,draft)" in pane
assert "Accounts.removeManualTransfer(session,row)" in pane
assert 'FinanceBankingAccountsPane {' in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance
assert 'transferId:e.transferId||""' in journal
assert 'CORRECT / REMOVE THIS MANUAL ENTRY' in provider
for source in (policy,pane):
    for forbidden in (
        "Process {","FileView {","FileDialog {","XMLHttpRequest",
        "fetch(","WebSocket","localStorage","FinanceServices.",
        "financeWrite","actual-cli","ACTUAL_PASSWORD","ACTUAL_SYNC",
        "access_token","client_secret","onPaymentSent","openDatabase",
        "writeFile(","paymentExecution","onTraderOrder","Quickshell.Io",
        "Qt.openUrlExternally"
    ):
        assert forbidden not in source,forbidden
print("Banking M4l: stale-safe account label/opening correction, two-click native UI, no account/provider mutation or financial authority PASS")
