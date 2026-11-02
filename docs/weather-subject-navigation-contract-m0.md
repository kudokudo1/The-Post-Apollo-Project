# Weather StationW // Subject Navigation Contract M0

Status: draft, test-only, not integrated into live QML.
Owner: isolated new files. Patient: The-Post-Apollo-Project.
Provenance: Operator selected subject-first WEATHER / COSMOS / EARTH / MEDIA / MAGICK / TOOLS.

## Purpose

This pure QML JavaScript module establishes the route tree before any existing component,
service, terminal, or Quickshell UI is moved. It does not request data, change the current
eight-mode Weather Station interface, create persistence, or activate the MAGICK features.

## Interface

- `SUBJECTS`: nested canonical route metadata. A route is `subject/section[/detail[/subdetail]]`.
- `findRoute(path)`: accepts only exact known lowercase routes; returns a description with `status: SPEC_ONLY`.
- `childrenOf(path)` and `breadcrumbs(path)`: render nested rails without hardcoded mode-specific assumptions.
- `defaultForSubject(subject)` / `resumeSubject(subject, remembered)`: preserve each subject's last path without bleeding state across subjects.
- `legacyLanding(mode)`: hints for old *whole-screen* IDs; not a complete content migration.
- `panelLanding(panel)`: primary route for individual existing sections and controls.
- `relatedRoutes(topic)`: navigation links only; source collectors remain the owners.

## Semantics / invariants

1. A subject contains all its own observation, forecast, map, alert, history and analysis views.
2. Weather, Cosmos, Earth, Media and Tools do not become parallel global MAP / LAB / ARCHIVE modes.
3. MAGICK is the only deliberately cross-domain interpretive subject; its symbolic/traditional
   uses must remain distinct from measured and derived astronomical evidence.
4. Pure policy: no network, disk, processes, widgets, or side effects.
5. No clone of WeatherService, SpaceService, source caches or Radio Browser/Hi-Fi.
6. Existing keyboard Tab/Shift+Tab and Up/Down/Enter behavior, source status, the NEWS→MAP
   location handoff, and context Kitty app ID/session rules require separate integration.
7. Existing provider lifetimes and operator-requested image fetching must remain intact.
8. M23 cross-source dossier admission remains independent; no new dossier writes or retention rules.

## Known UI integration seams

- `widgets/weather/WeatherStationW.qml`: `currentView`, `mainModes`, rail,
  loader, status and context-terminal routes, keyboard navigation.
- `widgets/weather/StationGround.qml`: split Weather water/air/hazards from Earth seismic.
- `widgets/weather/StationSky.qml`: split Weather observations/forecasts from Cosmos astronomy.
- `widgets/weather/StationSpace.qml`: Cosmos space weather; preserve request cadence.
- `widgets/weather/StationDiscovery.qml`: decouple shared map renderer from source inspector.
- `widgets/weather/StationNewsHub.qml`: Media NEWS; preserve GDELT cooldown and viewer.
- `widgets/weather/StationRadio.qml`: Media RADIO; preserve shared Hi-Fi and MPD.
- `widgets/weather/StationTerminal.qml`: Tools and contextual console; preserve exact actor
  identity, geometry verification and close scope.
- `shell.qml`: existing singleton source/cache wiring must not be duplicated.

## Verification

Run `node --test tests/weather/subject_navigation_contract.test.js`.
CI workflow `.github/workflows/weather-subject-navigation-contract.yml` runs only
the focused Node contract tests. No Quickshell/live acceptance is implied.

## Next / ownership

Operator can review the hierarchy and per-panel destinations first. A later integration
branch may consume this module, subject to ownership checks, preservation tests, and the
operator's final approval. Do not merge this draft or activate production from this milestone.
