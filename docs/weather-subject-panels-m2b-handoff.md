# Weather StationW // M2b WEATHER overview, maps and history

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station / Subject Migration M2b
ASSIGNMENT // Finish first integration of WEATHER overview, history and map routes
PROVIDER // OpenAI / ChatGPT (external Hospital-compatible)
STATUS // DRAFT PR; no local run, production activation or merge

## IMPLEMENTATION

- Reuses the existing `StationHome.qml` UI through new optional `subjectRoute`.
  WEATHER OVERVIEW exposes original NWS alert summary, current snapshot cards.
  HISTORY / HISTORICAL FORECAST exposes the existing Open-Meteo historical
  forecast model, clearly distinguished from observed measurements.
  HISTORY / RELATIONSHIPS exposes AQI/weather trend inspectors.
- Adds four children within WEATHER / HISTORY / RELATIONSHIPS:
  AQI, MARINE, COASTAL, and RIVERS, all mapped to existing original panels
  and the same NDBC, CO-OPS, NWPS, and live history store.
- The shared `WeatherHistoryService` only runs in CLASSIC HOME or
  WEATHER / HISTORY / HISTORICAL FORECAST. No duplicate instance.
- Extends deep river routes and flood hazards to the complete original NWPS
  instrument. Deeper route labels do NOT imply separately trimmed subpanels.
- Reuses `StationDiscovery.qml` as the real WEATHER map surface: same local
  Natural Earth basemap, existing mouse wheel zoom / drag pan, manual NOAA
  MRMS radar (4h history), RainViewer past radar fallback, and NOAA HMS
  smoke plume overlays. `weatherMapOnly` false is the exact CLASSIC behavior.
- WEATHER MAP excludes EONET, GDACS, USGS quakes, FIRMS hotspots and news
  points, controls and service activations; those remain in their original
  CLASSIC and future EARTH/MEDIA contexts.
- Lightning's existing NOAA nowCOAST density image is reused through the
  GROUND lightning panel at WEATHER / MAPS / LIGHTNING, not incorrectly
  claimed to be a georeferenced strike overlay in the map canvas.
- SOURCE ownership: existing singleton WeatherService, NWS, NWPS,
  lightning, historical forecast and existing map's manual radar/smoke
  services. No new source identity, extra provider polling or writers.
- MAGICK and COSMOS are not changed.

## HOW TO USE AFTER OPERATOR REVIEW + MERGE + LOCAL ACTIVATION

Open Weather Station > SUBJECTS > WEATHER.
Use OVERVIEW, MAPS / RADAR, MAPS / RADAR FALLBACK, MAPS / SMOKE,
HISTORY / HISTORICAL FORECAST, or HISTORY / RELATIONSHIPS.
The map only fetches radar/smoke after manual LOAD; wheel zoom and drag pan
remain. CLASSIC restores unchanged eight-page navigation.

## VERIFY

- Run `node --test tests/weather/subject_navigation_contract.test.js
  tests/weather/subject_navigation_browser.test.js
  tests/weather/test_weather_subject_panels_m2a.js
  tests/weather/test_weather_subject_panels_m2b.js`.
- Full Weather teardown and QML contracts must pass.
- Source contract tests are not a substitute for local Fedora Quickshell
  visual and live-source verification.

## WATCH OUT FOR

- The original HOME and MAP components now support optional route filters
  and the exact empty/default CLASSIC mode remains original.
- The weather map only presents manual snapshot imagery and polygons. No
  live global radar, strike locations, local eclipse map or wildfire boundary.
- Nighttime/latest weather states and maps depend on external provider data.
- Relationship tabs are provider-specific and scientific correlations are not
  causal explanations.
- The Map and HOME widgets are large; preserve source identity and its
  explicit data freshness/cooldown contracts when iterating.
- Do not alter M25 dossier archive, Kitty, or Stage Director.

## CHECKLIST

- [x] Rechecked main and open PRs; M2a/M2a1 both merged
- [x] Same-component WEATHER overview/history
- [x] Existing four relationship groups in one WEATHER hierarchy
- [x] Real weather-only map with previous renderer and manual controls
- [x] Dedicated focused CI tests
- [ ] All checks verified on final PR head
- [ ] Operator acceptance
- [ ] Local Quickshell visual/source verification

## NEXT

Verify CI and repair regressions. Next subject family: COSMOS or EARTH once
WEATHER navigation has operator visual acceptance. Do not automatically
turn one WEATHER test pass into deployment authority.

## DECISIONS

No local Fedora writes; no merge, production activation, or live Hospital
registration implied. This PR edits only Weather Station-owned source.
