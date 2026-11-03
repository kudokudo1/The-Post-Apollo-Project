#!/usr/bin/env python3
"""M6c diagnostics remain read-only and reuse Weather Station's source owner."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
station = (root/"widgets/weather/WeatherStationW.qml").read_text()
panel = (root/"widgets/weather/StationWeatherProviderDiagnostics.qml").read_text()
policy = (root/"widgets/weather/StationProviderDiagnosticsPolicy.js").read_text()
home = (root/"widgets/weather/StationHome.qml").read_text()
health = (root/"widgets/weather/StationSourceHealthPolicy.js").read_text()
weather = (root/"services/weather/WeatherService.qml").read_text()

for token in (
    'import "StationProviderDiagnosticsPolicy.js" as ProviderDiagnostics',
    'ProviderDiagnostics.snapshot({', 'id: providerDiagnosticsButton',
    'label: weatherStation.providerDiagnosticsOpen',
    'onLeftClicked:', 'weatherStation.providerDiagnosticsOpen =',
    'StationWeatherProviderDiagnostics {', 'snapshot: weatherStation.weatherDiagnostics',
    'onCloseRequested: weatherStation.providerDiagnosticsOpen = false',
    'if (providerDiagnosticsOpen)',
    'weatherDiagnostics.header',
):
    assert token in station, token
assert station.count('StationWeatherProviderDiagnostics {') == 1
# The unified M28-N Escape handler preserves M6c overlay priority across
# BOTH Qt Keys and the root WindowShortcut, before INDEX/close handling.
assert station.index('if (providerDiagnosticsOpen)') < station.index('SubjectDefaultPolicy.escapeAction(')
assert station.count('weatherStation.handleEscape()') == 2
assert 'id: sourceStatusIndicator' in station
assert station.index('if (officialAlertSummary.available)')        < station.index('if (usesWeatherSource)')
assert 'id: sourceStatusIndicator' in station
assert 'width: 150' in station
assert 'id: headerActions' in station
assert 'id: providerDiagnosticsPane' in station
assert 'visible: weatherStation.providerDiagnosticsOpen' in station

for token in (
    'property var snapshot: null', 'signal closeRequested()',
    'PROVIDER HEALTH // DIAGNOSTICS', 'DISPLAYED //',
    'LOCATION //', 'LAST PROVIDER SUCCESS //', 'REASON // CURRENT ROUTING',
    'READ ONLY // PROVIDER STATUS IS SESSION-LOCAL',
):
    assert token in panel, token
for forbidden in ('Process {','Timer {','FileView {','curl','Qt.openUrlExternally',
                  'saveHome(', 'refresh(', 'exploreHere('):
    assert forbidden not in panel, forbidden
    assert forbidden not in policy, forbidden

for token in (
    'property var primaryLastSuccessAt: null',
    'property var fallbackLastSuccessAt: null',
    'primaryLastSuccessAt = receivedAt;',
    'fallbackLastSuccessAt = receivedAt;',
    'primaryLastSuccessAt = null;',
    'fallbackLastSuccessAt = null;',
):
    assert token in weather, token
assert weather.count('    Process {') == 3  # no new provider
assert weather.count('    Timer {') == 1   # no new polling

for token in (
    '"cached": weatherService',
    '"fallback": weatherService',
    'weatherService.activeWeatherProvider === "OPEN_METEO"',
    'weatherService.usingPersistentCurrentCache',
    'weatherService.usingPersistentAqiCache',
):
    assert token in home, token
assert 'case "CACHE": return "yellow";' not in health or 'case "CACHE"' in health
assert 'state = stale ? "CACHE STALE" : "CACHE";' in health
assert 'state = stale ? "FALLBACK STALE" : "FALLBACK";' in health
assert 'detail = "LAST KNOWN // "' in health

print("Weather M6c single-owner, UI navigation and source-provenance contract: PASS")
