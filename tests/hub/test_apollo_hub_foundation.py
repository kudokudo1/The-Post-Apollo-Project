#!/usr/bin/env python3
"""Source contracts for the standalone ApolloHubW foundation (no live shell change)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
dock = (ROOT / "modules/ApolloHub.qml").read_text(encoding="utf-8")
window = (ROOT / "widgets/ApolloHubW.qml").read_text(encoding="utf-8")
tile = (ROOT / "widgets/hub/ApolloHubTile.qml").read_text(encoding="utf-8")
layout = (ROOT / "services/hub/ApolloHubLayout.js").read_text(encoding="utf-8")
store = (ROOT / "services/hub/ApolloHubStore.qml").read_text(encoding="utf-8")
module = (ROOT / "services/hub/qmldir").read_text(encoding="utf-8")

# Center dock integration is a separate shared-shell branch, allowing the
# user to accept the root-safe click preview before live activation.
assert "Calendar {" not in shell
assert "ApolloHub {" in shell
assert "ApolloHubW {" in shell
assert "onToggleRequested: apolloHubWindow.toggle()" in shell
assert "menuOpen: apolloHubWindow.menuOpen" in shell
assert "keyboardActive: !relationshipFocus.active" in shell
assert "WlrKeyboardFocus.Exclusive" not in window

# Use approved shared controls / frames rather than duplicating menus.
assert "DockButton {" in dock
assert 'NotoText {' in dock
assert 'textFormat: Text.StyledText' in dock
assert '⌯⌲ <font color=' in dock
assert '>🗓</font> ⋆˙⟡' in dock
assert """text: " ⌯⌲ <font color='" + (dock.open ? Colors.magenta : Colors.orange) + "'>🗓</font> ⋆˙⟡ " """ .strip() in dock
assert "color: dock.foregroundColor" in dock
assert "normalForegroundColor: Colors.white" in dock
assert "openForegroundColor: Colors.magenta" in dock
assert "contentGlowSource: hubMark" in dock
# Keep every chassis/artwork halo magenta, with reactive glow tracking.
# Ornaments and Calendar switch to magenta on open; Calendar is orange idle.
assert "normalDockGlowColor: Colors.magenta" in dock
assert "trackArtworkGlowLocally: true" in dock
for glow in ("hoverDockGlowColor", "pressedDockGlowColor", "openGlowColor",
             "normalContentGlowColor", "hoverContentGlowColor",
             "pressedContentGlowColor"):
    assert glow + ": Colors.magenta" in dock, glow
assert "PanelWindow {" in window
assert "WindowPanelFrame {" in window
assert "ModeButton {" in window

# ApolloHub chassis: 1000x700 visible body flush with top of screen,
# centered horizontally, square frame, magenta title and cyan inner outline.
assert "readonly property int frameWidth: 1000" in window
assert "readonly property int frameHeight: 700" in window
assert "readonly property int frameInset: 8" in window
assert "implicitHeight: frameHeight + glowGutter" in window
assert "        top: 0" in window
assert "anchors.topMargin: 0" in window
assert "((hub.screen ? hub.screen.width : 2560) - hub.implicitWidth) / 2" in window
assert "id: hubInnerFrame" in window
assert "anchors.margins: hub.frameInset" in window
assert "border.color: Colors.cyan" in window
assert "glowColor: Colors.magenta" in window
assert "borderColor: Colors.magenta" in window
assert "radius: 0" in window
assert 'color: Colors.magenta\n                    text: "APOLLO // HUB"' in window
assert "id: headerDivider" in window
assert "height: 2\n                color: Colors.cyan" in window

# Scroll content subtracts both header divider and fixed footer, including
# view/edit visibility-dependent Column spacings; the footer cannot be pushed
# below the bottom border by a full-height Flickable.
assert "id: statusFooter" in window
assert "- statusFooter.height" in window
assert "- headerDivider.height" in window
assert "(hub.editMode ? 6 : 5) * hubColumn.spacing" in window
assert "verticalAlignment: Text.AlignVCenter" in window
assert "    radius: 0\n    inset: 10" in tile
assert window.count("ActionButton {") >= 5
assert "SectionFrame {" in tile
assert "MouseArea {" not in window + tile + dock

# The header Close action uses the canonical U+00D7 multiplication sign.
# Red stays its identity for normal/hover/keyboard states, without changing
# ActionButton's destructive black-on-red pressed state. Size follows the
# accepted FinanceW Close precedent, not a generic 10px label.
close_start = window.index("id: closeButton")
close_end = window.index("onLeftClicked: hub.menuOpen = false", close_start)
close_button = window[close_start:close_end]
for needle in (
    'label: "×"',
    "labelPixelSize: 22",
    "contentPadding: 4",
    "accentColor: Colors.red",
    "destructive: true",
    "trackLabelGlowLocally: true",
    "hoverForegroundColor: Colors.red",
    "hoverBorderColor: Colors.red",
    "hoverContentGlowColor: Colors.red",
    "softGlowEnabled: true",
    "wideGlowEnabled: true",
    "softGlowIdleOpacity: 0.48",
    "wideGlowIdleOpacity: 0.22",
):
    # trackLabelGlowLocally appears before the id, unlike state/size options.
    if needle == "trackLabelGlowLocally: true":
        assert needle in window[window.rindex("ActionButton {", 0, close_start):close_start]
    else:
        assert needle in close_button, f"Hub Close missing {needle}"
assert 'label: "X"' not in close_button
assert 'label: "✕"' not in close_button
assert 'label: "✖"' not in close_button
assert "onLeftClicked: hub.menuOpen = false" in window[close_start:close_end + 42]

# Hub editor/selector buttons use ActionButton's existing reactive label
# tracking (proven on Projects ARCHIVE). Keep the icon and caption alignment
# independent from button backgrounds, halos and click actions.
import re

for path, source, count in (
    ("widgets/ApolloHubW.qml", window, 6),
    ("widgets/hub/ApolloHubTile.qml", tile, 3),
):
    actions = len(re.findall(r"\bActionButton\s*\{", source))
    tracked = len(re.findall(
        r"\bActionButton\s*\{\s*(?://[^\n]*\n\s*)?trackLabelGlowLocally:\s*true",
        source,
    ))
    assert actions == count, f"{path}: action count changed ({actions})"
    assert tracked == actions, f"{path}: {actions - tracked} untracked glow(s)"

for action in (
    'label: hub.editMode ? "VIEW" : "EDIT"',
    'label: hub.activeMode.subModes[index].name',
    'label: "+ MODE"',
    'label: "+ GROUP"',
    'label: "+ TILE"',
):
    assert action in window, f"Hub button behavior changed: {action}"
for action in ('label: "←"', 'label: "→"', 'label: "SWAP"'):
    assert action in tile, f"Hub edit-tile action changed: {action}"

shared_action = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")
assert "property bool trackLabelGlowLocally: false" in shared_action
assert "contentHost.x + labelText.x" in shared_action
assert "contentHost.y + labelText.y" in shared_action

# Configure modes/sub-modes and exchange module positions independently.
for name in ("defaultLayout", "normalize", "parse", "swapTiles",
             "renameMode", "addMode", "addSubMode", "addTile", "cycleTile"):
    assert "function " + name + "(" in layout
assert 'version: 1' in layout
assert 'Math.min(6, data.modes.length)' in layout
assert 'Math.min(6, inputMode.subModes.length)' in layout
assert 'Math.min(8, inputSub.tiles.length)' in layout
assert "onMoveLeft: hub.shiftTile(" in window
assert "onMoveRight: hub.shiftTile(" in window
assert "Layout.cycleTile(" in window
assert "Qt.formatTime" in tile
assert "Qt.formatDate" in tile

# Standard window-local key grammar, without inventing a bottom rail.
for key in ("Tab", "Shift+Tab", "Shift+Left", "Shift+Right",
            "Left", "Right", "Up", "Down", "Enter", "Return", "Esc"):
    assert 'sequence: "' + key + '"' in window, key
assert 'sequence: "Ctrl+Left"' not in window
assert 'sequence: "Ctrl+Right"' not in window
assert "function cycleMainMode(direction)" in window
assert "function cycleTopSubMode(direction)" in window
assert "function moveNavigationCursor(delta)" in window
assert "function activateNavigationCursor()" in window
assert "Keys.onShortcutOverride" in window
assert "Keys.onPressed" in window
assert "modeNameInput.activeFocus" in window
assert "context: Qt.WindowShortcut" in window
assert "WlrKeyboardFocus.OnDemand" in window
assert "WlrKeyboardFocus.Exclusive" not in window
assert "property bool keyboardSelected" in tile
assert "onPointerEntered: hub.selectedTileIndex = index" in window
assert "if (!editMode || selectedTileIndex < 0" in window


# Only save configuration, not user secrets or duplicated system services.
assert '"/apollo-hub-layout.json"' in store
assert "JsonAdapter {" in store
assert "onAdapterUpdated: writeAdapter()" in store
assert "singleton ApolloHubStore" in module
assert "ApolloHubStore.layoutJson = JSON.stringify(layout);" in window
assert "DATA ADAPTER NOT CONNECTED" in tile

# W1 UI: consume the shared shell's existing bridge through reactive QML
# bindings, never a copied snapshot or another WeatherService. Independent
# weather/AQI states must be visible even without a shell attachment.
assert "property var liveBridge: null" in window
assert "weatherSnapshot: hub.liveBridge" in window
assert "hub.liveBridge.weatherSnapshot : null" in window
assert "property var weatherSnapshot: null" in tile
assert 'weatherState === "ready"' in tile
assert "weatherSnapshot.fresh === true" in tile
assert 'weatherState === "ready" && !weatherReady' in tile
assert "tile.weatherStatus" in tile
assert 'tile.moduleId === "weather"' in tile
assert "tile.weatherSnapshot.temperatureF" in tile
assert "tile.weatherSnapshot.condition" in tile
assert "tile.weatherSnapshot.humidity" in tile
assert "tile.weatherSnapshot.windMph" in tile
assert "tile.airQualityText" in tile
assert "airQuality.fresh === true" in tile
assert "airQuality.index" in tile
assert 'return "DISCONNECTED";' in tile
assert 'String(airQuality.state || "unavailable").toUpperCase()' in tile
assert 'tile.weatherSnapshot.ageMinutes' in tile
for forbidden in ("WeatherService {", "ApolloHubLiveBridge {", "SystemTelemetry {"):
    assert forbidden not in window + tile, forbidden
assert "SystemTelemetry {" not in window
assert "HeadlessMediaController {" not in window

# W3 Network UI: use the existing B3 passive bridge, not an additional
# NetworkManager/polling instance. The visible status must say LOCAL LINK
# and explicitly UNVERIFIED INTERNET; unknown signal/speed stays "--".
assert "networkSnapshot: hub.liveBridge" in window
assert "hub.liveBridge.networkSnapshot : null" in window
assert "property var networkSnapshot: null" in tile
for needle in (
    'networkState === "connected"',
    "networkSnapshot.connected === true",
    'networkTransport === "ethernet"',
    'networkTransport === "wifi"',
    'networkState === "disconnected"',
    'networkState === "unavailable"',
    "networkWifi.networkName",
    "networkWifi.interfaceName",
    "networkEthernet.interfaceName",
    "networkWifi.signalPercent",
    "value >= 0 && value <= 100",
    'return "--";',
    "networkSnapshot.linkSpeedMbps",
    '"WI-FI LINK  " + tile.wifiLinkText',
    '"ETHERNET   " + tile.ethernetLinkText',
    '"INTERNET   UNVERIFIED"',
    '"LOCAL LINK CONNECTED"',
    '" // INTERNET UNVERIFIED"',
):
    assert needle in tile, f"B3 Network mini-tile missing {needle}"
assert 'visible: tile.moduleId === "network"' in tile
assert 'tile.moduleId !== "weather" && tile.moduleId !== "network"' in tile
for forbidden in ("Network {", "Networking {", "Process {", "nmcli", "iw dev",
                  "ethtool", "checkConnectivity(", "Networking.devices"):
    assert forbidden not in window + tile, f"UI must not collect/control network: {forbidden}"

# Launchers and widget backends are unchanged in this first stage.
print("ApolloHubW foundation source contracts passed")
