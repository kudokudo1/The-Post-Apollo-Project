#!/usr/bin/env python3
"""Weather M6b scoped persistent-cache integration source invariants.

This is not live QML execution. It guards routing, writing, initialization,
data provenance and the permanent NWS and unscoped-cache boundaries.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
shell=(root/"shell.qml").read_text(encoding="utf-8")
service=(root/"services/weather/WeatherService.qml").read_text(encoding="utf-8")
store=(root/"services/weather/WeatherPlaceCacheStore.qml").read_text(encoding="utf-8")
policy=(root/"services/weather/WeatherPlaceCachePolicy.js").read_text(encoding="utf-8")
legacy=(root/"services/weather/WeatherPersistentCacheStore.qml").read_text(encoding="utf-8")

assert shell.count("    WeatherPlaceCacheStore {")==1
assert "id: weatherPlaceCache" in shell
assert "locationCacheStore: weatherPlaceCache" in shell
assert shell.count("    WeatherService {")==1
assert 'property var locationCacheStore: null' in service
assert 'readonly property bool hasManualPlace:' in service
assert 'readonly property string requestContextKey:' in service
assert 'function hydrateLocationCache()' in service
assert 'function placeCachePut(kind, receivedAtMs, provider, payload)' in service
for phrase in (
    'locationCacheStore.record("weather-current", key, now)',
    'locationCacheStore.record("air-quality", key, now)',
    '"weather-forecast", key, now',
    'locationCacheStore.put(',
    'function persistSelectedCurrentWeather(receivedAtMs)',
    'function persistSelectedForecast(receivedAtMs)',
    'function persistSelectedAirQuality(receivedAtMs)',
    'persistSelectedCurrentWeather(receivedAt.getTime());',
    'persistSelectedForecast(receivedAt.getTime());',
    'persistSelectedAirQuality(aqiLastUpdated.getTime());',
    'cachedWeatherProvider = String(saved.provider || "");',
    'activeWeatherProvider = "CACHE";',
    'usingPersistentCurrentCache = true;',
    'usingPersistentForecastCache = true;',
    'usingPersistentAqiCache = true;',
):
    assert phrase in service,phrase
assert service.count('persistSelectedCurrentWeather(receivedAt.getTime());')==2
assert service.count('persistSelectedForecast(receivedAt.getTime());')==2
assert service.count('persistSelectedAirQuality(aqiLastUpdated.getTime());')==1

# No silent migration of old unscoped cache into a selected destination.
assert 'if (!cacheStore || hasManualPlace)' in service
assert 'if (!cacheStore || hasManualPlace || !forecastReady)' in service
assert 'if (!cacheStore || hasManualPlace || !aqiReady)' in service
assert 'weather-last-known-v1.json' in legacy
assert 'weather-place-last-known-v1.json' in store
assert 'weather-place-last-known-v1.json' not in legacy
assert "weather-place-last-known-v1.json" not in service
assert 'if (!hasManualPlace || !locationCacheStore)' in service
assert 'if (!hasManualPlace || !locationCacheStore)' in service

# Return Home, startup and late file-load callback all hydrate the exact
# active key. Existing primary/fallback and independent AQI remain running.
switch=service[service.index('onRequestContextKeyChanged:'):
               service.index('function parseWeather(rawText)')]
assert 'clearLocationData();' in switch
assert 'weatherService.hydrateLocationCache();' in switch
assert 'weatherService.hydratePersistentCache();' in switch
assert 'weatherService.refresh();' in switch
assert 'weatherService.refreshAirQuality();' in switch
assert service.count('function onStorageStateChanged()')>=2
boot=service[service.rindex('Component.onCompleted:'):]
assert boot.index("hydratePersistentCache();") < boot.index("hydrateLocationCache();")
assert boot.index("hydrateLocationCache();") < boot.index("refresh();")
assert service.count("    Process {")==3
assert service.count("    Timer {")==1
assert 'activeWeatherProvider = "WTTR"' in service
assert 'activeWeatherProvider = "OPEN_METEO"' in service
assert "fallbackRequestContextKey" in service

# The scoped store is one atomic-writes owner, with deferred startup writes
# and write coalescing. Reads never use uncommitted or foreign coordinates.
for phrase in (
    'atomicWrites: true','watchChanges: false',
    'function record(kind, scopeKey, nowMs)',
    'Policy.record(document, kind, scopeKey, nowMs)',
    'function workingDocument()',
    'function put(kind, scopeKey, receivedAtMs, provider, payload)',
    'function applyDeferredUpdates()',
    'function flushQueued()',
    'onSaved:','onSaveFailed:','FileView {',
    'Policy.upsert(', 'if (storageState === "loading")',
    'pendingDocument = queuedDocument',
    'document = saved'
):
    assert phrase in store,phrase
assert store.count("    FileView {")==1
for phrase in (
    'var MAX_RECORDS = 30;', 'var MAX_DOCUMENT_BYTES = 262144;',
    'function key(value)', 'function normalizeRecord(raw)',
    'function upsert(documentRaw, kind, scopeKey, receivedAtMs, provider, data)',
    'function record(documentRaw, kind, scopeKey, nowMs)',
    '"weather-current": 5400000',
    '"weather-forecast": 43200000',
    '"air-quality": 10800000',
):
    assert phrase in policy,phrase
for forbidden in ('POST_APOLLO_NWS_ALERT_POINT','NwsOfficialAlert',
                  'timedatectl','placeRegistry.saveHome(',
                  'placeRegistry.exploreHere(','placeRegistry.returnHome(',
                  'http://','https://'):
    assert forbidden not in store,forbidden
    assert forbidden not in policy,forbidden

print("Weather M6b scoped-cache wiring, startup, provenance and safety: PASS")
