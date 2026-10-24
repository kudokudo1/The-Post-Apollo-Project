#!/usr/bin/env python3
"""Source contracts for FinanceW navigation and icon controls."""

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
assert "onTriggered: {" in menu
assert "root.selectMainMode(modelData.id);" in menu
assert "onLeftClicked: {" in menu
assert "root.selectedBudgetSubMode = modelData.id;" in menu
assert "root.keyboardOwnershipRequested();" in menu

# Reuse the standard controls instead of introducing custom MouseAreas.
assert menu.count("ModeButton {") == 1
# Existing controls plus local-draft actions, ALLOCATE and CHECK WRITE LOCK.
# Navigation grammar remains unchanged; no custom MouseArea introduced.
assert menu.count("ActionButton {") == 21  # two reversible M0 size controls
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
assert "Item {\n                        id: mainIcon" in menu
assert "Item {\n                            id: subIcon" in menu
assert "id: mainGlyphParts" in menu
assert "id: subGlyphParts" in menu
assert "GohuText {" in menu
assert "font.pixelSize: 24" in menu
assert "font.pixelSize: 22" in menu
assert menu.count("fontSizeMode: Text.Fit") == 2
assert "minimumPixelSize: 15" in menu
assert "minimumPixelSize: 12" in menu
assert "opacity: mainModeButton.selected ? 0.60 : 0.36" in menu

# No increase in ornament size: the two core glyphs are larger, the
# decorations remain smaller and Unicode combining marks stay on the core.
segmented = {
    '"market"': ("₊˚", "$", "🗠๋࣭", "⭑", "₊˚$🗠๋࣭⭑"),
    '"radar"': ("࣪ ˖(˓", "", "🛰", "₊˚⊹", "࣪ ˖(˓🛰₊˚⊹"),
    '"strategies"': ("˙°", "", "⚖︎๋࣭", "⭑", "˙°⚖︎๋࣭⭑"),
    '"safety"': ("", "", "🛡๋࣭", "⭑", "🛡๋࣭⭑"),
    '"agentic"': ("⋆˚", "", "⚡︎๋࣭", "⭑", "⋆˚⚡︎๋࣭⭑"),
}
for key, (pre, dollar, core, post, full) in segmented.items():
    assert pre + dollar + core + post == full
    dollar_field = f'dollar: "{dollar}", ' if dollar else ""
    assert (f'prefix: "{pre}", ' + dollar_field
            + f'core: "{core}", suffix: "{post}"') in menu, key
for pre, dollar, core, post, full in (
    ("˗ˋˏ˖", "", "⛁⛀๋࣭", "⭑ˎˊ˗", "˗ˋˏ˖⛁⛀๋࣭⭑ˎˊ˗"),
    ("₊˚", "$", "🗠๋࣭", "⭑", "₊˚$🗠๋࣭⭑"),
):
    assert pre + dollar + core + post == full
    dollar_field = f'dollar: "{dollar}", ' if dollar else ""
    assert (f'prefix: "{pre}", ' + dollar_field
            + f'core: "{core}", suffix: "{post}"') in menu

# Market and Reports dollars now have the same Gohu font setting as
# Main Budget's $; chart symbols retain 34px and 31px sizes.
assert menu.count('dollar: "$"') == 2
assert menu.count('text: modelData.dollar || ""') == 2
assert menu.count("visible: !!modelData.dollar") == 2
# The 24px dollar must be vertically centered alongside each larger chart.
# Do not recenter the small stars or resize any glyphs in this follow-up.
for row_id, end_id in (("mainGlyphParts", "mainModeButton"),
                       ("subGlyphParts", "budgetSubButton")):
    start = menu.index("id: " + row_id)
    after = menu.index('visible: !!modelData.dollar', start)
    dollar_block = menu[after:menu.index("}", after)]
    assert "anchors.verticalCenter: parent.verticalCenter" in dollar_block, row_id
assert menu.count("anchors.verticalCenter: parent.verticalCenter") >= 2
assert menu.count("font.pixelSize: 24") == 3  # main Budget + two dollar glyphs
assert 'font.pixelSize: modelData.coreSize || 34' in menu
assert 'font.pixelSize: 31' in menu
for size in (31, 15, 12):
    assert f"font.pixelSize: {size}" in menu
assert "font.pixelSize: modelData.coreSize || 34" in menu
for ident, size in (("radar", 30), ("strategies", 28), ("safety", 28)):
    row = next(line for line in menu.splitlines()
               if f'id: "{ident}", name:' in line)
    assert f'coreSize: {size}' in row, (ident, row)
for ident in ("market", "agentic"):
    row = next(line for line in menu.splitlines()
               if f'id: "{ident}", name:' in line)
    assert "coreSize:" not in row, (ident, row)
assert menu.count("coreSize:") == 3
assert "scale: Math.min(1, mainIcon.width" in menu
assert "scale: Math.min(1, subIcon.width" in menu
# Ornaments are vertically centered relative to the larger core glyph
# while retaining the 15/12 px small decorations and original source strings.
for row_id, ornament_px, expected_color in (
    ("mainGlyphParts", 15, "mainModeButton.primaryColor"),
    ("subGlyphParts", 12, "budgetSubButton.foregroundColor"),
):
    row = menu[menu.index("id: " + row_id):]
    for ornament in ("prefix", "suffix"):
        marker = 'text: modelData.' + ornament + ' || ""'
        pos = row.index(marker)
        block = row[row.rfind("GohuText {", 0, pos):row.index("}", pos)]
        assert "anchors.verticalCenter: parent.verticalCenter" in block, (row_id, ornament)
        assert f"font.pixelSize: {ornament_px}" in block, (row_id, ornament)
        assert f"color: {expected_color}" in block, (row_id, ornament)
assert menu.count('anchors.verticalCenter: parent.verticalCenter') >= 6


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
assert "readonly property int frameWidth: chassisFrame.width" in menu
assert "readonly property int frameHeight: chassisFrame.height" in menu
assert "visible: true" in menu
assert "width: root.menuOpen ? root.frameWidth : 0" in menu
assert "WlrKeyboardFocus.None" in menu
assert "WlrKeyboardFocus.OnDemand" in menu
assert "WlrKeyboardFocus.Exclusive" in menu
assert "property bool keyboardActive: false" in menu
assert "property bool keyboardLock: false" in menu
assert "id: financeKeyboardAnchor" in menu
assert "menuOpen && keyboardActive" in menu
for sequence in ("Tab", "Shift+Tab", "Shift+Left", "Shift+Right",
                 "Up", "Down", "Left", "Right", "Return", "Enter", "Esc"):
    assert f'sequence: "{sequence}"' in menu, sequence
assert "context: Qt.WindowShortcut" in menu
assert "enabled: root.standardKeysAvailable" in menu
assert "root.menuOpen = false" in menu
assert "activeMainModes().length" in menu
assert "return mainModes.filter(function(mode) { return !mode.future; });" in menu
assert "root.moveNavigationZone(-1)" in menu
assert "root.activateNavigationCursor()" in menu
for forbidden in ("Process {", "Actual", "fetch(", "Qt.openUrlExternally", "Sqlite"):
    assert forbidden not in menu, forbidden

print("FinanceW navigation scaffold contracts: PASS")
