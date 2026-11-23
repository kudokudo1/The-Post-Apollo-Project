#!/usr/bin/env python3
"""Banking M4g: optional date-range activity UI and read-only totals contracts."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
accounts=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

for phrase in (
    'fromDate=opts.fromDate===undefined?"":opts.fromDate',
    'toDate=opts.toDate===undefined?"":opts.toDate',
    'typeof fromDate!=="string"||typeof toDate!=="string"',
    '(fromDate!==""&&!safeDate(fromDate))',
    '(toDate!==""&&!safeDate(toDate))',
    '(fromDate!==""&&toDate!==""&&fromDate>toDate)',
    'INVALID DATE RANGE // USE YYYY-MM-DD AND FROM <= TO',
    'if(fromDate!==""&&e.date<fromDate)continue;',
    'if(toDate!==""&&e.date>toDate)continue;',
    'if(e.amountCents>0)matchedInCents+=e.amountCents;',
    'else matchedOutCents+=-e.amountCents;',
    'matchedInCents:matchedInCents,matchedOutCents:matchedOutCents',
    'matchedNetCents:matchedInCents-matchedOutCents',
    'totalsScope:"FILTERED SESSION ENTRIES // NOT VERIFIED INCOME OR SPENDING"',
    'fromDate:fromDate,toDate:toDate',
    'rows.slice(start,start+PAGE_SIZE)',
    'providerCount!==projection.transactionCount',
    'connected:false,persisted:false'
):
    assert phrase in journal,phrase

for phrase in (
    'fromDate:activityFromDate.text,toDate:activityToDate.text',
    'id: activityFromDate',
    'id: activityToDate',
    'FROM DATE (OPTIONAL)',
    'TO DATE (OPTIONAL)',
    'SESSION DATE RANGE // INCLUSIVE // YYYY-MM-DD',
    'maximumLength: 10',
    'CLEAR ACTIVITY DATE RANGE',
    'activityFromDate.text="";',
    'activityToDate.text="";',
    'providerPane.activityPageIndex=0;',
    'providerPane.clearSelectedEntry();',
    'providerPane.filteredActivity.matchedInCents',
    'providerPane.filteredActivity.matchedOutCents',
    'providerPane.filteredActivity.matchedNetCents',
    'THESE ARE USER-ENTERED MONEY MOVEMENTS // NOT VERIFIED INCOME OR SPENDING',
    'providerPane.filteredActivity.error',
    'providerPane.filteredActivity.totalMatches',
    'providerPane.filteredActivity.pageCount',
    'onManualCorrectionRequested: function(draft)' if False else 'signal manualCorrectionRequested(var draft)',
    'signal manualDeletionRequested(var draft)',
    'FinanceBankingOfficialHandoff {'
):
    assert phrase in provider,phrase

assert provider.count('id: activityFromDate')==1
assert provider.count('id: activityToDate')==1
assert provider.count('maximumLength: 10')==2
assert "property var manualSession" in provider
assert 'manualSession: manager.session' in manager
assert 'Accounts.correctEntry(session,draft)' in manager
assert 'Accounts.deleteEntry(session,draft)' in manager
assert 'Accounts.addEntry(session,{' in manager
assert 'function validState(state)' in accounts
assert 'FinanceBankingAccountsPane {' in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance
for source in (journal,provider):
    for forbidden in (
        'Process {','FileDialog {','FileView {','XMLHttpRequest','fetch(',
        'WebSocket','localStorage','FinanceServices.','financeWrite',
        'actual-cli','ACTUAL_PASSWORD','ACTUAL_SYNC','access_token',
        'client_secret','onPaymentSent','openDatabase','writeFile(',
        'paymentExecution','onTraderOrder','Quickshell.Io','Settings {'
    ):
        assert forbidden not in source,forbidden
assert 'Qt.openUrlExternally' not in provider
assert 'Qt.openUrlExternally' not in journal
print("Banking M4g: valid optional dates, aggregate summaries, existing M3 ownership and no external financial authority PASS")
