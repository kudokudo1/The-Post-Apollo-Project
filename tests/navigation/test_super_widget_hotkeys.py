#!/usr/bin/env python3
"""Source safety contracts for opt-in global Super-key widget toggles.

Global Sway dispatch cannot be proved without the user's live config/seat.
This test verifies the exact eight chords route to the existing widget owners.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SWAY = (ROOT / "config/sway/post-apollo-widget-hotkeys.conf").read_text(
    encoding="utf-8")
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")
MEDIA = (ROOT / "modules/Mediaplayer.qml").read_text(encoding="utf-8")

expected = {
    "Mod4+t": "todo",
    "Mod4+m": "social",
    "Mod4+Shift+m": "finance",
    "Mod4+n": "notifications",
    "Mod4+a": "apolloHub",
    "Mod4+Shift+t": "clock",
    "Mod4+Shift+w": "weatherStation",
    "Mod4+r": "media",
}
chords = re.findall(
    r"^bindsym --no-repeat (Mod4(?:\\+Shift)?\\+[a-z])"
    r"\\s+exec qs ipc call controlMenus (\\w+)\\s*$",
    SWAY, flags=re.MULTILINE,
)
assert len(chords) == len(expected), chords
assert dict(chords) == expected, chords
assert len({chord for chord, _ in chords}) == len(expected), "duplicate chord"
assert "Mod4+grave" not in SWAY, "Koinoikos prefix must stay untouched"
assert not re.search(r"^(include|mode|exec_always|bindcode)\\b", SWAY, re.M)
assert "OPT-IN" in SWAY, "never install in a live Sway config silently"

# Reuse the one existing controlMenus endpoint. No second widget instance.
assert SHELL.count('target: "controlMenus"') == 1
handler = SHELL.split('target: "controlMenus"', 1)[1].split(
    "// ===== SERVICES", 1)[0]
routes = {
    "todo": "tasksWindow.toggle();",
    "finance": "financeWindow.toggle();",
    "notifications": "notificationsHubWindow.toggle();",
    "apolloHub": "apolloHubWindow.toggle();",
    "clock": "timewWindow.toggle();",
    "weatherStation": "weatherStationWindow.toggle();",
    "media": "sharedMediaDock.toggleDeck();",
}
for method, call in routes.items():
    assert f"function {method}(): void" in handler, method
    assert call in handler, (method, call)
assert "function social(): void" in handler
assert "Qt.callLater(function()" in handler
assert "messagingWindow.menuOpen = !messagingWindow.menuOpen;" in handler
# Existing Git/Hospital IPC methods are still intact.
assert "function git(): void" in handler
assert "function hospital(): void" in handler
assert "gitWindow.toggle();" in handler
assert "hospitalWindow.toggle();" in handler
assert "sharedMediaDock.deckOpen =" not in handler

# Media's owner must calculate initial placement for keyboard and click.
# Escape closing through the parent retains the existing QML binding.
assert MEDIA.count("function toggleDeck()") == 1
assert "onLeftClicked: mediaRoot.toggleDeck()" in MEDIA
assert "mediaDock.mapToItem(null, 0, 0).x" in MEDIA
assert "deckPanel.panelLeftMargin = Math.max(" in MEDIA
assert MEDIA.count("mediaRoot.deckOpen = !mediaRoot.deckOpen;") == 1
assert "menuOpen: mediaRoot.deckOpen" in MEDIA
assert "onCloseRequested: mediaRoot.deckOpen = false" in MEDIA

print("Super widget hotkeys source contracts: PASS")
