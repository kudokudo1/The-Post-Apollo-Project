#!/usr/bin/env python3
"""Source contracts for the FinanceW UI-only navigation scaffold."""

from pathlib import Path

root = Path(__file__).resolve().parents[2]
menu = (root / "widgets/FinanceW.qml").read_text(encoding="utf-8")

main_modes = [
    ('"budget"', '"Budget"', '"⋆$🗓₊˚"'),
    ('"market"', '"Market"', '"₊˚$🗠๋࣭⭑"'),
    ('"radar"', '"Radar"', '"࣪ ˖(˓🛰₊˚⊹"'),
    ('"research"', '"Research"', '"⋆˚🗃₊"'),
    ('"strategies"', '"Strategies"', '"˙°⚖︎๋࣭⭑"'),
    ('"safety"', '"Safety"', '"🛡๋࣭⭑"'),
    ('"agentic"', '"Agentic"', '"⋆˚⚡︎๋࣭⭑"'),
    ('"later-shop"', '"Later"', '"🛍"'),
    ('"later-print"', '"Later"', '"🖨"'),
]
sub_modes = [
    ('"budget"', '"Budget"', '"˗ˋˏ˖⛁⛀๋࣭⭑ˎˊ˗"'),
    ('"reports"', '"Reports"', '"₊˚$🗠๋࣭⭑"'),
    ('"schedules"', '"Schedules"', '"⋆$🗓₊˚"'),
]
for key, label, glyph in main_modes + sub_modes:
    assert f"id: {key}, name: {label}, icon: {glyph}" in menu, (key, glyph)
assert menu.count("future: true") == 2
assert 'interactive: !modelData.future' in menu
assert 'primaryGlowEnabled: !modelData.future' in menu
assert 'if (mainModes[i].id === id && !mainModes[i].future)' in menu
assert 'property string selectedMainMode: "budget"' in menu
assert 'property string selectedBudgetSubMode: "budget"' in menu
assert 'onTriggered: root.selectMainMode(modelData.id)' in menu
assert 'onLeftClicked: root.selectedBudgetSubMode = modelData.id' in menu

# Reuse the standard controls instead of introducing custom MouseAreas.
assert menu.count("ModeButton {") == 1
assert menu.count("ActionButton {") == 2
assert "MouseArea {" not in menu

# Distinct header, divider, and canonical U+00D7 close control.
assert "id: financeHeader" in menu
assert "color: Colors.magenta" in menu
assert "id: headerDivider" in menu
assert "color: Colors.cyan" in menu
assert 'label: "×"' in menu
assert "onLeftClicked: root.menuOpen = false" in menu
assert "id: mainModeRail" in menu
assert "id: budgetSubRail" in menu
assert 'visible: root.selectedMainMode === "budget"' in menu

# Specialized sub-mode foreground + independent glow.
assert 'id === "budget" ? Colors.omnitrix' in menu
assert 'id === "reports" ? Colors.white : Colors.green' in menu
assert 'id === "schedules" ? Colors.green : Colors.omnitrix' in menu
for line in (
    "idleContentGlowColor: identityGlow",
    "hoverContentGlowColor: identityGlow",
    "selectedContentGlowColor: identityGlow",
    "contentGlowSource: subIcon",
):
    assert line in menu, line

# Preserve the 9:16 surface, mapped-close safety and zero backend scope.
assert "readonly property int frameWidth: 432" in menu
assert "readonly property int frameHeight: 768" in menu
assert "visible: true" in menu
assert "width: root.menuOpen ? root.frameWidth : 0" in menu
assert "WlrLayershell.keyboardFocus: WlrKeyboardFocus.None" in menu
for forbidden in ("Process {", "Actual", "fetch(", "Qt.openUrlExternally", "Sqlite"):
    assert forbidden not in menu, forbidden

print("FinanceW navigation scaffold contracts: PASS")
