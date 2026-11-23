#!/usr/bin/env python3
"""Banking M4b: existing session authority, provider activity and QML interaction gates."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
policy=(root/"widgets/FinanceBankingProviderPolicy.js").read_text()
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
accounts=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

assert 'function filterRecentActivity(projection,options)' in policy
assert 'projection.sectionKind!=="activity"' in policy
assert 'projection.connected!==false' in policy
assert 'projection.persisted!==false' in policy
assert 'projection.allAccounts.some(function(a){return a.id===accountId;})' in policy
assert 'entry.accountId===accountId' in policy
assert 'entry.description.toLowerCase().indexOf(query)>=0' in policy
assert 'entry.accountNickname.toLowerCase().indexOf(query)>=0' in policy
assert 'activity: selected.kind==="activity"?activity.slice(0,24):[]' in policy
assert 'activitySourceCount:activity.length' in policy
assert 'allAccounts:accounts' in policy
assert 'transactionCount:txCount' in policy
assert 'recentWindowCount:projection.activity.length' in policy
assert 'hasOlderEntries:projection.transactionCount>projection.activity.length' in policy

assert 'readonly property var filteredActivity: Journal.project(' in pane
assert 'property string activityDirection: "all"' in pane
assert 'property int activityAccountIndex: 0' in pane
assert 'property int entryAccountIndex: 0' in pane
assert 'property string entryDirection: "out"' in pane
assert 'signal manualEntryRequested(var draft)' in pane
assert 'manualEntryRequested({' in pane
assert 'providerId:providerId' in pane
assert 'accountId:providerAccounts[index].id' in pane
assert 'details.sectionKind!=="activity"' in pane
assert 'accountSnapshot.mode!=="manual"' in pane
assert 'function clearAfterEntry()' in pane
assert 'quickDescription.text=""' in pane
assert 'quickAmount.text=""' in pane
assert 'onLeftClicked: providerPane.requestManualEntry()' in pane
assert 'onLeftClicked: providerPane.activityDirection="all"' in pane
assert 'onLeftClicked: providerPane.activityDirection="in"' in pane
assert 'onLeftClicked: providerPane.activityDirection="out"' in pane
assert 'FILTER ACCOUNT // ALL' in pane
assert 'maximumLength: 64' in pane
assert 'SEARCH SESSION DESCRIPTION OR MANUAL ACCOUNT NICKNAME' in pane
assert 'COMPLETE CURRENT MANUAL SESSION' not in pane  # label is built by isolated journal policy
assert 'providerPane.filteredActivity.scope' in pane
assert 'PROVIDER SESSION ENTRIES // PAGE ' in pane
assert 'NO SESSION ACTIVITY MATCHES THESE FILTERS' in pane
assert 'model: providerPane.filteredActivity.ok?providerPane.filteredActivity.rows:[]' in pane
assert 'QUICK MANUAL ENTRY // UPDATES ONLY THIS SESSION // DOES NOT MOVE MONEY' in pane
assert 'ADD PROVIDER MANUAL ACTIVITY' in pane
assert 'NO VERIFIED BALANCES, PAYMENTS, CARDS, STOCKS OR LOANS // MANUAL BOOKKEEPING ONLY' in pane

assert 'function addProviderTransaction(draft)' in manager
assert 'view!=="provider" || providerMiniApp.sectionId!=="activity"' in manager
assert 'session.mode!=="manual" || !draft || draft.providerId!==selectedProviderId' in manager
assert 'a.id===draft.accountId && a.providerId===selectedProviderId' in manager
assert 'Accounts.addEntry(session,{' in manager
assert 'accountId:target.id' in manager
assert 'session=res.state;' in manager
assert 'PROVIDER MANUAL ACTIVITY SAVED IN SESSION // NO FINANCIAL ACTION' in manager
assert 'onManualEntryRequested: function(draft)' in manager
assert 'if(manager.addProviderTransaction(draft))' in manager
assert 'providerMiniApp.clearAfterEntry();' in manager
assert 'feedback: manager.message' in manager
assert 'function addTransaction()' in manager  # M3 survives
assert 'FinanceBankingProviderPane {' in manager
assert 'FinanceBankingAccountsPane {' in banking
assert 'FinanceTransferGuidePane {' in banking
assert 'FileDialog {' in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance
assert 'function addEntry(state,fields)' in accounts
assert 'state.mode!=="manual"' in accounts
assert 'findProduct(a.providerId,a.productId)' in accounts
assert 'function validState(state)' in accounts

for content in (pane,policy):
    for bad in (
        "Process {", "FileView {", "FileDialog {", "XMLHttpRequest",
        "fetch(", "Qt.openUrlExternally", "WebSocket", "console.",
        "localStorage", "FinanceServices.", "financeWrite",
        "actual-cli", "ACTUAL_PASSWORD", "ACTUAL_SYNC", "access_token",
        "client_secret", "banking_csv_reader", "onPaymentSent", "openDatabase",
        "writeFile(", "paymentExecution", "onTraderOrder",
        "Quickshell.Io", "Settings {"
    ):
        assert bad not in content,bad
print("FinanceW Banking M4b: provider activity QML, M3-only manual writer and no-provider-authority PASS")
