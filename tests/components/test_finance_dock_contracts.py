#!/usr/bin/env python3
"""FinanceW dock and blank 9:16 menu source contract (no provider or writes)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")
FINANCE = (ROOT / "modules/Finance.qml").read_text(encoding="utf-8")
MENU = (ROOT / "widgets/FinanceW.qml").read_text(encoding="utf-8")

# Left-to-right top dock order: Media, Hospital, Finance, Git.
assert SHELL.count("        Mediaplayer {") == 1
assert SHELL.index("        Mediaplayer {") < SHELL.index("        // Hospital") < SHELL.index("HospitalW {") < SHELL.index("        // Finance") < SHELL.index("FinanceW {") < SHELL.index("        // Git", SHELL.index("        // Finance"))
assert SHELL.count("            Finance {") == 1
assert SHELL.count("            FinanceW {") == 1
assert "menuOpen: financeWindow.menuOpen" in SHELL
assert "onToggleRequested: financeWindow.toggle()" in SHELL
assert "dockCenterX: shellRoot.margins.left + leftModules.x" in SHELL
assert "chassisTopY: hospitalWindow.panelTopMargin" in SHELL
assert "+ hospitalWindow.topGlowGutter" in SHELL
assert "dockBottomY:" not in SHELL
assert "DockButton {" in FINANCE
assert 'import "../components"' in FINANCE

# Do not normalize the operator's decorated identity or lose combining marks.
assert 'text: "˗ˋˏ˖<font color=\'" + financeDock.coinColor + "\'>⛁⛀</font>๋࣭⭑ˎˊ˗"' in FINANCE
assert "readonly property color coinColor: menuOpen ? Colors.magenta : Colors.green" in FINANCE
assert "textFormat: Text.StyledText" in FINANCE
assert "implicitWidth: Math.max(80, Math.ceil(financeMark.implicitWidth) + 24)" in FINANCE
assert "contentGlowSource: financeMark" in FINANCE
assert "open: menuOpen" in FINANCE
assert "onLeftClicked: toggleRequested()" in FINANCE
assert "color: financeDock.foregroundColor" in FINANCE
assert "⛀⛁ ⛁⛀" not in FINANCE

# Idle: green coins/white decoration; open: all magenta.
for state in ("normal", "hover", "pressed"):
    assert f"{state}ForegroundColor: Colors.white" in FINANCE
assert "openForegroundColor: Colors.magenta" in FINANCE
for state in ("normal", "hover", "pressed"):
    assert f"{state}ContentGlowColor: Colors.omnitrix" in FINANCE
    assert f"{state}DockGlowColor: Colors.omnitrix" in FINANCE
assert "openFillColor: Colors.yellow" in FINANCE
assert "openGlowColor: Colors.magenta" in FINANCE

# No backend, duplicate click area, or duplicated glow machinery.
for forbidden in (
    "FinanceW {", "Process {", "onRightClicked:",
    "MouseArea {", "SafeDropShadow {", "RectangularShadow {",
):
    assert forbidden not in FINANCE, forbidden

# FinanceW begins at 9:16 compact, then resizes its one mapped window.
assert "PanelWindow {" in MENU
assert "readonly property int frameWidth: chassisFrame.width" in MENU
assert "readonly property int frameHeight: chassisFrame.height" in MENU
assert "implicitWidth: frameWidth + glowGutter * 2" in MENU
assert "implicitHeight: frameHeight + frameTopInset + bottomScreenGap" in MENU
assert "readonly property int frameTopInset: 9" in MENU
assert "readonly property int bottomScreenGap: 8" in MENU
assert "anchors.bottomMargin: root.bottomScreenGap" in MENU
assert "property real dockCenterX: 0" in MENU
assert "property real chassisTopY: 0" in MENU
assert "FinanceChassisPolicy.leftMargin(" in MENU
assert "FinanceChassisPolicy.topMargin(" in MENU
assert "root.chassisLevel, root.chassisTopY," in MENU
assert "dockBottomY" not in MENU
assert "buttonGap" not in MENU
assert "visible: true" in MENU  # do not remap layer-shell for toggles
assert "visible: root.menuOpen" in MENU  # only the inner chassis hides
assert "width: root.menuOpen ? root.frameWidth : 0" in MENU
assert "height: root.menuOpen ? root.frameHeight : 0" in MENU
assert "WlrKeyboardFocus.None" in MENU
assert "WlrKeyboardFocus.OnDemand" in MENU
assert "WlrKeyboardFocus.Exclusive" in MENU
assert "focusable: root.menuOpen && root.keyboardActive" in MENU
assert "keyboardLock" in MENU
assert "id: financeKeyboardAnchor" in MENU
assert "WindowPanelFrame {" in MENU
assert "glowColor: Colors.omnitrix" in MENU
assert "radius: 0" in MENU
assert "borderColor: Colors.omnitrix" in MENU
assert "menuOpen = !menuOpen;" in MENU

for forbidden in ("Process {", "Actual", "fetch(", "Qt.openUrlExternally"):
    assert forbidden not in MENU, forbidden

print("FinanceW dock and blank portrait menu contracts: PASS")
