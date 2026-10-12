#!/usr/bin/env python3
"""Static Main Mode component contracts; runtime/visual testing remains separate."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "components"
mode = (COMP / "ModeButton.qml").read_text(encoding="utf-8")
close = (COMP / "ModeButtonCloseHalo.qml").read_text(encoding="utf-8")
wide = (COMP / "ModeButtonWideHalo.qml").read_text(encoding="utf-8")
hash_glow = (COMP / "TextHashGlow.qml").read_text(encoding="utf-8")
recipes = (COMP / "VisualLanguage.qml").read_text(encoding="utf-8")
qmldir = (COMP / "qmldir").read_text(encoding="utf-8")

assert "ModeButton 1.0 ModeButton.qml" in qmldir
assert not (COMP / "ModeButton.qml.template").exists()
assert "default property alias contentData: customContentHost.data" in mode
for token in (
    "property bool customArtwork: false",
    "property bool horizontalContent: false",
    "property bool textOnly: false",
    "property bool keyboardActive: false",
    "property bool keyboardSelected: false",
    "readonly property bool secondaryHovered:",
    "keyboardActive && pointerInside && !keyboardSelected",
    "onPositionChanged: modeButton.pointerMoved()",
    "onClicked: modeButton.triggered()",
    "property bool bordered: false",
    "property real borderThickness: 1",
    "property color idleFillColor: Colors.black",
    "property color selectedFillColor: Colors.yellow",
    "property color hoveredFillColor: Colors.yellow",
    "property color pressedFillColor: Colors.magenta",
    "property color pressedBorderColor: Colors.black",
    "property color perimeterGlowColor: Colors.orange",
    "color: modeButton.textOnly",
    "quietOpacity: modeButton.textOnly",
    "requestedVisible: modeButton.primaryGlowEnabled",
    "requestedVisible: modeButton.labelGlowEnabled",
    "modeButtonRecipe: true",
    "ModeButtonCloseHalo {",
    "ModeButtonWideHalo {",
    "safeSource: modeButton.primaryGlowSource",
    "safeSource: modeButton.labelGlowSource",
):
    assert token in mode, f"Main Mode component missing: {token}"
assert "implicitWidth:" not in mode and "implicitHeight:" not in mode
assert "pressed ? pressedBorderColor" in mode
assert "primaryHovered ? hoveredFillColor" in mode
assert "selected ? selectedFillColor" in mode
assert "selected ? selectedPrimaryColor" in mode
assert "hovered ? hoverPrimaryColor" in mode
assert "hovered ? hoverPrimaryColor" in mode
for effect, spread, z in ((close, "modeCloseSpread", "-1"), (wide, "modeWideSpread", "1")):
    assert f"spread: VisualLanguage.{spread}" in effect
    assert f"z: {z}" in effect
    assert "modeHaloPressedStrength" in effect
    assert "modeHaloSelectedStrength" in effect
    assert "modeHaloHoverStrength" in effect
    assert "glowStrength:" in effect
for token in ("property bool modeButtonRecipe: false", "property bool modeSelected: false",
              "property bool modeHovered: false", "modeIconIdleRadius",
              "modeIconSelectedSamples", "modeIconIdleOpacity", "safeSource.mapToItem"):
    assert token in hash_glow, f"TextHashGlow missing: {token}"
for token in (
    "modeIconIdleOpacity: 0.40", "modeIconHoverOpacity: 0.80",
    "modeIconSelectedOpacity: 1.00", "modeIconIdleRadius: 10",
    "modeIconHoverRadius: 14", "modeIconSelectedRadius: 18",
    "modeIconIdleSamples: 7", "modeIconHoverSamples: 9",
    "modeIconSelectedSamples: 17", "modeCloseSpread: 3",
    "modeWideSpread: 10", "modeHaloColor: Colors.orange",
    "modeLabelIdleOpacity: 0.34", "modeLabelActiveOpacity: 0.48",
    "modeLabelPressedOpacity: 0.42", "modeLabelGlowIdleOpacity: 0.06",
    "modeLabelGlowActiveOpacity: 0.10",
):
    assert token in recipes, f"Main Mode recipe missing: {token}"
print("Main Mode button contracts: PASS")
