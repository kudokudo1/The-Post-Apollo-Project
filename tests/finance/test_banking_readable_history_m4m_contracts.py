#!/usr/bin/env python3
"""Banking M4m: readable read-only history and navigation, no new ledger authority."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
policy=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()

for p in (
    'property bool showAllRecentHistory: false',
    'onViewChanged: {',
    'onSelectedIdChanged: {',
    'showAllRecentHistory=false;',
    'RECENT ACTIVITY // ',
    'manager.showAllRecentHistory?12:3',
    'manager.selected.transactionCount',
    'manager.selected.recent.slice(0,manager.showAllRecentHistory?12:3):[]',
    'readonly property bool transferLeg: !!modelData.transferId',
    'recentEntryCard.transferLeg?Colors.magenta:Colors.cyan',
    'height: activityBlock.implicitHeight+14',
    'font.pixelSize: 12',
    'font.bold: true',
    'Math.abs(modelData.amountCents)',
    'Accounts.money(Math.abs(modelData.amountCents))',
    'modelData.amountCents<0?Colors.orange:Colors.omnitrix',
    'modelData.amountCents<0?"TRANSFER OUT // ":"TRANSFER IN // "',
    'modelData.amountCents<0?"MONEY OUT // ":"MONEY IN // "',
    'DATE // ',
    'DECLARED PAIRED MANUAL TRANSFER // NOT VERIFIED INCOME OR SPENDING',
    'ONLY THE 12 MOST RECENTLY RECORDED ENTRIES ARE PREVIEWED HERE',
    'SHOW LATEST 3 ENTRIES',
    'SHOW UP TO 12 RECENT ENTRIES',
    'onLeftClicked: manager.showAllRecentHistory=!manager.showAllRecentHistory',
    'OPEN FULL PROVIDER ACTIVITY // FILTERS AND HISTORY',
    'function openSelectedProviderActivity()',
    'view!=="detail"||!selected',
    '!ProviderPolicy.isProviderId(selected.providerId)',
    'selectedProviderId=selected.providerId;',
    'view="provider";',
    'providerMiniApp.sectionId="activity";',
    'onLeftClicked: manager.openSelectedProviderActivity()',
):
    assert p in pane,p

assert pane.count('id: recentEntryCard')==1
assert pane.count('model: manager.selected\n                    ? manager.selected.recent.slice')==1
assert pane.count('OPEN FULL PROVIDER ACTIVITY // FILTERS AND HISTORY')==1
assert pane.count('function openSelectedProviderActivity()')==1
assert 'recent:activity.slice(-12).reverse()' in policy
assert 'transactionCount:activity.length' in policy
assert 'function validState(state)' in policy
assert 'function correctManualTransfer(state,fields)' in policy
assert 'function correctAccountDetails(state,fields)' in policy
assert 'FinanceBankingProviderPane {' in pane
assert 'property string sectionId: "home"' in provider
assert 'providerPane.details.sectionKind==="activity"' in provider
assert 'FinanceBankingAccountsPane {' in banking

# No account write or network action is added; preview and navigation use the
# existing M3 snapshot and existing provider Activity journal.
assert 'Accounts.snapshot(session)' in pane
assert 'Accounts.addManualTransfer(session,{' in pane
assert 'Accounts.correctManualTransfer(session,{' in pane
assert 'Accounts.correctAccountDetails(session,{' in pane
for source in (pane,policy):
    for forbidden in (
        'Process {','FileView {','XMLHttpRequest','fetch(','WebSocket',
        'Qt.openUrlExternally','localStorage','FinanceServices.','financeWrite',
        'actual-cli','access_token','client_secret','onPaymentSent',
        'openDatabase','writeFile(','paymentExecution','onTraderOrder',
        'Quickshell.Io'
    ):
        assert forbidden not in source,forbidden
print("Banking M4m: recent-3/full-12 readable cards, safe provider Activity navigation, unchanged manual source authority PASS")
