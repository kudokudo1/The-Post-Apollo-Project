#!/usr/bin/env python3
"""Weather Station DOMAIN / VIEW remain orthogonal after Main Mode migration."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
weather = (root / "widgets/weather/WeatherStationW.qml").read_text(encoding="utf-8")
assert weather.count("ModeButton {") == 3
for token in (
    "id: homeButton", "id: domainButton", "id: viewButton",
    'selected: weatherStation.currentView === "home"',
    "selected: weatherStation.activeDomain === modelData.id",
    "selected: weatherStation.currentView === modelData.id",
    'weatherStation.currentView = "home";',
    "weatherStation.activeDomain = modelData.id;",
    "weatherStation.currentView = modelData.id;",
    "iconText: modelData.symbol", "labelText: modelData.name",
    "horizontalContent: true", "onTriggered:",
):
    assert token in weather, token
for old in ("id: homeMouse", "id: domainMouse", "id: viewMouse"):
    assert old not in weather, old
print("Weather Main Mode: PASS")
