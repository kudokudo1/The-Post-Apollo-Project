#!/usr/bin/env python3
"""Banking M4: provider mini-app navigation and no-authority source contracts."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
policy=(root/"widgets/FinanceBankingProviderPolicy.js").read_text()
accounts=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

assert 'FinanceBankingProviderPolicy.js' in manager
assert 'property string view: "overview" // overview | provider | detail' in manager
assert 'property string selectedProviderId: ""' in manager
assert 'property string detailReturnView: "overview"' in manager
assert 'function openProvider(id)' in manager
assert 'ProviderPolicy.isProviderId(id)' in manager
assert 'function showProviderAccount(id)' in manager
assert 'a.id===id && a.providerId===selectedProviderId' in manager
assert 'detailReturnView="provider"' in manager
assert 'detailReturnView="overview"' in manager
assert 'view=detailReturnView;' in manager
assert 'manager.view=manager.detailReturnView' in manager
assert 'label: "OPEN "+modelData.name.toUpperCase()+" WORKSPACE"' in manager
assert 'FinanceBankingProviderPane {' in manager
assert 'providerId: manager.selectedProviderId' in manager
assert 'accountSnapshot: manager.review' in manager
assert 'onAccountRequested: function(accountId)' in manager
assert 'manager.showProviderAccount(accountId);' in manager
assert 'onReturnToTopRequested: manager.returnToTopRequested()' in manager
assert 'visible: manager.view==="provider"' in manager
assert 'OPEN ACCOUNT DETAILS' in manager
assert 'ADD MANUAL ACCOUNT' in manager
assert 'UNDO LAST MANUAL TRANSACTION' in manager
assert 'LOAD FICTIONAL DEMO' in manager
assert 'FinanceBankingAccountsPane {' in banking
assert 'property string selectedTool: "accounts"' in banking
assert 'FinanceTransferGuidePane {' in banking
assert 'FileDialog {' in banking
assert 'selectedMainMode === "banking"' in finance
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance

assert 'FinanceBankingProviderPolicy.js' in provider
assert 'property string sectionId: "home"' in provider
assert 'onProviderIdChanged: sectionId="home"' in provider
assert 'onSectionIdChanged: returnToTopRequested()' in provider
assert 'signal returnToTopRequested()' in provider
assert 'ProviderPolicy.build(' in provider
assert 'signal accountRequested(string accountId)' in provider
assert 'providerPane.accountRequested(modelData.id)' in provider
assert 'selected: providerPane.details.sectionId===modelData.id' in provider
assert 'onLeftClicked: providerPane.sectionId=modelData.id' in provider
assert 'OPEN ACCOUNT DETAILS' in provider
assert 'PROVIDER AUTHORIZATION REQUIRED' in policy
assert 'POST-APOLLO VIEW // NOT THE ORIGINAL APP // NO PROVIDER LOGIN' in provider
assert 'OPEN THE OFFICIAL PROVIDER APP FOR REAL ACTIONS' in provider
assert 'FICTIONAL PROVIDER CASH TOTAL' in provider
assert 'MANUAL PROVIDER CASH ESTIMATE' in provider
assert 'PARTIAL KNOWN CASH AMOUNT' in provider
assert 'NO VERIFIED BALANCES, PAYMENTS, CARDS, STOCKS OR LOANS' in provider
assert 'CASH ACCOUNTS ONLY' in provider
assert 'stock' in policy.lower() and 'borrow' in policy.lower()
assert 'paylater' in policy and 'chime-checking' in policy
assert 'activity: selected.kind==="activity"?activity.slice(0,24):[]' in policy
assert 'connected:false,persisted:false,canTransfer:false' in policy
assert 'canTrade:false,canBorrow:false,canManageCard:false' in policy
assert 'snapshot.connected!==false' in policy
assert 'snapshot.persisted!==false' in policy
assert 'account.balanceCents===null' in policy
assert 'totalCents:accounts.length>0&&unknown===0?subtotal:null' in policy
assert '"cashapp"' in accounts and '"paypal"' in accounts

# Provider mini-apps must remain read-only projections of M3's source.
# Restricted operations have labels, not clickable provider/payment commands.
for source in (provider,policy):
    for forbidden in (
        "Process {", "FileView {", "FileDialog {", "XMLHttpRequest", "fetch(",
        "Qt.openUrlExternally", "WebSocket", "console.", "localStorage",
        "FinanceServices.", "financeWrite", "actual-cli", "ACTUAL_PASSWORD",
        "ACTUAL_SYNC", "access_token", "client_secret", "banking_csv_reader",
        "onPaymentSent", "openDatabase", "writeFile(", "paymentExecution",
        "onTraderOrder", "paydayLoan", "Quickshell.Io", "Settings {"
    ):
        assert forbidden not in source, forbidden
assert 'import Quickshell.Io' not in provider
assert 'import Quickshell.Io' not in manager
assert 'FinanceBankingProviderPane' not in finance
assert 'FinanceBankingProviderPolicy' not in banking
print("FinanceW Banking M4: isolated provider workspaces, data projection and navigation contract PASS")
