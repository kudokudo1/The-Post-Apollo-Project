#!/usr/bin/env python3
"""Read-only FinanceW Budget UI and queued auto-refresh source contracts."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
ui = (root / "widgets/FinanceW.qml").read_text()
bridge = (root / "services/finance/FinanceBudgetReadService.qml").read_text()
cli = (root / "scripts/finance/read_budget.mjs").read_text()
assert 'FinanceServices.FinanceBudgetReadService {' in ui
assert 'monitoring: root.menuOpen' in ui
assert 'id: financeFeedIndicator' in ui
assert 'import QtQuick.Effects' in ui
assert 'id: financeFeedText' in ui
assert 'color: root.feedBorderColor' in ui
assert 'color: root.feedStatusColor' in ui
assert 'feedStatus === "LIVE" ? Colors.green' in ui
assert 'feedStatus === "OFFLINE" || feedStatus === "ERROR"' in ui
assert '|| feedStatus === "NO FEED" ? feedStatusColor : Colors.omnitrix' in ui
assert 'id: closeButton' in ui
assert 'softGlowIdleOpacity: 0.48' in ui
assert 'wideGlowEnabled: true' in ui
assert 'idleWideGlowColor: Colors.red' in ui
assert 'root.moneyText(modelData.amountCents)' in ui
assert 'modelData.date + "  " + modelData.description' in ui
assert 'modelData.account' in ui
assert 'LATEST 24 SHOWN // READ ONLY' in ui
assert 'financeBudget.snapshot.transactionsCount' in ui
assert 'Number.isSafeInteger(payload.transactionsCount)' in bridge
assert 'payload.transactions.length > 24' in bridge
assert 'anchors.right: closeButton.left' in ui
assert 'anchors.right: financeFeedIndicator.left' in ui
assert 'border.color: root.feedBorderColor' in ui
assert 'text: root.feedStatus' in ui
assert 'color: root.feedStatusColor' in ui
assert 'feedStatus === "LIVE" ? Colors.green' in ui
assert 'feedStatus === "OFFLINE" || feedStatus === "ERROR" ? Colors.red' in ui
assert 'financeBudget.state === "ready"' in ui
assert 'financeBudget.healthStatus === "online" ? "LIVE"' in ui
assert ui.index('financeBudget.healthStatus === "offline" ? "OFFLINE"') < ui.index('financeBudget.state === "failed" ? "ERROR"')
assert '!hasBudgetFeed ? "NO FEED"' in ui
assert 'text: "ACCOUNTS "' in ui
assert 'root.accountTotalCents()' in ui
assert 'Number.isSafeInteger(sum)' in ui
assert 'ACTUAL // CACHED' in ui
assert 'SOURCE OFFLINE // LAST READ' in ui
assert 'property bool monitoring: false' in bridge
assert 'property string healthStatus: "unknown"' in bridge
assert 'onMonitoringChanged:' in bridge
assert 'running: budgetBridge.monitoring' in bridge
assert 'onTriggered: budgetBridge.checkReachability()' in bridge
assert 'id: healthProbe' in bridge
assert '["/usr/bin/curl", "--silent", "--fail"' in bridge
assert 'budgetBridge.monitoring' in bridge
assert 'exitCode === 0 ? "online" : "offline"' in bridge
assert 'const wasOffline = budgetBridge.healthStatus === "offline";' in bridge
assert 'if (wasOffline && nextHealth === "online"' in bridge
assert '&& !budgetBridge.loading)' in bridge
assert 'budgetBridge.refresh();' in bridge[bridge.index('id: healthProbe'):bridge.index('Timer {')]
assert 'lastReadAt = Qt.formatTime(new Date(), "hh:mm:ss");' in bridge
assert 'onLeftClicked: financeBudget.refresh()' in ui
assert 'available: !financeBudget.loading' in ui
assert 'onLeftClicked: financeBudget.shiftMonth(-1)' in ui
assert 'onLeftClicked: financeBudget.shiftMonth(1)' in ui
assert 'text: financeBudget.selectedMonth' in ui
assert 'root.moneyText(modelData.spentCents)' in ui
assert 'NET SPENT ' in ui
assert 'OVERSPENT' in ui
assert 'Math.max(0, Math.min(1,' in ui
assert 'function shiftMonth(direction)' in bridge
assert 'selectedMonth = String(nextYear)' in bridge
assert 'FINANCEW_MONTH: selectedMonth' in bridge
assert 'payload.month !== selectedMonth' in bridge
assert 'if (direction !== 1 && direction !== -1)' in bridge
assert 'refresh();' in bridge[bridge.index('function shiftMonth'):bridge.index('function fail')]
assert 'if (requestActive || probe.running)' in bridge
assert 'property bool requestActive: false' in bridge
assert 'requestActive = true;' in bridge
assert 'budgetBridge.requestActive = false;' in bridge
assert 'pendingRefresh = selectedMonth !== inFlightMonth;' in bridge
assert 'property bool pendingRefresh: false' in bridge
assert 'inFlightMonth !== selectedMonth' in bridge
assert 'if (budgetBridge.pendingRefresh)' in bridge
assert 'budgetBridge.refresh();' in bridge
assert 'if (menuOpen) {' in ui[ui.index('onMenuOpenChanged:'):ui.index('onKeyboardActiveChanged:')]
assert 'financeBudget.refresh();' in ui[ui.index('onMenuOpenChanged:'):ui.index('onKeyboardActiveChanged:')]
assert 'available: !financeBudget.loading' in ui[ui.index('id: refreshBudget'):ui.index('id: financeMonthRail')]
for arrow in ('previousBudgetMonth', 'nextBudgetMonth'):
    portion = ui[ui.index('id: ' + arrow):ui.index('onLeftClicked: financeBudget.shiftMonth', ui.index('id: ' + arrow))]
    assert 'available: !financeBudget.loading' not in portion
assert 'visible: !actualBudgetPage.visible' in ui
assert 'root.moneyText(modelData.balanceCents)' in ui
assert 'root.moneyText(modelData.availableCents)' in ui
assert 'root.moneyText(modelData.budgetedCents)' in ui
assert 'textFormat: Text.PlainText' in ui
assert 'property string state: "idle"' in bridge
assert 'if (requestActive || probe.running)' in bridge
assert 'Quickshell.shellPath("scripts/finance/read_budget.mjs")' in bridge
assert 'ACTUAL_SYNC_ID: null' in bridge
assert 'ACTUAL_SYNC_ID_FILE: null' in bridge
assert 'ACTUAL_PASSWORD_FILE: null' in bridge
assert 'ACTUAL_SERVER_URL: "http://127.0.0.1:5007"' in bridge
assert 'Number.isSafeInteger(payload.toBudgetCents)' in bridge
assert 'onStreamFinished: budgetBridge.acceptOutput(text)' in bridge
assert 'onStreamFinished: budgetBridge.acceptError(text)' in bridge
assert 'snapshot = null;' in bridge
assert bridge.count('Timer {') == 1
assert 'interval: 15000' in bridge
assert 'triggeredOnStart: true' in bridge
assert bridge.count('Process {') == 2
assert 'running: true' not in bridge
# QML's JS parser requires a catch binding; JS optional catch syntax
# would otherwise prevent the entire Post-Apollo shell from starting.
assert 'catch (error) {' in bridge
assert 'catch {' not in bridge
assert 'console.log' not in bridge
for forbidden in ('runBankSync(', 'setBudgetAmount(', 'updateTransaction('):
    assert forbidden not in bridge
for forbidden in ('password:', 'syncId:', 'ACTUAL_SYNC_ID='):
    assert forbidden not in ui
assert 'ACTUAL_SYNC_ID_FILE' in cli
print("FinanceW Budget read-only UI and queued refresh contracts: PASS")
