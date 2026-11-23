#!/usr/bin/env python3
"""FinanceW Banking M4n: selected account to provider Activity, display-only."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
policy=(root/"widgets/FinanceBankingActivityNavigationPolicy.js").read_text()
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
accounts=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()

assert "function accountFilterIndex(details,providerId,accountId)" in policy
for phrase in (
    "details.ok!==true",
    "details.connected!==false||details.persisted!==false",
    "details.providerId!==providerId",
    'typeof accountId!=="string"',
    "!Array.isArray(details.allAccounts)",
    "details.allAccounts.length>12",
    "Object.create(null)",
    "account.providerId!==providerId",
    "Object.prototype.hasOwnProperty.call(seen,account.id)",
    "if(account.id===accountId)result=i+1;",
    "return result;",
):
    assert phrase in policy,phrase

assert 'import "FinanceBankingActivityNavigationPolicy.js" as ActivityNavigation' in provider
start=provider.index("    function showActivityForAccount(accountId) {")
end=provider.index("    function chooseManualEntry(row) {",start)
method=provider[start:end]
for phrase in (
    "ActivityNavigation.accountFilterIndex(details,providerId,accountId)",
    "if(index<1)return false;",
    'sectionId="activity";',
    'activityDirection="all";',
    'activityFromDate="";',
    'activityToDate="";',
    'activitySearch.text="";',
    "activityPageIndex=0;",
    "showActivityBreakdown=false;",
    "activityAccountIndex=index;",
    "clearSelectedEntry();",
    "return activityAccountId===accountId&&filteredActivity.ok;",
):
    assert phrase in method,phrase
# Section changes invoke the previous reset; only AFTER that reset may
# the requested account index be installed, otherwise UI shows ALL.
assert method.index("if(index<1)") < method.index('sectionId="activity";')
assert method.index('sectionId="activity";') < method.index("activityAccountIndex=index;")
assert method.index("activitySearch.text=") < method.index("activityAccountIndex=index;")
assert "onSectionIdChanged: {" in provider
assert 'activityAccountIndex=0;' in provider
assert "readonly property string activityAccountId:" in provider
assert "accountId:activityAccountId" in provider
assert "FILTER ACCOUNT // " in provider
assert "providerPane.activityPageIndex=0;" in provider

start=manager.index("    function openSelectedProviderActivity() {")
end=manager.index("    function showProviderAccount(id) {",start)
bridge=manager[start:end]
for phrase in (
    'view!=="detail"||!review.ok||!selected',
    "!ProviderPolicy.isProviderId(selected.providerId)",
    "review.accounts.some(function(a)",
    "a.id===selected.id&&a.providerId===selected.providerId;",
    "var accountId=selected.id;",
    "selectedProviderId=selected.providerId;",
    'providerMiniApp.sectionId="activity";',
    "providerMiniApp.showActivityForAccount(accountId)",
    'message="ACCOUNT-SCOPED PROVIDER ACTIVITY UNAVAILABLE";',
    'view="provider";',
):
    assert phrase in bridge,phrase
assert bridge.index("providerMiniApp.showActivityForAccount(accountId)") < bridge.index('view="provider";')
assert 'onLeftClicked: manager.openSelectedProviderActivity()' in manager
assert 'OPEN FULL PROVIDER ACTIVITY // FILTERS AND HISTORY' in manager
assert 'id: providerMiniApp' in manager
assert 'providerId: manager.selectedProviderId' in manager
assert 'accountSnapshot: manager.review' in manager
assert 'manualSession: manager.session' in manager

# Only the validated existing journal is filtered, never a new provider API
# or a direct transaction writer. Previous M4i/M4j/M4l writers remain owned
# by the Accounts pane.
assert "function project(projection,session,options)" in journal
assert "ACCOUNT IS NOT IN THIS PROVIDER" in journal
assert "accountId && !Object.prototype.hasOwnProperty.call(providerAccounts,accountId)" in journal
assert "function correctAccountDetails(state,fields)" in accounts
assert "function correctManualTransfer(state,fields)" in accounts
assert "function addManualTransfer(state,fields)" in accounts
for source in (policy,method,bridge):
    for unsafe in (
        "Process {","FileView {","XMLHttpRequest","fetch(","WebSocket",
        "Qt.openUrlExternally","localStorage","financeWrite","actual-cli",
        "access_token","client_secret","onPaymentSent","openDatabase",
        "writeFile(","paymentExecution","onTraderOrder","Quickshell.Io",
        "Accounts.addEntry","Accounts.deleteEntry","Accounts.correctEntry",
        "Accounts.addManualTransfer","Accounts.correctManualTransfer",
        "Accounts.correctAccountDetails",
    ):
        assert unsafe not in source,unsafe

print("Banking M4n: account-id scoped Activity deep-link, reset ordering, provider isolation and no-write UI contracts PASS")
