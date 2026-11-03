#!/usr/bin/env python3
"""M6 provider fallback source and ownership contract.

This checks source invariants; separate disposable QML and operator-network
verification are still required.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
weather = (root/"services/weather/WeatherService.qml").read_text()
fallback = (root/"services/weather/OpenMeteoFallbackPolicy.js").read_text()
shell = (root/"shell.qml").read_text()
registry = (root/"services/location/PlaceRegistry.qml").read_text()
station = (root/"widgets/weather/WeatherStationW.qml").read_text()

assert 'import "OpenMeteoFallbackPolicy.js" as FallbackPolicy' in weather
assert weather.count("    Process {") == 3
assert weather.count("    Timer {") == 1
assert 'id: weatherFetch' in weather
assert 'id: fallbackWeatherFetch' in weather
assert 'id: airQualityFetch' in weather
assert 'weatherService.fallbackWeatherEndpoint' in weather
assert 'hasManualPlace ? FallbackPolicy.endpoint(latitude, longitude) : ""' in weather
assert 'function startFallbackWeather()' in weather
assert 'function parseFallbackWeather(rawText)' in weather
assert 'FallbackPolicy.parse(rawText)' in weather
assert 'weatherService.startFallbackWeather()' in weather
assert 'Qt.callLater(function()' in weather
assert 'weatherService.primaryParseSucceeded' in weather
assert 'weatherService.fallbackParseSucceeded' in weather
assert 'primaryWeatherStatus = "FETCHING"' in weather
assert 'fallbackWeatherStatus = "FETCHING"' in weather
assert 'activeWeatherProvider = "WTTR"' in weather
assert 'activeWeatherProvider = "OPEN_METEO"' in weather
assert 'weatherGeneration += 1;' in weather
assert 'fallbackGeneration = weatherGeneration;' in weather
assert '=== weatherService.weatherGeneration' in weather
assert '!== weatherService.weatherGeneration' in weather
assert 'weatherRequestContextKey' in weather
assert 'fallbackRequestContextKey' in weather
assert 'readonly property bool loading:\n        weatherFetch.running || fallbackWeatherFetch.running' in weather

# Fallback has the same public current/forecast keys as the existing
# WeatherDataPolicy readers, so widgets do not need a second data model.
for field in (
    "tempF", "feelsLikeF", "humidity", "windMph", "windDirection",
    "pressureHpa", "visibilityMiles", "cloudCover", "precipMm",
    "observationTime", "localObservationDateTime", "weatherCode",
    "condition", "uvIndex", "hourlyForecast", "dailyForecast",
    "lastUpdated", "forecastLastUpdated",
):
    assert field in weather, field
for key in ("daily:", "hourly:", "condition:", "weatherCode:",
            "chanceRain:", "chanceSnow:", "sunrise:", "sunset:"):
    assert key in fallback, key

# No extra file owner or source of location truth.
assert "FileView {" not in weather
assert "FileView {" not in fallback
assert "Quickshell.dataDir" not in fallback
assert "Quickshell.dataDir" not in weather
assert "placeRegistry: PlaceRegistry" in shell
assert 'readonly property var effectivePlace:' in registry
assert "weatherService: weatherService" in station or "weatherStation.weatherService" in station
assert 'property var placeRegistry: null' in weather

# Never hydrate or write location-unscoped cache for a manually selected
# Home/Explore destination. Fallback's missing sensors stay unknown.
assert 'if (!cacheStore || hasManualPlace)' in weather
assert 'if (!cacheStore || hasManualPlace || !forecastReady)' in weather
assert 'if (!cacheStore || hasManualPlace || !aqiReady)' in weather
assert 'visibilityMiles:-1' in fallback
assert 'uvIndex:-1' in fallback
assert 'moonPhase:"--"' in fallback

# Pinned NWS point remains separate. No system clock or local modifications.
for forbidden in ("POST_APOLLO_NWS_ALERT_POINT", "timedatectl",
                  "placeRegistry.saveHome(", "placeRegistry.exploreHere(",
                  "placeRegistry.returnHome()"):
    assert forbidden not in weather
assert 'weatherFetch.running = true' in weather
assert 'fallbackWeatherFetch.running = true' in weather

print("Weather M6 primary/fallback sequencing and safety contracts: PASS")
