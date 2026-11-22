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

# Yellow is canonical; purple is a distinct local theme identity, NOT a
# fabricated Colors.purple or the existing magenta pressed interaction shade.
present("property color decreaseAccentColor: Colors.yellow")
present('property color increaseAccentColor: "#A46AFF"')
present("accentColor: increasing ? increaseAccentColor : decreaseAccentColor")
assert 'readonly property color yellow:' in COLORS
assert not re.search(r"(?m)^\s*readonly property color purple:", COLORS)
assert "Colors.magenta" not in RESIZE

# Ordinary ActionButton states and effect intensities must be inherited EXACTLY.
# No custom hover, pressed, unavailable, glow palette or shadow constructed here.
for prop in (
    "destructive", "idleFillColor", "hoverFillColor", "pressedFillColor",
    "idleForegroundColor", "hoverForegroundColor", "pressedForegroundColor",
    "idleBorderColor", "hoverBorderColor", "pressedBorderColor",
    "contentGlowEnabled", "contentGlowSource", "contentGlowIdleOpacity",
    "contentGlowHoverOpacity", "contentGlowPressedOpacity",
    "softGlowEnabled", "softGlowIdleOpacity", "softGlowHoverOpacity",
    "softGlowPressedOpacity", "wideGlowEnabled", "wideGlowIdleOpacity",
    "wideGlowHoverOpacity", "wideGlowPressedOpacity",
    "unavailableOpacity", "unavailableContentGlowOpacity",
    "unavailableSoftGlowOpacity", "unavailableWideGlowOpacity",
    "trackLabelGlowLocally", "selectedFillColor", "keyboardSelectedFillColor",
):
    assert not re.search(rf"(?m)^\s*{prop}\s*:", RESIZE), f"must inherit {prop}"

for token in (
    "property color hoverFillColor: Colors.yellow",
    "property color hoverForegroundColor: Colors.orange",
    "property color pressedFillColor:",
    "destructive ? destructiveColor : Colors.magenta",
    "property color pressedForegroundColor: Colors.black",
    "property real contentGlowIdleOpacity: 0.34",
    "property real contentGlowHoverOpacity: 0.72",
    "property real contentGlowPressedOpacity: 0.0",
    "property real softGlowIdleOpacity: 0.22",
    "property real softGlowHoverOpacity: 0.56",
    "property real softGlowPressedOpacity: 0.60",
    "property bool wideGlowEnabled: false",
    "property bool trackLabelGlowLocally: true",
    "safeSource: actionButton.contentGlowSource",
):
    assert token in BASE, f"underlying shared state contract changed: {token}"

for forbidden in (
    "MouseArea {", "DropShadow {", "SafeDropShadow {",
    "RectangularShadow {", "setGeometry(", "chassisLevel =",
    "menuOpen =", "root.close()", "onTriggered:",
):
    assert forbidden not in RESIZE, f"resize component owns forbidden work {forbidden}"

print("Universal ResizeButton source contract: PASS")
