#!/usr/bin/env python3
"""M5 shared Places -> WeatherService integration source contract.

Read-only source checks complement pure JS policy tests; they do not
replace a native QML runtime test or operator weather-provider verification.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
shell = (root/"shell.qml").read_text(encoding="utf-8")
weather = (root/"services/weather/WeatherService.qml").read_text(encoding="utf-8")
registry = (root/"services/location/PlaceRegistry.qml").read_text(encoding="utf-8")
station = (root/"widgets/weather/WeatherStationW.qml").read_text(encoding="utf-8")
policy = (root/"services/location/WeatherLocationPolicy.js").read_text(encoding="utf-8")

assert "import qs.services.location" in shell
assert "placeRegistry: PlaceRegistry" in shell
assert shell.count("    WeatherService {") == 1
assert 'readonly property var effectivePlace:' in registry
assert 'readonly property string contextKind:' in registry
assert 'PlacePolicy.effectivePlace(document, clockMs)' in registry
assert 'LocationPolicy.requestContextKey(selectedPlace, location)' in weather
assert 'LocationPolicy.coordinates(' in weather
assert 'LocationPolicy.locationQuery(selectedPlace, location)' in weather
assert 'readonly property string latitude: resolvedCoordinates.latitude' in weather
assert 'readonly property string longitude: resolvedCoordinates.longitude' in weather
assert 'property string providerLatitude: ""' in weather
assert 'property string providerLongitude: ""' in weather
assert 'property var placeRegistry: null' in weather
assert 'readonly property var selectedPlace:' in weather
assert 'readonly property bool hasManualPlace:' in weather

# Old provider-derived coordinates must no longer mutate public effective
# location fields. All downstream Weather Station source consumers still use
# weatherService.latitude and weatherService.longitude.
for line in weather.splitlines():
    assert not line.lstrip().startswith(("latitude =", "longitude =")), line
for token in (
    "weatherStation.weatherService.latitude",
    "weatherStation.weatherService.longitude",
):
    assert token in station

# AQI can launch on load/change without a successful wttr.in parser.
assert 'Component.onCompleted:' in weather
init = weather[weather.rindex("Component.onCompleted:"):]
assert init.index("refreshAirQuality();") < init.index("refresh();")
changed = weather[weather.index("onRequestContextKeyChanged:"):
                  weather.index("// ─────────────────────────────────────────────\n    // WEATHER PARSER")]
assert "clearLocationData();" in changed
assert "weatherService.refreshAirQuality();" in changed
assert "weatherService.refresh();" in changed
assert "weatherFetch.running = false" not in changed
assert "airQualityFetch.running = false" not in changed

# Asynchronous old-location payloads must be rejected before parsing.
assert 'weatherService.weatherRequestContextKey\n                        === weatherService.requestContextKey' in weather
assert 'weatherService.aqiRequestContextKey\n                        === weatherService.requestContextKey' in weather
assert weather.count("Qt.callLater(weatherService.refresh)") >= 1
assert weather.count("Qt.callLater(weatherService.refreshAirQuality)") >= 1

# Unscoped legacy cache must not be relabelled as manual Home or Explore.
assert 'if (!cacheStore || hasManualPlace)' in weather
assert 'if (!cacheStore || hasManualPlace || !forecastReady)' in weather
assert 'if (!cacheStore || hasManualPlace || !aqiReady)' in weather
assert 'if (latitude === "" || longitude === "")\n            return "";' in weather

# No alert-point, system clock, local machine or PlaceRegistry mutation.
for token in ("POST_APOLLO_NWS_ALERT_POINT", "NwsOfficialAlert",
              "setSystemTime", "placeRegistry.saveHome(",
              "placeRegistry.exploreHere(", "placeRegistry.returnHome()"):
    assert token not in weather, token
assert "source" not in policy or 'place.source !== "MANUAL"' in policy
print("Weather Location M5 integration and safety boundaries: PASS")
