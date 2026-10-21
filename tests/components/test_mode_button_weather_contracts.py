#!/usr/bin/env python3
"""Weather Station domains are first-class Main Modes after separation."""

from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
weather = (root / "widgets/weather/WeatherStationW.qml").read_text(
    encoding="utf-8"
)

assert weather.count("ModeButton {") == 1
assert "id: mainModeButton" in weather

order_match = re.search(
    r"readonly property var mainModes:\s*\[([^\]]+)\]",
    weather,
)
assert order_match
order = re.findall(r'"id":\s*"([^"]+)"', order_match.group(1))
assert order == [
    "home", "ground", "sky", "space",
    "map", "news", "radio", "terminal",
]

for token in (
    "model: weatherStation.mainModes",
    "selected:",
    "weatherStation.currentView === modelData.id",
    "weatherStation.currentView = modelData.id;",
    "iconText: modelData.symbol",
    "labelText: modelData.name",
    "horizontalContent: true",
    "onTriggered:",
):
    assert token in weather, token

for old in (
    "id: homeButton",
    "id: domainButton",
    "id: viewButton",
    "weatherStation.activeDomain",
):
    assert old not in weather, old

print("Weather Main Mode: PASS")
