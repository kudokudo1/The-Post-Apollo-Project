#!/usr/bin/env python3
"""Operator-approved resize-arrow component, read-only source contract.

No widget migration, fake chassis updates, or Syntagma changes in this test.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RESIZE = (ROOT / "components/ResizeButton.qml").read_text(encoding="utf-8")
BASE = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")
COLORS = (ROOT / "components/Colors.qml").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")


def present(token: str):
    assert token in RESIZE, f"ResizeButton missing {token!r}"


assert re.search(r"(?m)^ActionButton\s*\{", RESIZE)
assert "ResizeButton 1.0 ResizeButton.qml" in QMLDIR

# Finance baseline: square 30px, 17px arrow, compact width override to 28px.
for token in (
    "implicitWidth: 30",
    "implicitHeight: 30",
    "width: implicitWidth",
    "height: width",
    "labelPixelSize: 17",
):
    present(token)

# Optical centering is owned by the shared ResizeButton, not Finance or
# another consumer. ActionButton defaults stay zero for every other button.
for token in (
    "property real labelCenterOffsetX: 0",
    "property real labelCenterOffsetY: 0",
    "property alias labelItem: labelText",
    "anchors.horizontalCenterOffset: actionButton.labelCenterOffsetX",
    "anchors.verticalCenterOffset: actionButton.labelCenterOffsetY",
):
    assert token in BASE, f"base opt-in centering hook missing: {token}"

for token in (
    "TextMetrics {",
    "font: resizeButton.labelItem.font",
    "text: resizeButton.label",
    "arrowInk.tightBoundingRect",
    "arrowInk.advanceWidth",
    "labelCenterOffsetX:",
    "labelCenterOffsetY:",
    "resizeButton.labelItem.baselineOffset",
):
    present(token)
assert "anchors.centerIn:" not in RESIZE
assert "direction === \"up\"" in RESIZE
assert "onResizeRequested:" not in BASE

# EXACT operator-supplied code points, no ASCII/ordinary arrows.
for token in ('"⮜"', '"⮝"', '"⮟"', '"➤"'):
    present(token)
for forbidden in ('"↑"', '"↓"', '"←"', '"→"', '"X"'):
    assert forbidden not in RESIZE, forbidden

# Both axes use their directional sign; no resizing is performed here.
for token in (
    'property string direction: "down"',
    'direction === "left"',
    'direction === "up"',
    'direction === "down"',
    'direction === "right"',
    'readonly property bool directionValid:',
    'readonly property bool increasing:',
    'readonly property int sizeDelta: increasing ? 1 : -1',
    'interactive: available && directionValid',
    'signal resizeRequested(int delta)',
    'if (directionValid)',
    'resizeButton.resizeRequested(sizeDelta);',
):
    present(token)

# Decrease is canonical orange; increase retains its approved distinct purple.
present("property color decreaseAccentColor: Colors.orange")
present('property color increaseAccentColor: "#A46AFF"')
present("accentColor: increasing ? increaseAccentColor : decreaseAccentColor")
assert 'readonly property color orange:' in COLORS
assert 'readonly property color yellow:' in COLORS
assert not re.search(r"(?m)^\s*readonly property color purple:", COLORS)
assert "Colors.magenta" not in RESIZE

# CloseButton-like behavior, but each direction owns its own semantic hue.
# The widget does not duplicate text, shadows, or mouse handling.
visual_colors = {
    "idleFillColor": "Colors.black",
    "hoverFillColor": "Colors.yellow",
    "pressedFillColor": "accentColor",
    "selectedFillColor": "Colors.yellow",
    "keyboardSelectedFillColor": "Colors.yellow",
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
for prop, value in visual_colors.items():
    assert re.search(rf"(?m)^\s*{prop}:\s*{re.escape(value)}\s*$", RESIZE), (prop, value)

# Hover and press preserve the directional hue across all three glow planes.
# Use CloseButton intensities, including visible pressed glyph and wide glow.
for prefix, opacity in (
    ("contentGlow", {"Idle": .34, "Hover": .72, "Pressed": 1.0, "Selected": .72, "KeyboardSelected": .72}),
    ("softGlow", {"Idle": .48, "Hover": .70, "Pressed": 1.0, "Selected": .70, "KeyboardSelected": .70}),
    ("wideGlow", {"Idle": .22, "Hover": .32, "Pressed": 1.0, "Selected": .32, "KeyboardSelected": .32}),
):
    present(f"{prefix}Enabled: true")
    for state in ("idle", "hover", "pressed", "selected", "keyboardSelected"):
        present(f"{state}{prefix[0].upper() + prefix[1:]}Color: accentColor")
    for state, value in opacity.items():
        present(f"{prefix}{state}Opacity: {value:.2f}" if value != 1.0 else f"{prefix}{state}Opacity: 1.0")

for token in (
    "idleBorderWidth: 1",
    "hoverBorderWidth: 1",
    "pressedBorderWidth: 1",
    "selectedBorderWidth: 1",
    "keyboardSelectedBorderWidth: 1",
    "trackLabelGlowLocally: true",
    "contentGlowRadius: 7",
    "contentGlowSamples: 7",
    "softGlowSpread: 3",
    "softGlowMargin: 0",
    "wideGlowSpread: 10",
):
    present(token)

# The two existing ActionButton glow layers source the actual rendered label.
for token in (
    "property Item contentGlowSource:",
    "showLabel ? labelText : contentHost",
    "actionButton.contentGlowSource === labelText",
    "contentHost.x + labelText.x",
    "contentHost.y + labelText.y",
    "safeSource: actionButton.contentGlowSource",
):
    assert token in BASE, f"base glyph-sampling invariant missing: {token}"

for forbidden in (
    "MouseArea {", "DropShadow {", "SafeDropShadow {",
    "RectangularShadow {", "setGeometry(", "chassisLevel =",
    "menuOpen =", "root.close()", "onTriggered:",
):
    assert forbidden not in RESIZE, f"resize component owns forbidden work {forbidden}"

print("Universal ResizeButton source contract: PASS")
