#!/usr/bin/env python3
"""Shared DIAG contract: Weather M6c extraction + Finance service-owner reuse."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
button=(root/"components/DiagnosticsDockButton.qml").read_text()
popup=(root/"components/DiagnosticsServicePopup.qml").read_text()
weather=(root/"widgets/weather/WeatherStationW.qml").read_text()
weather_adapter=(root/"widgets/weather/StationWeatherProviderDiagnostics.qml").read_text()
weather_policy=(root/"widgets/weather/StationProviderDiagnosticsPolicy.js").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()

# The actual shared toggle is icon-only. White stars use rich text and the
# medical glyph retains its state color; the three effect planes match the
# canonical CloseButton / ResizeButton numeric intensities.
for marker in (
    "ActionButton {", "property bool diagnosticsOpen: false",
    "signal toggleRequested()", "˖", "⚕๋࣭", "⭑",
    "labelItem.textFormat: Text.StyledText",
    "selected: diagnosticsOpen",
    "width: 59", "height: 32", "labelPixelSize: 21",
    "accentColor: Colors.yellow",
    "onLeftClicked: diagnosticButton.toggleRequested()",
    "contentGlowRadius: 7", "contentGlowSamples: 7",
    "contentGlowIdleOpacity: 0.34",
    "contentGlowHoverOpacity: 0.72",
    "contentGlowPressedOpacity: 1.0",
    "softGlowIdleOpacity: 0.48",
    "softGlowHoverOpacity: 0.70",
    "softGlowPressedOpacity: 1.0",
    "wideGlowEnabled: true", "wideGlowSpread: 10",
    "wideGlowIdleOpacity: 0.22",
    "wideGlowHoverOpacity: 0.32",
    "wideGlowPressedOpacity: 1.0",
):
    assert marker in button, marker
assert 'label: diagnosticsOpen ? "BACK" : "DIAG"' not in button
assert button.count("Colors.white") == 2  # both decorative star regions

# Weather's M6c pane retains its real source policy and overlay ownership.
for marker in (
    "DiagnosticsDockButton {", "id: providerDiagnosticsButton",
    "diagnosticsOpen: weatherStation.providerDiagnosticsOpen",
    "onToggleRequested:", "providerDiagnosticsOpen = false",
    "StationWeatherProviderDiagnostics {", "snapshot: weatherStation.weatherDiagnostics",
    "onCloseRequested: weatherStation.providerDiagnosticsOpen = false",
    "if (providerDiagnosticsOpen)", "visible: weatherStation.providerDiagnosticsOpen",
):
    assert marker in weather, marker
assert "ProviderDiagnostics.snapshot({" in weather
assert "function snapshot(" in weather_policy
assert weather.count("StationWeatherProviderDiagnostics {") == 1
assert "DiagnosticsServicePopup {" in weather_adapter
assert "[snapshot.primary, snapshot.fallback, snapshot.aqi]" in weather_adapter
assert "snapshot ? snapshot.currentState" in weather_adapter

# The reusable popup is the true rendering, status color and scroll owner.
for marker in (
    "signal closeRequested()", "Flickable {", "Repeater {",
    "NeonScrollBar {", "function statusColor(state)",
    'text: "DISPLAYED // " + diagnosticsPane.displayedState',
    'text: "ORIGIN // " + diagnosticsPane.providerLabel',
    'text: "LOCATION // "',
    "model: Array.isArray(diagnosticsPane.serviceRows)",
    "text: sourceRow.modelData.state", "text: sourceRow.modelData.label",
    "CloseButton {", "onCloseRequested: diagnosticsPane.closeRequested()",
    "id: diagnosticsPointerShield", "id: diagnosticsWheelContainment",
    "blocking: true", "wheel.accepted = true;",
    'color: "#110319"', "opacity: 1.0",
    "mountingParent: diagnosticsPane", "geometryHost: diagnosticsPane",
    'geometryMode: "box"', 'boxTopInset: 68',
    'boxBottomInset: 12', 'rightInset: 8',
):
    assert marker in popup, marker

# Finance uses the same real button AND popup on the same PanelWindow.
for marker in (
    "property bool diagnosticsOpen: false",
    "readonly property var diagnosticServiceRows:",
    "DiagnosticsDockButton {", "id: financeDiagnosticsButton",
    "onToggleRequested: root.diagnosticsOpen = !root.diagnosticsOpen",
    "DiagnosticsServicePopup {", "id: financeDiagnosticsPane",
    "visible: root.menuOpen && root.diagnosticsOpen",
    "serviceRows: root.diagnosticServiceRows",
    "onCloseRequested: root.diagnosticsOpen = false",
    "diagnosticsOpen = false;",
    "if (event.key === Qt.Key_Escape && root.diagnosticsOpen)",
    "if (root.diagnosticsOpen)",
    "else\n                root.menuOpen = false;",
    "&& !diagnosticsOpen", "z: 90",
):
    assert marker in finance, marker
assert finance.count("DiagnosticsServicePopup {") == 1
assert finance.count("DiagnosticsDockButton {") == 1
assert "id: financeDiagnosticsBackdrop" in finance
assert "z: 89" in finance
assert "color: Qt.rgba(Colors.black.r, Colors.black.g," in finance
assert "onWheel: function(wheel) { wheel.accepted = true; }" in finance
assert "id: providerDiagnosticsBackdrop" in weather
assert "z: 49" in weather
assert "onWheel: function(wheel) { wheel.accepted = true; }" in weather
assert "ActionButton {" not in popup  # use existing CloseButton, not a local clone

# The rows must read SAME pre-existing service actors without adding new owners.
for actor in (
    "financeBudget", "marketService", "crawlService", "secService",
    "secDocumentService", "secPriceService",
):
    assert actor in finance, actor
for source in (
    'label:"BUDGET / ACTUAL"',
    'label:"MARKET / PUBLIC"',
    'label:"RESEARCH / SOURCE CRAWL"',
    'label:"RESEARCH / SEC EDGAR"',
    'label:"SEC DOCUMENT / INSPECT"',
    'label:"SEC PRICE / CONTEXT"',
    'label:"BANKING / MANUAL"',
):
    assert source in finance, source
assert "return \"SNAPSHOT\";" in finance
assert 'state:root.menuOpen && root.selectedMainMode === "banking"' in finance
assert "NO EXTRA FETCHES" in finance

# No new collectors or hidden writer permissions in either reusable primitive.
for item in (button,popup,weather_adapter):
    for forbidden in (
        "PanelWindow {", "Process {", "Timer {", "FileView {",
        "XMLHttpRequest", "Qt.openUrlExternally", "fetch(",
        "financeWrite", "writeEnabled", "runCommand(", "exec(",
    ):
        assert forbidden not in item, forbidden
assert finance.count("FinanceServices.FinanceMarketReadService {") == 1
assert finance.count("FinanceServices.FinanceCrawlReadService {") == 1
assert finance.count("FinanceServices.FinanceSecReadService {") == 1

print("Shared Weather/Finance dock diagnostics and actual service popup: PASS")
