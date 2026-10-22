#!/usr/bin/env python3
"""ApolloHub read-only shared Weather bridge source contracts.

Live Wayland/Qt delivery and freshness transitions require on-device testing.
These guards intentionally do not claim to replace runtime verification.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
bridge = (ROOT / "services/hub/ApolloHubLiveBridge.qml").read_text(encoding="utf-8")
qmldir = (ROOT / "services/hub/qmldir").read_text(encoding="utf-8")
policy = (ROOT / "services/weather/WeatherDockPolicy.js").read_text(encoding="utf-8")
weather = (ROOT / "services/weather/WeatherService.qml").read_text(encoding="utf-8")
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")

def require(haystack, needle, label):
    assert needle in haystack, f"{label}: missing {needle!r}"

# The bridge must be available to the Hub UI as a normal QML type.
require(qmldir, "ApolloHubLiveBridge 1.0 ApolloHubLiveBridge.qml", "registration")
require(bridge, "Scope {", "nonvisual bridge")
require(bridge, "property var weatherSource: null", "injected provider")
require(shell, "WeatherService {", "shared source")
require(shell, "id: weatherService", "shared source")

# Reuse existing WEATHER freshness/formatting rules, not a competing policy.
require(bridge, 'import "../weather/WeatherDockPolicy.js" as WeatherPolicy',
        "weather policy")
for call in ("WeatherPolicy.fresh(", "WeatherPolicy.formatTemperature("):
    require(bridge, call, "reuse source policy")
    assert call.replace("WeatherPolicy.", "function ") in policy
for field in ("ready", "loading", "errorText", "lastUpdated",
              "tempF", "feelsLikeF", "condition", "humidity",
              "windMph", "windDirection", "uvIndex", "aqiReady",
              "aqiLoading", "aqiErrorText", "aqiLastUpdated",
              "aqi", "aqiLabel"):
    require(weather, "property ", "WeatherService property declaration")
    assert field in weather, f"WeatherService no longer exposes {field}"

# One inexpensive freshness tick; NEVER start another weather instance,
# network fetch, subprocess, or write-through control.
require(bridge, "interval: 60000", "freshness tick")
require(bridge, "onWeatherSourceChanged: observationNowMs = Date.now()", "clock")
require(bridge, "onTriggered: bridge.observationNowMs = Date.now()", "clock")
for forbidden in ("WeatherService {", "Process {", "Command {", "curl",
                  "refresh()", "refreshAirQuality()", "Http", "FileView {",
                  "SystemTelemetry {", "HeadlessMediaController {"):
    assert forbidden not in bridge, f"Duplicate service / side effect: {forbidden}"

# Missing/stale/error observations are explicitly not fresh; provider and
# AQI have separate freshness and error states.
for contract in (
    "readonly property bool weatherConnected:",
    "readonly property bool weatherFresh:",
    "weatherConnected && weatherSource.ready && weatherError === \"\"",
    "WeatherPolicy.fresh(weatherUpdatedMs, observationNowMs)",
    "readonly property string weatherState:",
    'return "disconnected"',
    'return "loading"',
    'return "error"',
    'return "stale"',
    'return "unavailable"',
    "readonly property string temperatureF:",
    "readonly property string temperatureC:",
    "readonly property string feelsLikeF:",
    "readonly property string feelsLikeC:",
    "readonly property string condition:",
    "readonly property string humidity:",
    "readonly property string windMph:",
    "readonly property real uvIndex:",
    "readonly property string airQualityError:",
    "readonly property bool airQualityFresh:",
    "WeatherPolicy.fresh(airQualityUpdatedMs, observationNowMs)",
    "readonly property int airQualityIndex:",
    "readonly property string airQualityState:",
    "readonly property var weatherSnapshot:",
    "state: bridge.weatherState",
    "fresh: bridge.weatherFresh",
    "airQuality: {",
):
    require(bridge, contract, "read-only snapshot contract")

print("ApolloHub live Weather bridge source contracts passed")
