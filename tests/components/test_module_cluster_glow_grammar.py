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

# The icon is ONE text item, not multiple Row-positioned glyph fragments.
# Decorative text foreground follows the DockButton state: white when closed,
# magenta on open. Preserve the original single-line shaping and glow source.
for name, glow_source, glyphs in (
    ("Applauncher", "appmenuIcon", ("-⋆", "♱", "⋆-")),
    ("NotificationsHub", "text", ("-⋆", "🗒", "⋆-")),
    ("Calendar", "calendarText", (" ⌯⌲ ", "🗓", " ⋆˙⟡ ")),
    ("Bluetooth", "bluetoothText", ("(", "˓✟˒", ")")),
    ("Git", "gitMark", ("≽", "(", "•⩊•マ≼")),
):
    qml = module(name)
    assert f"contentGlowSource: {glow_source}" in qml, name
    assert qml.count("textFormat: Text.StyledText") == 1, name
    assert "anchors.centerIn: parent" in qml, name
    assert "<font color='" in qml, name
    state_foreground = {
        "Applauncher": "appmenuRoot.foregroundColor",
        "NotificationsHub": "dock.foregroundColor",
        "Calendar": "calendarDock.foregroundColor",
        "Bluetooth": "bluetoothDock.foregroundColor",
        "Git": "dock.foregroundColor",
    }[name]
    if name == "Git":
        assert '" + dock.foregroundColor + "' in qml, name
        assert 'color: dock.open ? dock.openForegroundColor : Colors.yellow' in qml
    else:
        assert f"color: {state_foreground}" in qml, name
        assert f'" + {state_foreground} + "' in qml, name
    for glyph in glyphs:
        assert glyph in qml, (name, glyph)
    assert "SafeDropShadow {" not in qml, name

for name in ("Applauncher", "NotificationsHub", "Calendar", "Bluetooth"):
    assert "Row {" not in module(name), name
assert module("Git").count("Row {") == 1, "Git retains one compound branch/cat layout"
assert 'text: "≽<font color=\'" + dock.foregroundColor + "\'>(</font>•⩊•マ≼"' in module("Git")
hospital = module("Hospital")
assert hospital.count("color: dock.foregroundColor") == 3
assert "color: Colors.white" not in hospital
assert "open: menuOpen" in hospital
for name in ("Applauncher", "NotificationsHub", "Git"):
    assert "open: menuOpen" in module(name), name
# Structural marks must glow magenta in the open state through DockButton's
# existing composite source and shared open-first glow priority.
assert "contentGlowSource: hospitalMark" in hospital

volume = module("Volumebar")
assert "contentGlowEnabled: false" in volume
assert volume.count("textFormat: Text.StyledText") == 2
assert 'safeSource: volumebarIcon' in volume
assert 'safeSource: volumebarText' in volume
assert 'safeSource: volumebarPercent' not in volume
assert 'id: volumebarPercent' not in volume
assert 'root.vol.toString() + "<font color=\'" + Colors.white + "\'>%</font>"' in volume
assert 'text: "⊹˖"' not in volume
assert 'return "<font color=\'" + Colors.white + "\'>⊹˖(</font>ᴗ˳ᴗ' in volume
assert 'color: !root.ready' in volume
assert 'root.muted\n                       ? Colors.white' in volume
assert volume.count("opacity: volumebarDock.pressed ? 1.0 : volumebarDock.hovered ? 0.95 : 0.75") == 2


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

# Wi-Fi now shares the rising dock glow intensity without flattening the
# icon, SSID, percentage, and speed into one sampled source.
network = module("Network")
assert network.count("opacity: networkDock.contentGlowOpacity") == 4
assert "networkDock.pressed ? 0.6 : networkDock.hovered ? 0.8 : 1.0" not in network
assert network.count("SafeDropShadow {") == 4, "Four independent sampled overlays required"
assert network.count("layer.effect: DropShadow {") == 1, "Legacy Ethernet pulse is the only remaining layer effect"
for field, radius in (
    ("networkIconRow", 14),
    ("networkText", 10),
    ("networkSignalText", 8),
    ("networkSpeedText", 8),
):
    assert f"safeSource: {field}" in network, field
    assert f"id: {field}Glow" in network, field
    assert f"readonly property point sourceOrigin: {field}.mapToItem(parent, 0, 0)" in network, field
    start = network.index(f"id: {field}Glow")
    end = network.index("\n    }", start)
    glow = network[start:end]
    assert f"radius: {radius}" in glow, (field, radius)
    assert "samples: 15" in glow, field
    assert "opacity: networkDock.contentGlowOpacity" in glow, field
    assert "color: root.networkGlowColor" in glow, field
    assert "z: 2" in glow, field
# Preserve all source containers, single-column telemetry geometry, and the
# independent signal-aware colors. The effect children must not be Layout
# children that claim row or column space.
assert "anchors.fill: parent" in network
assert "Layout.preferredWidth: 65" in network
assert "Layout.alignment: Qt.AlignVCenter" in network
assert "root.networkColor" in network
assert "property color networkGlowColor:" in network

# Preserve separately approved specialty behavior pending runtime review.
assert "softGlowSpread: 1" in module("Power")
assert "contentGlowSource: mediaArtwork" in module("Mediaplayer")

print("Dock cluster and structural-white contracts: PASS")
