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
# Operator screenshot: Bluetooth is optically low even when its single
# Text box is mathematically centered. A source-local -2px correction keeps
# artwork and DockButton glow aligned without splitting glyphs or moving layout.
bluetooth = module("Bluetooth")
assert "anchors.centerIn: parent" in bluetooth
assert "anchors.verticalCenterOffset: -2" in bluetooth
assert "contentGlowSource: bluetoothText" in bluetooth
assert "Row {" not in bluetooth
assert bluetooth.count("textFormat: Text.StyledText") == 1

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

# Wi-Fi's Qt layer effects MUST remain attached to the original glyph
# containers. Detached source-mapped copies visibly ghosted and displaced
# the SSID/telemetry in the operator's screenshots.
network = module("Network")
assert "SafeDropShadow {" not in network
assert "mapToItem(parent, 0, 0)" not in network
assert network.count("layer.effect: DropShadow {") == 7  # six + Ethernet pulse
assert network.count("color: networkDock.sampledGlowColor") == 6
assert network.count("radius: networkDock.contentGlowRadius") == 6
assert network.count("samples: networkDock.contentGlowSamples") == 6
assert network.count("layer.enabled: true") == 7
assert "opacity: networkDock.contentGlowOpacity" not in network
assert "readonly property color sampledGlowColor: Qt.rgba(" in network
assert "root.networkGlowColor.a * networkDock.contentGlowOpacity" in network
assert 'source: networkIconRow' in network  # original compound icon layer
assert "color: Colors.cyan" in network  # fixed Ethernet pulse, unchanged
for item, expected in (
    ("networkOpen", '"("'),
    ("networkClose", '")"'),
):
    block = network[network.index(f"id: {item}"):][:540]
    assert f"text: {expected}" in block, item
    assert "color: Colors.white" in block, item
    assert "layer.effect: DropShadow {" in block, item

assert 'text: root.signalPercent + "%"' in network
assert 'text: root.linkSpeed + " Mb/s"' in network
assert "Layout.preferredWidth: 65" in network
assert "Layout.alignment: Qt.AlignVCenter" in network
assert "root.networkColor" in network
assert "property color networkGlowColor:" in network
assert 'Quickshell.execDetached(["nm-connection-editor"])' in network
assert "root.ethernetMode = !root.ethernetMode" in network
assert "root.signalWeak" in network and "root.signalStrong" in network
dock_source = (ROOT / "components/DockButton.qml").read_text(encoding="utf-8")
assert "readonly property real contentGlowRadius:" in dock_source
assert "readonly property int contentGlowSamples:" in dock_source

# Preserve separately approved specialty behavior pending runtime review.
assert "softGlowSpread: 1" in module("Power")
assert "contentGlowSource: mediaArtwork" in module("Mediaplayer")

print("Dock cluster and structural-white contracts: PASS")
