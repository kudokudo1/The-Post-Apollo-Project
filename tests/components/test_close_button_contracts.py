#!/usr/bin/env python3
"""Contract for the operator-approved universal ordinary window Close ×.

This intentionally does NOT migrate any existing widgets.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CLOSE = (ROOT / "components/CloseButton.qml").read_text(encoding="utf-8")
BASE = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")


def has(value: str) -> None:
    assert value in CLOSE, f"missing CloseButton contract: {value}"


assert re.search(r"(?m)^ActionButton\s*\{", CLOSE)
assert "CloseButton 1.0 CloseButton.qml" in QMLDIR

# Geometry, Finance reference layout, and canonical multiplication sign.
for value in (
    "implicitWidth: 34",
    "implicitHeight: 32",
    "height: width * 16 / 17",
    "recommendedLeftGap: 7",
    "recommendedRightInset: 10",
    "recommendedVerticalClearance: 12",
    'label: "×"',
    "labelPixelSize: Math.round(width * 22 / 34)",
    "contentPadding: 4",
    "radius: 0",
):
    has(value)

# Close-only semantics: not a destructive action and not an implicit window kill.
for value in (
    "destructive: false",
    "acceptedButtons: Qt.LeftButton",
    'Accessible.name: "Close"',
    "signal closeRequested()",
    "onLeftClicked: closeButton.closeRequested()",
):
    has(value)
assert not re.search(r"\b(?:root|window)\.close\(", CLOSE)
assert "MouseArea {" not in CLOSE
assert "DropShadow {" not in CLOSE
assert "RectangularShadow {" not in CLOSE

# Filled surfaces, red semantic identity, and black pressed foreground/border.
expected_colors = {
    "idleFillColor": "Colors.black",
    "hoverFillColor": "Colors.yellow",
    "pressedFillColor": "Colors.red",
    "idleForegroundColor": "Colors.red",
    "hoverForegroundColor": "Colors.red",
    "pressedForegroundColor": "Colors.black",
    "idleBorderColor": "Colors.red",
    "hoverBorderColor": "Colors.red",
    "pressedBorderColor": "Colors.black",
}
for key, val in expected_colors.items():
    assert re.search(rf"(?m)^\s*{key}:\s*{re.escape(val)}\s*$", CLOSE), key

# Three independently controlled glow planes, none zero in ANY visible state.
for prefix, state_values in (
    ("contentGlow", {"Idle": .34, "Hover": .72, "Pressed": 1.0, "Selected": .72, "KeyboardSelected": .72}),
    ("softGlow", {"Idle": .48, "Hover": .70, "Pressed": 1.0, "Selected": .70, "KeyboardSelected": .70}),
    ("wideGlow", {"Idle": .22, "Hover": .32, "Pressed": 1.0, "Selected": .32, "KeyboardSelected": .32}),
):
    has(f"{prefix}Enabled: true")
    for state, val in state_values.items():
        key = f"{prefix}{state}Opacity"
        pattern = rf"(?m)^\s*{key}:\s*{val:.2f}\s*$"
        # 1.0 is kept in source instead of an unnecessary 1.00 presentation.
        if val == 1.0:
            pattern = rf"(?m)^\s*{key}:\s*1(?:\.0+)?\s*$"
        assert re.search(pattern, CLOSE), f"{key}: expected {val}"

    for state in ("idle", "hover", "pressed", "selected", "keyboardSelected"):
        has(f"{state}{prefix[0].upper() + prefix[1:]}Color: Colors.red")

for needle in (
    "trackLabelGlowLocally: true",
    "contentGlowRadius: 7",
    "contentGlowSamples: 7",
    "softGlowSpread: 3",
    "wideGlowSpread: 10",
):
    has(needle)

# The actual label is the sampled effect source; no second painted X.
for token in (
    "property Item contentGlowSource:",
    "showLabel ? labelText : contentHost",
    "actionButton.contentGlowSource === labelText",
    "contentHost.x + labelText.x",
    "contentHost.y + labelText.y",
    "safeSource: actionButton.contentGlowSource",
):
    assert token in BASE, f"base glyph-sampling invariant missing: {token}"

print("Universal CloseButton source contracts: PASS")
