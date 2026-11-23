#!/usr/bin/env python3
"""Banking M4h: read-only filtered per-account movement and QML disclosure."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
accounts=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

for item in (
    "var breakdownById=Object.create(null),breakdown=[];",
    "for(var b=0;b<projection.allAccounts.length;b++)",
    "var account=projection.allAccounts[b];",
    "breakdownById[account.id]=bucket;",
    "var bucket=breakdownById[e.accountId];",
    'if(!bucket)return fail("INVALID PROVIDER ACTIVITY BUCKET")',
    "bucket.matchedCount++;",
    "bucket.matchedInCents+=e.amountCents;",
    "bucket.matchedOutCents+=-e.amountCents;",
    "if(item.matchedCount===0)continue;",
    "accountBreakdown.push({accountId:item.accountId,",
    "accountNickname:item.accountNickname,",
    "matchedCount:item.matchedCount,",
    "matchedInCents:item.matchedInCents,",
    "matchedOutCents:item.matchedOutCents,",
    "matchedNetCents:item.matchedInCents-item.matchedOutCents",
    "checkCount!==rows.length",
    "checkIn!==matchedInCents||checkOut!==matchedOutCents",
    'return fail("INCONSISTENT SESSION MOVEMENT TOTAL")',
    "accountBreakdown:accountBreakdown,",
    'totalsScope:"FILTERED SESSION ENTRIES // NOT VERIFIED INCOME OR SPENDING"',
    "rows.slice(start,start+PAGE_SIZE)",
    'connected:false,persisted:false'
):
    assert item in journal,item

for item in (
    "property bool showActivityBreakdown: false",
    "showActivityBreakdown=false;",
    'label: "SHOW FILTERED ACCOUNT BREAKDOWN"',
    'label: "HIDE FILTERED ACCOUNT BREAKDOWN"',
    "providerPane.showActivityBreakdown=",
    "!providerPane.showActivityBreakdown",
    "providerPane.filteredActivity.accountBreakdown.length>0",
    "MATCHED ACTIVITY BY MANUAL ACCOUNT // TOTALS INCLUDE ALL MATCHING PAGES",
    "model: providerPane.filteredActivity.ok",
    "? providerPane.filteredActivity.accountBreakdown:[]",
    "required property var modelData",
    "modelData.accountNickname",
    "modelData.matchedCount",
    "modelData.matchedInCents",
    "modelData.matchedOutCents",
    "modelData.matchedNetCents",
    "MANUAL/DEMO CASH MOVEMENT ONLY // NOT VERIFIED BALANCES OR PROFIT",
    "THESE ARE USER-ENTERED MONEY MOVEMENTS // NOT VERIFIED INCOME OR SPENDING",
    "signal manualCorrectionRequested(var draft)",
    "signal manualDeletionRequested(var draft)",
    "FinanceBankingOfficialHandoff {",
):
    assert item in provider,item

assert 'manualSession: manager.session' in manager
assert 'Accounts.correctEntry(session,draft)' in manager
assert 'Accounts.deleteEntry(session,draft)' in manager
assert 'Accounts.addEntry(session,{' in manager
assert 'function validState(state)' in accounts
assert 'FinanceBankingAccountsPane {' in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance
assert "var MAX_ACCOUNTS = 12" in accounts
assert "var MAX_ENTRIES = 300" in accounts
assert "var MAX_ACCOUNTS=12;" in journal
assert "var MAX_ENTRIES=300;" in journal

for source in (journal,provider):
    for unsafe in (
        "Process {","FileDialog {","FileView {","XMLHttpRequest","fetch(",
        "WebSocket","localStorage","FinanceServices.","financeWrite",
        "actual-cli","ACTUAL_PASSWORD","ACTUAL_SYNC","access_token",
        "client_secret","onPaymentSent","openDatabase","writeFile(",
        "paymentExecution","onTraderOrder","Quickshell.Io","Settings {"
    ):
        assert unsafe not in source,unsafe
assert "Qt.openUrlExternally" not in provider
assert "Qt.openUrlExternally" not in journal
print("Banking M4h: filtered per-account read projection, UI disclosure, existing writer authority and source isolation PASS")
