#!/usr/bin/env python3
"""Banking M4c: session-only cash product dashboards, no action privileges."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
policy=(root/"widgets/FinanceBankingProviderPolicy.js").read_text()
accounts=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

for requirement in (
    "var viewIn=0,viewOut=0,viewCount=0,preview=[],older=false;",
    "var viewKnown=0,viewUnknown=0,viewSubtotal=0;",
    "selectedAccount.balanceCents===null",
    "viewIn+=selectedAccount.creditsCents;",
    "viewOut+=selectedAccount.debitsCents;",
    "viewCount+=selectedAccount.transactionCount;",
    "selectedAccount.transactionCount>selectedAccount.recent.length",
    "visibleKnownBalanceCount:viewKnown",
    "visibleUnknownBalanceCount:viewUnknown",
    "visibleKnownBalanceSubtotalCents:viewSubtotal",
    "visibleBalanceCents:listed.length>0&&viewUnknown===0?viewSubtotal:null",
    "visibleMovementInCents:viewIn",
    "visibleMovementOutCents:viewOut",
    "visibleMovementNetCents:viewIn-viewOut",
    "visibleTransactionCount:viewCount",
    "visibleRecent:preview.slice(0,4)",
    "visibleRecentOmitted:older||preview.length>4",
    "function compareSessionActivity(a,b)",
    "activity.sort(compareSessionActivity)",
    "preview.sort(compareSessionActivity)",
    "row.creditsCents-row.debitsCents!==row.netChangeCents",
    "row.transactionCount>300",
    "transactionCount:txCount,visibleAccounts:listed,allAccounts:accounts",
    "connected:false,persisted:false,canTransfer:false",
    "canTrade:false,canBorrow:false,canManageCard:false"
):
    assert requirement in policy, requirement

for requirement in (
    'visible: providerPane.details.ok && providerPane.details.sectionKind==="product"',
    "FICTIONAL SELECTED PRODUCT BALANCE",
    "MANUAL SELECTED PRODUCT ESTIMATE",
    "SELECTED PRODUCT HAS UNKNOWN BALANCE",
    "NO MANUAL ACCOUNT MATCHES THIS PRODUCT",
    "CASH ACCOUNTS // SESSION MONEY MOVEMENT",
    "visibleMovementInCents",
    "visibleMovementOutCents",
    "visibleMovementNetCents",
    "NOT VERIFIED INCOME, SPENDING OR TRANSFERS",
    "SESSION IN ",
    "modelData.creditsCents",
    "modelData.debitsCents",
    "RECENT SESSION ACTIVITY // UP TO 4 ENTRIES",
    "model: providerPane.details.visibleRecent",
    "MORE OR OLDER ENTRIES EXIST",
    "OPEN ACCOUNT DETAILS",
    "OPEN THE OFFICIAL PROVIDER APP FOR REAL ACTIONS",
    "NO VERIFIED BALANCES, PAYMENTS, CARDS, STOCKS OR LOANS"
):
    assert requirement in pane, requirement

# The new product screens cannot gain network, payment, storage, identity or
# API access through a summary. They reuse the existing manual/demo session.
for source in (pane,policy):
    for forbidden in (
        "Process {", "FileView {", "FileDialog {", "XMLHttpRequest",
        "fetch(", "Qt.openUrlExternally", "WebSocket", "console.",
        "localStorage", "FinanceServices.", "financeWrite",
        "actual-cli", "ACTUAL_PASSWORD", "ACTUAL_SYNC", "access_token",
        "client_secret", "banking_csv_reader", "onPaymentSent", "openDatabase",
        "writeFile(", "paymentExecution", "onTraderOrder", "Quickshell.Io",
        "Settings {"
    ):
        assert forbidden not in source, forbidden
assert "Accounts.addEntry(session,{" in manager
assert "function validState(state)" in accounts
assert 'FinanceBankingAccountsPane {' in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance
print("Banking M4c: provider cash summaries, product-scoped balances, bounded previews and no payment permissions PASS")
