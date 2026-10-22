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
assert "implicitWidth: frameWidth + glowGutter * 2" in MENU
assert "implicitHeight: frameHeight + glowGutter * 2" in MENU
assert "dockCenterX - root.implicitWidth / 2" in MENU
assert "root.chassisTopY - root.glowGutter" in MENU
assert "root.screen ? root.screen.width - root.implicitWidth : 0" in MENU

# Leave the Wayland surface mapped and empty its pointer mask when closed.
assert "WlrLayershell.layer: WlrLayer.Overlay" in MENU
assert "WlrLayershell.keyboardFocus: WlrKeyboardFocus.None" in MENU
assert "focusable: false" in MENU
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
assert 'text: "TASKS // HOME"' in MENU
assert "color: Colors.magenta" in MENU
assert "height: 2" in MENU
assert 'label: "×"' in MENU
assert "destructive: true" in MENU
assert 'text: "NO FEED"' in MENU
assert 'text: "NO TASKS LOADED"' in MENU
assert 'text: "TASK EDITOR // NOT CONNECTED"' in MENU

for forbidden in (
    "Process {", "FileView {", "JsonAdapter {", "Timer {",
    "Qt.openUrlExternally", "fetch(", "running: true",
):
    assert forbidden not in MENU, forbidden

assert "TasksW {" in SHELL
print("TASKS basic menu contracts: PASS")
