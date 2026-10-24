#!/usr/bin/env python3
"""M2 optional OSIRIS in-window globe pilot. Fake/source-only: no live network."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
market = (root / "widgets/FinanceMarketPane.qml").read_text()
osiris = (root / "widgets/FinanceOsirisPane.qml").read_text()
web = (root / "widgets/FinanceOsirisWebView.qml").read_text()
finance = (root / "widgets/FinanceW.qml").read_text()
host = (root / "widgets/FinanceToolHost.qml").read_text()

assert 'property string activeTool: "markets"' in market
assert 'pane.activeTool = "markets"' in market
assert 'pane.activeTool = "osiris"' in market
assert 'visible: pane.activeTool === "markets"' in market
assert 'FinanceOsirisPane {' in market
assert 'visible: pane.activeTool === "osiris"' in market
assert 'shown: pane.activeTool === "osiris" && pane.visible' in market
assert 'id: marketsView' in market  # Old Polymarket view persists
assert 'id: marketScroller' in market
assert 'onLeftClicked: marketFeed.refresh()' in market

# Quickshell's root never imports QtWebEngine, so missing web engine must not
# prevent normal FinanceW/Polymarket/Actual from loading on shell boot.
assert 'import QtWebEngine' not in finance + host + market + osiris
assert web.startswith("import QtQuick\nimport QtWebEngine\n")
assert 'import QtWebEngine' in web
assert 'source: Qt.resolvedUrl("FinanceOsirisWebView.qml")' in osiris
assert 'active: osiris.shown && osiris.loadRequested' in osiris
assert 'property bool loadRequested: false' in osiris
assert 'onLeftClicked: osiris.loadRequested = !osiris.loadRequested' in osiris
assert 'globeLoader.status === Loader.Error' in osiris
assert 'WEB RENDERER UNAVAILABLE' in osiris

# The embedded OSIRIS page cannot create a new visible app or open arbitrary
# URLs. No credentials, Budget writers or local changes are introduced.
assert 'WebEngineView {' in web
assert 'url: "https://osirisai.live/"' in web
assert 'settings.webGLEnabled: true' in web
assert 'settings.unknownUrlSchemePolicy: WebEngineSettings.DisallowUnknownUrlSchemes' in web
assert 'onNavigationRequested:' in web and 'request.reject();' in web
assert 'onNewWindowRequested:' in web and 'openIn(' not in web
assert 'onPermissionRequested:' in web and 'permission.deny();' in web
for forbidden in ('Qt.openUrlExternally', 'Process {', 'writeFile(', 'Qt.openUrlExternally(', 'openIn(view', 'financeWrite.submit'):
    assert forbidden not in market + osiris + web, forbidden
assert finance.count('PanelWindow {') == 1
assert finance.count('FinanceToolHost {') == 1
assert 'embeddedComponent: marketPaneComponent' in finance
print("FinanceW OSIRIS guarded in-workspace pilot source contracts: PASS")
