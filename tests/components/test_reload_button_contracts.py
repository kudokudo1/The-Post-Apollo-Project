#!/usr/bin/env python3
"""Shared ReloadButton UI and TimeW resync owner contract (source-only)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RELOAD = (ROOT / "components/ReloadButton.qml").read_text(encoding="utf-8")
CLOSE = (ROOT / "components/CloseButton.qml").read_text(encoding="utf-8")
BASE = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")
TIME = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")


def require(token):
    assert token in RELOAD, f"ReloadButton missing {token!r}"


assert re.search(r"(?m)^ActionButton\s*\{", RELOAD)
assert "ReloadButton 1.0 ReloadButton.qml" in QMLDIR
for name in ("contentGlow", "softGlow", "wideGlow"):
    assert f"{name}Enabled: true" in CLOSE, "CloseButton comparison baseline absent"

# Preserve TimeW geometry and the actual existing Unicode glyph, not a
# replacement emoji or a function that immediately resynchronizes the host.
for token in (
    "property color semanticColor: Colors.yellow",
    "property color hoverSurfaceColor: Colors.orange",
    "implicitWidth: 35", "implicitHeight: 32",
    "width: implicitWidth", "height: implicitHeight",
    'label: "⟳"', "labelPixelSize: 22", "contentPadding: 3",
    "acceptedButtons: Qt.LeftButton", 'Accessible.name: "Reload"',
    "destructive: false", "accentColor: semanticColor",
    "signal reloadRequested()",
    "onLeftClicked: reloadButton.reloadRequested()",
):
    require(token)

# The semantic glyph and border stay yellow while orange serves only as
# the hover/selected surface; press swaps to a yellow surface with black ink.
expected_colors = {
    "idleFillColor": "Colors.black",
    "hoverFillColor": "hoverSurfaceColor",
    "pressedFillColor": "accentColor",
    "selectedFillColor": "hoverSurfaceColor",
    "keyboardSelectedFillColor": "hoverSurfaceColor",
    "idleForegroundColor": "accentColor",
    "hoverForegroundColor": "accentColor",
    "pressedForegroundColor": "Colors.black",
    "selectedForegroundColor": "accentColor",
    "keyboardSelectedForegroundColor": "accentColor",
    "idleBorderColor": "accentColor",
    "hoverBorderColor": "accentColor",
    "pressedBorderColor": "Colors.black",
    "selectedBorderColor": "accentColor",
    "keyboardSelectedBorderColor": "accentColor",
}
for prop, value in expected_colors.items():
    assert re.search(rf"(?m)^\s*{prop}:\s*{re.escape(value)}\s*$", RELOAD), prop
for stage in ("idle", "hover", "pressed", "selected", "keyboardSelected"):
    for layer in ("ContentGlow", "SoftGlow", "WideGlow"):
        require(f"{stage}{layer}Color: accentColor")
for prop in (
    "idleBorderWidth: 1", "hoverBorderWidth: 1",
    "pressedBorderWidth: 1", "selectedBorderWidth: 1",
    "keyboardSelectedBorderWidth: 1",
    "radius: 0", "clip: false",
    "trackLabelGlowLocally: true", "contentGlowEnabled: true",
    "contentGlowRadius: 7", "contentGlowSamples: 7",
    "softGlowEnabled: true", "softGlowSpread: 3", "softGlowMargin: 0",
    "wideGlowEnabled: true", "wideGlowSpread: 10",
):
    require(prop)

# Exactly the same three-plane intensity recipe as the existing X, even
# when pressed, while every glow's COLOR follows this button's semantic hue.
for prefix in ("contentGlow", "softGlow", "wideGlow"):
    for suffix in ("Idle", "Hover", "Pressed", "Selected", "KeyboardSelected"):
        key = prefix + suffix + "Opacity"
        expression = rf"(?m)^\s*{key}:\s*([^\s]+)\s*$"
        new_value = re.search(expression, RELOAD)
        x_value = re.search(expression, CLOSE)
        assert new_value and x_value and new_value.group(1) == x_value.group(1), key

for token in (
    "property Item contentGlowSource:", "showLabel ? labelText : contentHost",
    "actionButton.contentGlowSource === labelText",
    "contentHost.x + labelText.x", "contentHost.y + labelText.y",
    "safeSource: actionButton.contentGlowSource",
):
    assert token in BASE, f"base glyph-sampling invariant missing {token!r}"

for forbidden in (
    "MouseArea {", "DropShadow {", "SafeDropShadow {",
    "RectangularShadow {", "TimeSettings.", "menuOpen =",
    "quickshell --", "Process {", "onTriggered:",
):
    assert forbidden not in RELOAD, f"shared button owns forbidden behavior {forbidden!r}"

header = TIME.split("id: header", 1)[1].split("id: headerDivider", 1)[0]
assert header.count("ReloadButton {") == 1
assert 'id: syncButton' in header
assert 'semanticColor: Colors.yellow' in header
assert 'hoverSurfaceColor: Colors.orange' in header
assert 'Accessible.name: "Time resync options"' in header
assert 'selected: timew.resyncPopupOpen' in header
assert 'onReloadRequested: timew.toggleResyncPopup()' in header
assert "onLeftClicked: timew.toggleResyncPopup()" not in header
assert "function toggleResyncPopup()" in TIME
assert "TimeSettings.prepareResync();" in TIME
assert "function dismissResyncPopup()" in TIME
assert "syncButton.width" in header, "TimeW responsive header must retain width binding"
assert "CloseButton {" in header and "onCloseRequested: timew.menuOpen = false" in header

print("Shared ReloadButton semantic colors, 3-plane glow and TimeW wiring: PASS")
