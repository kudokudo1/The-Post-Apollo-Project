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

# Preserve the existing center dock until integration is approved/reconciled.
assert "Calendar {" in shell
assert "ApolloHub {" not in shell
assert "ApolloHubW {" not in shell

# Use approved shared controls / frames rather than duplicating menus.
assert "DockButton {" in dock
assert 'text: "✦ APOLLO ✦"' in dock
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
