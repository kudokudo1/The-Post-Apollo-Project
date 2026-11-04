# 🏥💜 Weather Station // COSMOS V3c Angular Comparison Dial

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence, Lane B
STAFF ROLE // Nurse 2 / NRS-2, external Hospital-compatible
PROVIDER // OPEN AI // CHATGPT
ASSIGNMENT // V3c source-backed circular comparison of two planet event bearings
STATE // Draft GitHub review; CI/native acceptance pending
GIT // feat/weather-cosmos-v3c-bearing-comparison-dial-20261104
SOURCE // Existing USNO MRST planet rise/transit/set service via V2b-d clock and V3a/b Horizon policy
ROADMAP // docs/weather-subjects-visual-intelligence-future-worker-roadmap-2026-11-03.md

## IMPLEMENTATION

- V3b (#1187) verified merged. Open Weather/MAGICK ownership checked. No concurrent Weather PR at assignment start.
- Latest MAGICK design (#1191) and existing JPL-backed M4/M5 data/wheel reviewed. That team owns further true planetary-position/angular-aspect and spatial view expansion. **This V3c does not duplicate, alter or impersonate that pipeline.**
- New pure policy `StationCosmosBearingComparisonPolicy.js` compares **rise OR set azimuth** for two distinct planets. Both must derive from exactly dated, source-stamped `USNO MRST` event records exposed by the existing `StationCosmosPlanetHorizonPolicy.markers()`. The comparison is the **smaller angular difference between compass directions** (0–180°), with explicit clockwise/counterclockwise orientation for intermediate differences and unambiguous labels for 0°/180°.
- New standalone QML `StationCosmosBearingComparisonPane.qml`: true-north circular dial with two real event-bearing rays and markers, a magenta angular gap arc, two planet selectors (A/B), RISE/SET filter, direct A/B marker clicks, independent FOCUS A/FOCUS B controls (including coincident markers), measured local event time/date/source context, and HORIZON/TIMELINE return controls. No instrument can invent a missing source event.
- Narrow integration: one COMPARE button added to the existing Horizon header, and a sibling compare view added inside the original `StationCosmosPlanetEventClock.qml` 414px host. No `StationSky.qml`, shared navigator, FAMILY/INDEX or CLASSIC migration edits. No new source service, ephemeris, process, network call or persistent state.
- Circle is genuine visualization of the difference between two **geographic bearings**, not an orbital distance, current sky position, astrological aspect or angle between the planets as seen simultaneously. Two rise/set events can occur at different local times and do not imply spatial proximity.

## HOW TO USE

Once reviewed, authorized for merge, and separately installed on the operator's Fedora system:

1. Open Weather Station → SUBJECTS → COSMOS → ASTRONOMY → PLANET CLOCK → HORIZON, or INDEX → COSMOS → PLANETS AND STARS → PLANET RISE/SET → HORIZON.
2. Click **COMPARE** in the Horizon header.
3. Select Planet **A** and Planet **B**, then RISE or SET. The center dial shows source-true compass directions with a magenta shorter-gap arc and angle readout.
4. Click either A/B circular marker to inspect its timestamp and azimuth. FOCUS A and FOCUS B are also real buttons, including when both markers coincide. HORIZON returns to five concentric rings; TIMELINE returns to the 6/12/24h graph.

## VERIFY

- `tests/weather/test_cosmos_bearing_comparison_v3c.js` checks north-wrap (350°→10°), direction reversal, 0° and 180° cases, same-date/source requirement, special/missing events, bounded QML list input, cardinal mapping, clickable A/B hit-testing and focus controls, single USNO provider, and 414px mounted-view boundary.
- Existing `.github/workflows/weather-cosmos-planet-events-v2b.yml` triggers for V3c source/QML/tests and runs V3c plus V3b, V3a, V2b, V2c, V2d, prior COSMOS visual and navigation regressions.
- GitHub Actions PR-head results and mergeability require current independent verification. Native Qt/Quickshell Canvas drawing, hover/pointer event delivery, font fallback, view height and scroll containment remain **UNVERIFIED** until the operator tests locally.

## WATCH OUT FOR

- **Do not label this an aspect wheel.** An angular gap between rise/event bearings measured at different times is not ecliptic longitude separation, geocentric planetary angle, conjunction, heliocentric position, or an observed simultaneous separation. The MAGICK JPL pipeline is the appropriate owner for those.
- Missing input should show an unavailable state. Never fill a gap with simulated coordinates or use an unrelated fallback date/time.
- A/B event markers may coincide; direct FOCUS controls preserve inspectability. The shorter-gap arc chooses clockwise/counterclockwise for values strictly between 0 and 180, not a causal or temporal direction.
- 414px QML host, Gohu glyph/text sizes, Canvas arc appearance and native mouse clicks must be tested on the real station. CI cannot prove rendering.
- Operator likes circles as useful, distinctive retro CRT instruments. Keep the source values legible, selected controls actionable and color meanings consistent.
- The separate worker owns SUBJECTS/CLASSIC and MAGICK lens design. No navigation/integration ownership was transferred and no live Hospital connection is claimed.

## CHECKLIST

- [x] Verify V3b #1187 merge, source and current ownership
- [x] Review MAGICK JPL instruments and new design boundary #1191
- [x] Pure source-derived azimuth comparison and circular QML pane
- [x] Real R/S selectors, A/B markers and focus buttons
- [x] Narrow internal switch behind V3b Horizon view, no shared navigator
- [x] New regression tests and CI workflow wiring
- [ ] Verify PR-head CI green and merge safety
- [ ] Operator-approved native Fedora install/test and visual feedback
- [ ] Operator acceptance

## NEXT

Review PR and GitHub CI, resolve only evidenced failures, then request merge/deployment approval under current rules. Native acceptance should check 350°/10° wrap, A/B selection, coincident bearings, RISE/SET mode changes, true-north geometry, correct local times, absence of fake values and HORIZON/TIMELINE return. For true JPL celestial separations and spatial/astrological modes, coordinate with the MAGICK owner and its latest operator-approved design doc rather than duplicating source engines.

## DECISIONS

Lane B = COSMOS visual intelligence. V3c is a local horizon *bearing* comparison, not an expansion into MAGICK interpretations or new ephemerides. Read-only source consumption and no local machine modifications. Technical CI completion != native rendering or operator acceptance.
