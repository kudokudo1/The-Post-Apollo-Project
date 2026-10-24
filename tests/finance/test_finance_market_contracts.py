#!/usr/bin/env python3
"""Market M1: public-only, in-window, M0-safe integration contract."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
widget = (root/"widgets/FinanceW.qml").read_text()
host = (root/"widgets/FinanceToolHost.qml").read_text()
pane = (root/"widgets/FinanceMarketPane.qml").read_text()
service = (root/"services/finance/FinanceMarketReadService.qml").read_text()
backend = (root/"scripts/finance/read_polymarket.mjs").read_text()

assert 'FinanceServices.FinanceMarketReadService {' in widget
assert 'monitoring: root.menuOpen && root.selectedMainMode === "market"' in widget
assert 'embeddedComponent: marketPaneComponent' in widget
assert 'showEmbedded: root.selectedMainMode === "market"' in widget
assert 'marketFeed: marketService' in widget
assert widget.count('FinanceToolHost {') == 1
assert widget.count('PanelWindow {') == 1
assert 'active: host.toolConnected' in host  # resize never unmounts it
assert 'visible: host.toolConnected && host.showEmbedded' in host
assert 'visible: !host.toolConnected || !host.showEmbedded' in host
assert 'onLeftClicked: marketFeed.refresh()' in pane
assert 'readonly property bool wide: width >= 660' in pane
assert 'TapHandler {' in pane
assert 'FINANCE_MARKET_SNAPSHOT ' in service
assert 'payload.source !== "polymarket-gamma"' in service
assert 'payload.readOnly !== true' in service
assert 'if (!monitoring || reader.running || loading)' in service
assert 'Quickshell.shellPath("scripts/finance/read_polymarket.mjs")' in service
assert 'readOnly: true' in backend
assert 'method: "GET"' in backend
assert 'AbortSignal.timeout(10000)' in backend
for forbidden in ("Qt.openUrlExternally", "writeFile(", "setBudgetAmount(",
                  "addTransactions(", "updateTransaction(", "stdinEnabled:",
                  "https://clob.polymarket.com/order", "credentials:"):
    assert forbidden not in pane + service + backend, forbidden
assert "FINANCE_MARKET_ERROR" in service and "FINANCE_MARKET_ERROR" in backend
assert 'marketService.live ? "SNAPSHOT"' in widget
print("FinanceW Market M1 isolated read-only in-workspace contracts: PASS")
