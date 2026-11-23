#!/usr/bin/env python3
"""FinanceW M3: native Banking account manager source and authority boundaries."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
view=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
policy=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
root_qml=(root/"widgets/FinanceW.qml").read_text()
import_policy=(root/"widgets/FinanceBankingImportPolicy.js").read_text()
reader=(root/"scripts/finance/banking_csv_reader.py").read_text()

assert 'property string selectedTool: "accounts"' in banking
assert banking.index('label: "ACCOUNTS"')<banking.index('label: "TRANSFERS"')<banking.index('label: "IMPORT"')
assert "FinanceBankingAccountsPane {" in banking
assert 'visible: banking.selectedTool==="accounts"' in banking
assert 'active: banking.active && banking.selectedTool==="accounts"' in banking
assert 'height: visible ? implicitHeight : 0' in banking
assert 'onReturnToTopRequested: bankingScroll.flickable.contentY=0' in banking
assert "FinanceTransferGuidePane {" in banking
assert "BankingPolicy.parseCsv(" in banking
assert "FileDialog {" in banking
assert "Process {" in banking
assert root_qml.index('id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"')>=0
assert 'selectedMainMode === "banking"' in root_qml

assert 'FinanceBankingAccountsPolicy.js' in view
assert 'property var session: Accounts.emptyState()' in view
assert 'property string view: "overview"' in view
assert 'function createAccount()' in view
assert 'function addTransaction()' in view
assert 'function undoLast()' in view
assert 'function removeCurrent()' in view
assert 'function loadDemo()' in view
assert 'function clearDemo()' in view
assert 'signal returnToTopRequested()' in view
assert 'Accounts.addAccount(session,' in view
assert 'Accounts.addEntry(session,' in view
assert 'Accounts.undoLastEntry(session)' in view
assert 'Accounts.removeEmptyAccount(session,selectedId)' in view
assert 'Accounts.sampleDemo()' in view
assert 'Accounts.snapshot(session)' in view
assert 'OPEN ACCOUNT DETAILS' in view
assert 'BACK TO ALL ACCOUNTS' in view
assert 'ADD MANUAL ACCOUNT' in view
assert 'MONEY OUT' in view and 'MONEY IN' in view
assert 'CREATE MANUAL ACCOUNT' in view
assert 'ADD TO MANUAL ACTIVITY' in view
assert 'CONFIRM DELETE EMPTY ACCOUNT' in view
assert 'UNDO LAST MANUAL TRANSACTION' in view
assert 'LOAD FICTIONAL DEMO' in view
assert 'CLICK CLEAR DEMO AGAIN' in view
assert 'OPENING BALANCE USD // OPTIONAL // BLANK MEANS UNKNOWN' in view
assert 'BALANCE UNKNOWN' in view
assert 'FICTIONAL COMBINED TOTAL' in view
assert 'NOT SAVED' in view and 'NO BANK CONNECTION' in view
assert view.count("ActionButton {") >= 10
assert view.count("TextInput {") == 7  # original five + M4i paired-transfer amount and description
assert 'id: manualTransferAmount' in view
assert 'id: manualTransferDescription' in view
assert "Text.PlainText" in view
assert "Qt.formatDate(new Date()" in view
assert "Component.onCompleted:" not in view
assert "anchors.fill: parent" in view

assert 'var MAX_ACCOUNTS = 12' in policy
assert 'var MAX_ENTRIES = 300' in policy
assert 'var MAX_CENTS = 999999999' in policy
assert 'mode:"empty",accounts:[],entries:[],nextId:1' in policy
assert 'origin:"manual"' in policy and 'origin:"demo"' in policy
assert 'connected:false,persisted:false' in policy
assert 'combinedBalanceCents:unknown===0&&rows.length>0?total:null' in policy
assert "function validState(state)" in policy
assert "function addAccount(state,fields)" in policy
assert "function addEntry(state,fields)" in policy
assert "function undoLastEntry(state)" in policy
assert "function removeEmptyAccount(state,accountId)" in policy
assert "function sampleDemo()" in policy
assert "findProduct(a.providerId,a.productId)" in policy
assert 'a.openingCents===null' in policy
assert 'state.mode==="demo"' in policy
assert 'state.mode!=="manual"' in policy
assert "return {ok:true,state:updated" in policy

# The new account manager is deliberately independent from external source
# readers and from user identity/permissions/payment execution; no silent
# per-person profile switching, privileged writers, persistence or web calls.
for content in (view,policy):
    for forbidden in (
        "Process {", "FileView {", "FileDialog {", "XMLHttpRequest",
        "fetch(", "Qt.openUrlExternally", "WebSocket", "console.",
        "Qt.labs.settings", "LocalStorage", "localStorage",
        "FinanceServices.", "financeWrite", "actual-cli",
        "ACTUAL_PASSWORD", "ACTUAL_SYNC", "access_token", "client_secret",
        "secret_key", "banking_csv_reader", "onPaymentSent", "openDatabase",
        "writeFile(", "paymentExecution", "onTraderOrder"
    ):
        assert forbidden not in content, forbidden
assert "Process {" not in policy
assert "FinanceBankingAccountsPolicy.js" not in import_policy
assert "FinanceBankingAccountsPolicy.js" not in reader
assert "FinanceBankingAccountsPane" not in root_qml
print("FinanceW Banking M3: local account pane, source isolation, menu/nav continuity PASS")
