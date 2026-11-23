#!/usr/bin/env python3
"""Banking M4i: transfer-aware filtered summaries; never bank-confirmed income."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
accounts=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
for phrase in (
    'var pairs=Object.create(null);',
    'matchedTransferCount=0,matchedTransferInCents=0,matchedTransferOutCents=0;',
    'if(e.transferId) {',
    'matchedTransferCount++;',
    'bucket.transferCount++;',
    'matchedTransferInCents+=e.amountCents;',
    'matchedTransferOutCents+=-e.amountCents;',
    'bucket.transferInCents+=e.amountCents;',
    'bucket.transferOutCents+=-e.amountCents;',
    'if(!pair.out||!pair.in',
    'checkTransferCount!==matchedTransferCount',
    'checkTransferIn!==matchedTransferInCents',
    'checkTransferOut!==matchedTransferOutCents',
    'matchedTransferInCents>matchedInCents',
    'matchedTransferOutCents>matchedOutCents',
    'matchedTransferCount:matchedTransferCount',
    'matchedTransferInCents:matchedTransferInCents',
    'matchedTransferOutCents:matchedTransferOutCents',
    'matchedTransferNetCents:matchedTransferInCents-matchedTransferOutCents',
    'matchedUnlinkedCount:matchCount-matchedTransferCount',
    'matchedUnlinkedInCents:matchedInCents-matchedTransferInCents',
    'matchedUnlinkedOutCents:matchedOutCents-matchedTransferOutCents',
    'transferCount:item.transferCount',
    'transferInCents:item.transferInCents',
    'transferOutCents:item.transferOutCents',
    'unlinkedCount:item.matchedCount-item.transferCount',
    'unlinkedInCents:item.matchedInCents-item.transferInCents',
    'unlinkedOutCents:item.matchedOutCents-item.transferOutCents',
    'rows.slice(start,start+PAGE_SIZE)',
    'accountBreakdown:accountBreakdown',
    'connected:false,persisted:false',
):
    assert phrase in journal,phrase
for phrase in (
    'OF THE FILTERED MOVEMENT // DECLARED TRANSFERS ',
    'providerPane.filteredActivity.matchedTransferCount',
    'providerPane.filteredActivity.matchedTransferInCents',
    'providerPane.filteredActivity.matchedTransferOutCents',
    'UNLINKED MANUAL/DEMO ENTRIES ',
    'providerPane.filteredActivity.matchedUnlinkedCount',
    'providerPane.filteredActivity.matchedUnlinkedInCents',
    'providerPane.filteredActivity.matchedUnlinkedOutCents',
    'DECLARED TRANSFERS ARE NOT NEW INCOME OR SPENDING',
    'UNLINKED ENTRIES ARE ALSO UNVERIFIED',
    'modelData.transferCount',
    'modelData.transferInCents',
    'modelData.transferOutCents',
    'modelData.unlinkedCount',
    'modelData.unlinkedInCents',
    'modelData.unlinkedOutCents',
    'PAIRED MANUAL TRANSFER // NOT INCOME OR SPENDING',
):
    assert phrase in provider,phrase

# Identifying transfers never creates new authority or permits individual-leg editing.
assert 'function addManualTransfer(state,fields)' in accounts
assert 'function removeManualTransfer(state,fields)' in accounts
assert 'if(entry.transferId)' in accounts
assert 'Accounts.addManualTransfer(session,{' in manager
assert 'Accounts.removeManualTransfer(session,row)' in manager
for source in (journal,provider):
    for forbidden in (
        'Process {','FileView {','FileDialog {','XMLHttpRequest','fetch(',
        'WebSocket','localStorage','FinanceServices.','financeWrite',
        'actual-cli','access_token','client_secret','onPaymentSent',
        'openDatabase','writeFile(','paymentExecution','onTraderOrder','Quickshell.Io'
    ):
        assert forbidden not in source, forbidden
assert 'Qt.openUrlExternally' not in journal
assert 'Qt.openUrlExternally' not in provider
print("Banking M4i: declared transfer and unlinked summaries reconcile across provider/account/paging without promoting income or financial authority PASS")
