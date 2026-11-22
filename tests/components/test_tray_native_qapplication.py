#!/usr/bin/env python3
"""Tray native-menu bootstrap: QtWidgets support is a ROOT application property.

Source-only checks; do not launch a second Quickshell or touch the user's tray.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
tray = (ROOT / "modules/Tray.qml").read_text(encoding="utf-8")

# Qt's native platform menus require QApplication rather than the default
# QGuiApplication. This must be a top-of-file INSTANCE pragma in shell.qml,
# not a comment in Tray.qml, imported component, or late runtime property.
assert shell.splitlines()[0] == "//@ pragma UseQApplication"
assert shell.count("//@ pragma UseQApplication") == 1
assert shell.splitlines()[1] == "import Quickshell"
assert "PanelWindow {" in shell

# The standard menu owner remains Quickshell's StatusNotifier item.
# Lutris retains its application-owned menu rather than a synthetic action
# or an unchecked shell/DBus process invocation.
assert "import Quickshell.Services.SystemTray" in tray
assert "model: SystemTray.items" in tray
assert "QsMenuAnchor {" in tray
assert "menu: trayButton.modelData.menu" in tray
assert "anchor.item: trayButton" in tray
assert "trayNativeMenu.open();" in tray
assert "isLutrisTrayItem" in tray
assert "isDiscordTrayItem" in tray
assert "SocialTrayBridge.requestDiscordActivation();" in tray
assert "trayButton.modelData.activate();" in tray
assert "Process {" not in tray
assert "WlrLayershell" not in tray
print("Tray native QtWidgets menu backend / existing item action boundary: PASS")
