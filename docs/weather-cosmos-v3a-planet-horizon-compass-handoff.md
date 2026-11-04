# Hospital // COSMOS V3a True-North Horizon Compass

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence, Lane B
STAFF ROLE // NRS-2 external Hospital-compatible; not live registered
PROVIDER // OPEN AI // CHATGPT
ASSIGNMENT // V3a add an interactive rise/set bearing compass with transit-altitude comparison
STATE // GitHub draft; native Quickshell verification and operator acceptance pending
ROADMAP // docs/weather-subjects-visual-intelligence-future-worker-roadmap-2026-11-03.md

## IMPLEMENTATION

A source-backed local-horizon graphical instrument has been added as a *subview of the existing COSMOS Planet Clock*, not as a new navigation destination or a collector. One HORIZON button in the existing V2d clock swaps to a 414px true-north compass; TIMELINE returns to the pre-existing event graph.

- `StationCosmosPlanetHorizonPolicy.js`: bounded, read-only geometry and data contracts. Consumes the *validated* five-planet `StationCosmosPlanetEventPolicy.clockRows()` output, accepts only exact source-matched USNO rise/set azimuths 0–360° and date-matched, source-stamped events. Projects azimuth 0° to north (top), 90° east, 180° south and 270° west. Marker hit-testing uses the same coordinates as drawing. Includes separate transit-altitude measurements 0–90°, without pretending these are azimuths.
- `StationCosmosPlanetHorizonPane.qml`: independent Canvas compass with true-north rings and cardinal ticks, colored rise/set bearings, hover inspection, click-to-lock, UNLOCK, six interactive planet filters, and five independently source-backed transit-altitude bars. Missing values explicitly remain unavailable. The view displays its event-date/source context and states it is not a live position or continuous orbital path.
- `StationCosmosPlanetEventClock.qml`: narrowly adds `displayMode = "timeline" | "horizon"`, an HORIZON toggle in its existing title row, and the new pane as a sibling. Both views reuse `clock.rows` and `clock.selectedPlanet`. The existing graph and service are untouched; original footprint stays 414px.
- No changes to `StationSky.qml`, shared SUBJECTS navigation, HOME, CLASSIC migration, `StationSubjectNavigator.qml`, source services, storage, MAGICK JPL ephemeris, or Stage Director.

### Scientific boundaries

**The compass dots are dated RISE and SET directions at their respective times, not the planets' present sky positions.** The altitude bars show the USNO upper-transit altitude readings separately, not a current altitude or a continuous elevation curve. No positions are inferred between these records. Azimuths reference TRUE NORTH. For actual instantaneous planetary positions, aspects, longitude or retrograde motion, coordinate with the separate JPL-based MAGICK M4/M5 calculation pipeline.

## HOW TO USE

After PR review, authorized merge and separately approved local Fedora deployment:

Weather Station → SUBJECTS → COSMOS → ASTRONOMY → PLANET CLOCK, or INDEX → COSMOS → PLANETS AND STARS → PLANET RISE/SET. Click **HORIZON** on the clock header. Choose ALL or a planet, hover a cyan RISE or orange SET marker, click to lock details, and UNLOCK to clear. Read the five transit-altitude bars below. Click **TIMELINE** to return to the V2d zoomable event view.

## VERIFY

- Dedicated `tests/weather/test_cosmos_planet_horizon_v3a.js` validates true-north projection and all four cardinal bearings, exact date/provenance, malformed/special/missing events, QML indexed-list compatibility, measured 0–90° transit altitude, click hit-testing and no made-up orbital data.
- Existing `.github/workflows/weather-cosmos-planet-events-v2b.yml` now triggers on both new source files and executes V3a alongside prior V2b/V2c/V2d, V2/V2r, C1 and W1r tests.
- GitHub CI must be checked on the final PR head. Text/source tests are **not** a substitute for native QML load, canvas rendering, pointer hitboxes, readable Gohu labels or actual USNO freshness on the operator desktop.

## WATCH OUT FOR

- The internal TIMELINE/HORIZON switch is **not** a new outer mode: the other worker still owns SUBJECTS navigation/CLASSIC retirement.
- Five planets can have similar rise/set bearings, so dots may overlap in ALL mode. Use one planet filter to inspect a bearing; no fake angular offset is applied to source data.
- Missing angle, missing dated event or special above/below-horizon status must **not** draw a marker. The original USNO cards below remain the exact provider-level detailed reference.
- The compass is anchored to dated provider predictions and is not geolocation-dependent beyond the existing weather location inputs used by the USNO service. No new location/clock reader or background work was added.
- Font fallbacks, clipping, high-DPI Canvas scaling, 414px fit and potential conflict with parent Flickable should be checked natively. A default Canvas image is not evidence of successful desktop rendering.
- Do not merge or deploy locally without authorization; do not claim live Hospital registration.

## CHECKLIST

- [x] Verify V2d PR #1181 merged and current GitHub state
- [x] Recheck source ownership and single USNO provider
- [x] Add pure compass and data validation policy
- [x] Add interactive Canvas and in-clock view switch
- [x] Add dedicated tests and CI trigger
- [ ] Final PR-head CI verified green
- [ ] Native Fedora Quickshell horizon/timeline toggle and pointer test
- [ ] Operator's visual and scientific acceptance

## NEXT

Review CI and source changes, then merge only if authorized. On live Fedora confirm the compass bearings and altitude bars are populated when valid USNO data exist; test ALL vs one planet, direct marker hitboxes, lock/unlock and return to TIMELINE. Capture actual layout. Further COSMOS visualization can then reuse the existing MAGICK/JPL M4 data in a separate, coordinated assignment without creating a second calculation service.

## DECISIONS

Lane B owns isolated visual instruments and their pure policies, not SUBJECTS organization or data services. The V3a compass is intentionally a precise visualization of discrete USNO events rather than a simulated planetary sky path. GitHub review is technical completion only; operator acceptance remains pending.
