#!/usr/bin/env python3
"""TASKS minimal mapped menu: stable geometry, safe closed input, real close."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MENU = (ROOT / "widgets/TasksW.qml").read_text(encoding="utf-8")
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")

# Reuse actual FinanceW/TimeW chassis geometry; dock width remains independent.
assert "PanelWindow {" in MENU
assert 'import "Quickshell"' not in MENU  # built-in imports, not string imports
assert 'import "../components"' in MENU
assert "readonly property int frameWidth: 432" in MENU
assert "readonly property int frameHeight: 768" in MENU
assert "readonly property int glowGutter: 12" in MENU
assert "readonly property int frameTopInset: 9" in MENU
assert "implicitWidth: frameWidth + glowGutter * 2" in MENU
assert "implicitHeight: frameHeight + frameTopInset + glowGutter" in MENU
assert "y: root.frameTopInset" in MENU
assert "anchors.topMargin: root.frameTopInset" in MENU
assert "dockCenterX - root.implicitWidth / 2" in MENU
assert "root.chassisTopY - root.glowGutter" in MENU
assert "root.screen ? root.screen.width - root.implicitWidth : 0" in MENU

# Leave the Wayland surface mapped and empty its pointer mask when closed.
assert "WlrLayershell.layer: WlrLayer.Overlay" in MENU
assert "WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None" in MENU
assert 'focusable: root.menuOpen && (root.activeMode.id === "tasks"' in MENU
assert "visible: true" in MENU
assert "mask: Region {" in MENU
assert "width: root.menuOpen ? root.frameWidth : 0" in MENU
assert "height: root.menuOpen ? root.frameHeight : 0" in MENU
assert "visible: root.menuOpen" in MENU
assert "menuOpen = !menuOpen;" in MENU
assert "onLeftClicked: root.menuOpen = false" in MENU

# Standard chrome and truthful empty state; avoid invented task data.
assert "WindowPanelFrame {" in MENU
assert "fillColor: Colors.black" in MENU
assert "borderColor: Colors.cyan" in MENU
assert "glowColor: Colors.cyan" in MENU
assert 'text: "TASKS // " + root.activeMode.label' in MENU
assert "color: Colors.magenta" in MENU
assert "height: 2" in MENU
assert 'label: "×"' in MENU
assert "destructive: true" in MENU
assert "text: root.feedStatus" in MENU
assert 'emptyTitle: "NO TASKS LOADED"' in MENU
assert 'emptyDetail: "LOCAL CHECKLIST"' in MENU

# Five independent main modes, selected from one existing menu and
# rendered by ModeButton instead of five ad hoc click/halo implementations.
expected_modes = ("tasks", "today", "projects", "planner", "sync")
assert "readonly property var mainModes: [" in MENU
for mode_id in expected_modes:
    assert f'id: "{mode_id}"' in MENU
assert MENU.count("emptyTitle: ") == len(expected_modes)
assert MENU.count("emptyDetail: ") == len(expected_modes)
assert 'property int selectedMainModeIndex: 0' in MENU
assert "readonly property var activeMode: mainModes[selectedMainModeIndex]" in MENU
assert "function selectMainMode(index)" in MENU
assert "if (index >= 0 && index < mainModes.length)" in MENU
assert "selectedMainModeIndex = index;" in MENU
assert "id: mainModeRail" in MENU
assert "model: root.mainModes" in MENU
assert MENU.count("ModeButton {") == 1
assert "textOnly: true" in MENU
assert "bordered: false" in MENU
assert "selected: root.selectedMainModeIndex === index" in MENU
assert "onTriggered: root.selectMainMode(index)" in MENU
assert "text: root.activeMode.emptyTitle" in MENU
assert "text: root.activeMode.emptyDetail" in MENU
assert "anchors.left: mainModeRail.right" in MENU
assert "WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None" in MENU
assert 'focusable: root.menuOpen && (root.activeMode.id === "tasks"' in MENU

for forbidden in (
    "Process {", "FileView {", "JsonAdapter {", "Timer {",
    "Qt.openUrlExternally", "fetch(", "running: true",
):
    assert forbidden not in MENU, forbidden

assert "TasksW {" in SHELL
print("TASKS basic menu contracts: PASS")
