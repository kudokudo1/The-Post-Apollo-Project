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
assert "Colors.orange" in dock
assert "color: Colors.white" in dock
assert "contentGlowSource: hubMark" in dock
# Idle rear/wide chassis halo is orange; glyph sampling and active dock
# states remain magenta without disturbing the reactive glow-tracking repair.
assert "normalDockGlowColor: Colors.orange" in dock
assert "trackArtworkGlowLocally: true" in dock
for glow in ("hoverDockGlowColor", "pressedDockGlowColor", "openGlowColor",
             "normalContentGlowColor", "hoverContentGlowColor",
             "pressedContentGlowColor"):
    assert glow + ": Colors.magenta" in dock, glow
assert "PanelWindow {" in window
assert "WindowPanelFrame {" in window
assert "ModeButton {" in window
assert window.count("ActionButton {") >= 5
assert "SectionFrame {" in tile
assert "MouseArea {" not in window + tile + dock

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
assert "SystemTelemetry {" not in window
assert "HeadlessMediaController {" not in window

# Launchers and widget backends are unchanged in this first stage.
print("ApolloHubW foundation source contracts passed")
