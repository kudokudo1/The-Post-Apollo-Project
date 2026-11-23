#!/usr/bin/env python3
"""Banking M4e: full-session read-only journal & pagination interaction contracts."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
m3policy=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
existing=(root/"widgets/FinanceBankingProviderPolicy.js").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

for key in (
    "var PAGE_SIZE=20;", "var MAX_ENTRIES=300;", "var MAX_ACCOUNTS=12;",
    'function project(projection,session,options)',
    'projection.sectionKind!=="activity"',
    'projection.connected!==false||projection.persisted!==false',
    'session.entries.length>MAX_ENTRIES',
    'projection.dataLabel!==(',
    'projection.allAccounts.length',
    'totalProviderAccounts!==projection.allAccounts.length',
    'view.providerId!==projection.providerId',
    'view.nickname!==providerAccounts[view.id].nickname',
    'Object.prototype.hasOwnProperty.call(known,e.accountId)',
    'if(!owned)continue;',
    'providerCount!==projection.transactionCount',
    'rows.sort(compareEntries);',
    'pageCount=Math.max(1,Math.ceil(matchCount/PAGE_SIZE))',
    'pageIndex=Math.min(requested,pageCount-1)',
    'rows.slice(start,start+PAGE_SIZE)',
    '"COMPLETE FICTIONAL DEMO SESSION"',
    '"COMPLETE CURRENT MANUAL SESSION"',
    'connected:false,persisted:false'
):
    assert key in journal,key

for key in (
    'FinanceBankingSessionJournalPolicy.js',
    'property var manualSession: ({mode:"empty",accounts:[],entries:[]})',
    'property int activityPageIndex: 0',
    'readonly property var filteredActivity: Journal.project(',
    'details,manualSession,{direction:activityDirection,',
    'onActivityDirectionChanged: {',
    'onActivityAccountIndexChanged: {',
    'onManualSessionChanged: {',
    'onTextChanged: {',
    'providerPane.filteredActivity.totalMatches',
    'providerPane.filteredActivity.providerSessionCount',
    'providerPane.filteredActivity.pageCount',
    'providerPane.filteredActivity.from',
    'providerPane.filteredActivity.to',
    'UP TO 300 SESSION ENTRIES',
    'SEARCH SESSION DESCRIPTION OR MANUAL ACCOUNT NICKNAME',
    'NO SESSION ACTIVITY MATCHES THESE FILTERS',
    'model: providerPane.filteredActivity.ok?providerPane.filteredActivity.rows:[]',
    'label: "PREVIOUS PAGE"',
    'label: "NEXT PAGE"',
    'providerPane.filteredActivity.pageIndex>0',
    '<providerPane.filteredActivity.pageCount',
    'providerPane.returnToTopRequested();',
):
    assert key in provider,key
assert 'manualSession: manager.session' in manager
assert 'accountSnapshot: manager.review' in manager
assert 'function addProviderTransaction(draft)' in manager
assert 'Accounts.addEntry(session,{' in manager
assert 'function validState(state)' in m3policy
assert 'FinanceBankingAccountsPane {' in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance
# Legacy short previews remain for HOME and PRODUCT, separate from full
# ACTIVITY session journal, so the new feature doesn't falsify the old UI.
assert 'visibleRecent:preview.slice(0,4)' in existing
assert 'activity: selected.kind==="activity"?activity.slice(0,24):[]' in existing
assert 'OPEN ACCOUNT DETAILS' in provider
assert 'FinanceBankingOfficialHandoff {' in provider

for source in (journal,provider):
    for forbidden in (
        'Process {','FileDialog {','FileView {','XMLHttpRequest','fetch(',
        'WebSocket','localStorage','FinanceServices.','financeWrite',
        'actual-cli','ACTUAL_PASSWORD','ACTUAL_SYNC','access_token',
        'client_secret','onPaymentSent','openDatabase','writeFile(',
        'paymentExecution','onTraderOrder','Quickshell.Io','Settings {'
    ):
        assert forbidden not in source,forbidden
assert 'Qt.openUrlExternally' not in journal
assert 'Qt.openUrlExternally' not in provider
print("Banking M4e: complete manual-session journal, bounded paging, owner gating, prior Banking UI and no financial authority PASS")
