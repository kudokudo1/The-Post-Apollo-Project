#!/usr/bin/env python3
"""W1 shell-to-Hub shared WeatherService wiring contracts (source-level only)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
bridge = (ROOT / "services/hub/ApolloHubLiveBridge.qml").read_text(encoding="utf-8")
module = (ROOT / "services/hub/qmldir").read_text(encoding="utf-8")
hub = (ROOT / "widgets/ApolloHubW.qml").read_text(encoding="utf-8")
tile = (ROOT / "widgets/hub/ApolloHubTile.qml").read_text(encoding="utf-8")

assert "import qs.services.hub" in shell
assert "ApolloHubLiveBridge 1.0 ApolloHubLiveBridge.qml" in module
assert shell.count("WeatherService {") == 1, "Do not duplicate the weather collector"
assert shell.count("ApolloHubLiveBridge {") == 1, "Use one Hub bridge"
assert "id: weatherService" in shell
assert "id: apolloHubLive" in shell
assert "weatherSource: weatherService" in shell
assert "id: apolloHubWindow" in shell
assert "liveBridge: apolloHubLive" in shell
assert "property var weatherSource: null" in bridge
assert "readonly property var weatherSnapshot:" in bridge
assert "property var liveBridge: null" in hub
assert "weatherSnapshot: hub.liveBridge" in hub
assert "hub.liveBridge.weatherSnapshot : null" in hub
assert "property var weatherSnapshot: null" in tile

# Wiring must not modify focus ownership, introduce another collector, or
# manually copy a snapshot outside the reactive QML binding chain.
assert "keyboardActive: !relationshipFocus.active" in shell
assert "relationshipFocused: false" in shell
assert "WlrKeyboardFocus.Exclusive" not in hub
assert "WeatherService {" not in hub + tile + bridge
assert "SystemTelemetry {" not in hub + tile + bridge
assert "onToggleRequested: apolloHubWindow.toggle()" in shell

print("ApolloHub W1 shared WeatherService shell wiring contracts passed")
