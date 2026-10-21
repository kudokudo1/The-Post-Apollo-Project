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

# Match the chassis background; accent lives in the title, not a tinted header.
assert 'text: "FINANCE // " + root.mainModeName().toUpperCase()' in menu
header = menu[menu.index("id: financeHeader"):menu.index("id: headerDivider")]
assert 'color: "transparent"' in header
assert "opacity: 0.20" not in header
header_divider = menu[menu.index("id: headerDivider"):menu.index("// MAIN MODE")]
assert "anchors.leftMargin: 12" in header_divider
assert "anchors.rightMargin: 12" in header_divider

# Main and Budget sub-mode icon artwork uses Gohu, with fit to avoid
# truncating decorated glyphs in the narrow 9:16 panel.
assert "NotoText {" not in menu
assert "GohuText {\n                        id: mainIcon" in menu
assert "GohuText {\n                            id: subIcon" in menu
assert "font.pixelSize: 24" in menu
assert "font.pixelSize: 22" in menu
assert menu.count("fontSizeMode: Text.Fit") == 2
assert "minimumPixelSize: 15" in menu
assert "minimumPixelSize: 12" in menu
assert "opacity: mainModeButton.selected ? 0.60 : 0.36" in menu

# Permanent Omnitrix vertical line with independent, source-safe glow.
divider = menu[menu.index("id: mainRailDivider"):menu.index("id: workArea")]
assert "width: 2" in divider
assert "color: Colors.omnitrix" in divider
assert "id: mainRailDividerGlow" in divider
assert "safeSource: mainRailDivider" in divider
assert "radius: 10" in divider
assert "samples: 21" in divider

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
