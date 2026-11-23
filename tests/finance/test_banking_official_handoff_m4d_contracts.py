#!/usr/bin/env python3
"""FinanceW Banking M4d: exact official homepage and two-click handoff boundary."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
ui=(root/"widgets/FinanceBankingOfficialHandoff.qml").read_text()
policy=(root/"widgets/FinanceBankingOfficialHandoffPolicy.js").read_text()
provider=(root/"widgets/FinanceBankingProviderPolicy.js").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()

assert 'FinanceBankingOfficialHandoff {' in pane
assert 'providerPane.details.sectionKind==="restricted"' in pane
assert 'providerId: providerPane.providerId' in pane
assert 'sectionId: providerPane.details.ok ? providerPane.details.sectionId : ""' in pane
assert 'height: visible ? implicitHeight : 0' in pane
assert 'PROVIDER AUTHORIZATION REQUIRED' in provider
assert 'FinanceBankingAccountsPane {' in banking
assert 'FinanceBankingProviderPane {' in manager
assert 'POST-APOLLO VIEW // NOT THE ORIGINAL APP // NO PROVIDER LOGIN' in pane

for snippet in (
    'property bool armed: false',
    'property string outcome: ""',
    'readonly property var target: Official.destination(providerId,sectionId)',
    'function resetConfirmation()',
    'onProviderIdChanged: resetConfirmation()',
    'onSectionIdChanged: resetConfirmation()',
    'if(!visible)resetConfirmation();',
    'function requestOpen()',
    'if(!fresh.ok || !Official.canOpen(fresh,providerId,sectionId))',
    'if(!armed) {',
    'armed=true;',
    'armed=false;',
    'const accepted=Qt.openUrlExternally(fresh.url);',
    'BROWSER OPEN REQUEST SENT // NO PROVIDER ACTION WAS PERFORMED',
    'BROWSER HANDOFF WAS NOT ACCEPTED // NO PROVIDER ACTION WAS PERFORMED',
    'OPEN '+ '"'+ '+handoff.target.providerName.toUpperCase()+" OFFICIAL SITE"',
    'CONFIRM OPEN ',
    'EXTERNAL BROWSER // NOT A DIRECT LINK TO THIS FEATURE',
    'VERIFY THE DOMAIN BEFORE SIGN-IN',
    'onLeftClicked: handoff.requestOpen()',
):
    assert snippet in ui,snippet

for key in ('cashapp','chime','paypal'):
    assert key+':' in policy,key
assert 'url:"https://cash.app/"' in policy
assert 'url:"https://www.chime.com/"' in policy
assert 'url:"https://www.paypal.com/"' in policy
assert 'Object.prototype.hasOwnProperty.call(OFFICIAL,providerId)' in policy
assert 'Object.prototype.hasOwnProperty.call(RESTRICTED,providerId)' in policy
assert 'sections.indexOf(sectionId)<0' in policy
assert 'requiresConfirmation:true' in policy
assert 'passesCredentials:false' in policy
assert 'executesFinancialAction:false' in policy
assert 'function canOpen(decision,providerId,sectionId)' in policy
assert 'decision.url===expected.url' in policy
assert 'decision.sectionId===sectionId' in policy
assert 'decision.host===expected.host' in policy
assert 'kind:"official-homepage"' in policy
assert 'https://evil.example' not in policy
assert '?' not in policy.split('var OFFICIAL = {')[1].split('};')[0], "No query-string or token passing"
assert 'url:"http:' not in policy
assert 'bank:' not in policy.split('var OFFICIAL = {')[1].split('};')[0], "Generic bank cannot use a guessed URL"
assert ui.count('Qt.openUrlExternally(')==1,"Single explicit browser handoff only"
assert "Component.onCompleted" not in ui, "No implicit opening"
assert "Timer {" not in ui, "No background opening"
assert "onVisibleChanged:" in ui
assert "console." not in ui
assert "Quickshell.Io" not in ui
assert "FileDialog" not in ui

# No other Banking pane or provider UI can silently open arbitrary URLs.
assert 'Qt.openUrlExternally' not in pane
assert 'Qt.openUrlExternally' not in provider
assert 'Qt.openUrlExternally' not in manager
for forbidden in (
    "Process {","FileView {","XMLHttpRequest","fetch(","WebSocket",
    "access_token","client_secret","password:","accountNumber",
    "accountId:","amountCents:","paymentExecution","onTraderOrder",
    "onPaymentSent","writeFile(","openDatabase","FinanceServices.",
):
    assert forbidden not in ui,forbidden
print("Banking M4d: fixed official homepages, two-click user control, no credential/transaction data and restricted-only mounting PASS")
