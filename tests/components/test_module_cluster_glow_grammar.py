#!/usr/bin/env python3
"""Nurse 3A: dock cluster/structural-white source contracts.

These checks verify intended source construction, not visual parity in Qt.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    return (ROOT / "modules" / f"{name}.qml").read_text(encoding="utf-8")


dock = (ROOT / "components/DockButton.qml").read_text(encoding="utf-8")
# Operator-confirmed: open-magenta wins even for specialized yellow/green docks.
for state in ("contentGlowColor", "dockGlowColor"):
    match = re.search(
        rf"readonly property color {state}: open\s*\? openGlowColor",
        dock,
    )
    assert match, f"{state} must give open-magenta priority"
assert "property color openGlowColor: Colors.magenta" in dock
assert "property color openFillColor: Colors.yellow" in dock

# Ordinary icon compositions keep their original sequence with structural
# stars / separators / parentheses in white through all interaction states.
for name, source, parts in (
    ("Applauncher", "appmenuIcon", ('-⋆', '♱', '⋆-')),
    ("NotificationsHub", "text", ('-⋆', '🗒', '⋆-')),
    ("Calendar", "calendarText", (' ⌯⌲ ', '🗓', ' ⋆˙⟡ ')),
    ("Bluetooth", "bluetoothText", ('(', '˓✟˒', ')')),
    ("Git", "gitMark", ('≽', '(', '•⩊•マ≼')),
):
    qml = module(name)
    assert f"contentGlowSource: {source}" in qml, name
    positions = [qml.index(f'text: "{part}"') for part in parts]
    assert positions == sorted(positions), name
    assert qml.count("color: Colors.white") >= (1 if name == "Git" else 2), name

# Single marks remain single glow clusters. The rows above are not a
# pretext for three independent effects over fragments of one identity.
for name in ("Applauncher", "NotificationsHub", "Calendar", "Bluetooth", "Git"):
    assert "SafeDropShadow {" not in module(name), name

volume = module("Volumebar")
assert "contentGlowEnabled: false" in volume
assert 'text: "%"' in volume
assert 'return root.vol.toString();' in volume
assert 'return root.vol + "%";' not in volume
assert "safeSource: volumebarText" in volume
assert "safeSource: volumebarPercent" in volume
percent = volume[volume.index("id: volumebarPercent"):volume.index("id: textGlow")]
assert "visible: root.ready && !root.muted" in percent
assert "color: Colors.white" in percent
assert "opacity: volumebarDock.pressed ? 1.0 : volumebarDock.hovered ? 0.95 : 0.75" in volume
assert "color: !root.ready ? Colors.blue : root.muted ? Colors.yellow" in volume

tray = module("Tray")
assert re.search(r"(?m)^\s*SafeDropShadow\s*\{", tray)
assert not re.search(r"(?m)^\s*DropShadow\s*\{", tray)
assert "safeSource: trayIcon" in tray
assert "trayButtonMouse.containsMouse ? 0.95 : 0.75" in tray
assert "trayButtonHovered ? 0.09 : 0.07" in tray

workspaces = module("Workspaces")
assert workspaces.count("safeSource: workspacesText") == 2
assert "workspacesButtonHovered ? 0.09 : 0.07" in workspaces
assert workspaces.count("workspacesButtonMouse.containsMouse ? 0.95") == 2
assert workspaces.count(": 0.75") >= 2
assert "visible: workspacesWorkspaceButton.isActive" in workspaces

# Preserve documented exceptions until runtime and operator acceptance:
# Wi-Fi's inverted source icon glow, historical Power, dormant media dock.
assert "networkDock.pressed ? 0.6 : networkDock.hovered ? 0.8 : 1.0" in module("Network")
assert "softGlowSpread: 1" in module("Power")
assert "contentGlowSource: mediaArtwork" in module("Mediaplayer")

print("Dock cluster and structural-white contracts: PASS")
