# 🏥💜 Weather Station // V3b Concentric Horizon Compass

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence, Lane B
STAFF ROLE // Nurse 2, external Hospital-compatible; no live registration claim
ASSIGNMENT // Make source-backed COSMOS Horizon Compass circular, legible, and interactive
STATE // Draft GitHub implementation, native desktop acceptance pending
GIT // feat/weather-cosmos-v3b-concentric-compass-20261104
ROADMAP // docs/weather-subjects-visual-intelligence-future-worker-roadmap-2026-11-03.md

## IMPLEMENTATION

Builds directly on merged PR #1183 V3a without creating a new page, astronomy backend, or provider process.

- `StationCosmosPlanetHorizonPolicy.js` now projects each planet's original, USNO-dated rise/set azimuth onto one of **five concentric *display* lanes**: Mercury innermost, then Venus, Mars, Jupiter, Saturn outermost. Every marker still uses the same true-north 0–360° angle from the original source. Radius is *only an identity lane* and has **no orbital distance, altitude, time, visibility, or physical size meaning**. `point(...)` without a planet preserves the V3a full-radius cardinal geometry. `pick(...)` uses the same planet lane as paint so close bearings no longer overwrite one another.
- `StationCosmosPlanetHorizonPane.qml` replaces three decorative grid circles with five softly glowing data-lane circles, highlights the inspected planet's lane, and gives only a selected event a full center-to-bearing ray. Other data markers get short radial ticks to reduce visual clutter.
- Replaces five 55px rectangular horizontal transit bars with five **73px interactive circular altitude gauges**. Each 0–90° value is mapped to a 0–100% arc, labelled in true source degrees in the center. Absent transit altitude draws an empty background ring with `--`. Click any gauge to select that planet in the main compass. Original source transit clock appears below each dial; no derived altitude is asserted as current.
- Reduces the main compass row from 212px to 194px, conserving the **414px** pane and parent V2b/V2c/V2d Timeline/Horizon mount. Does not change `StationCosmosPlanetEventClock.qml`, `StationSky.qml`, the left rail or INDEX.
- Adds a source-visible inner→outer legend and explicit disclaimer that ring depth is a UI convention, not a physical coordinate.

## HOW TO USE

After approved merge and *separately* authorized Fedora update: Weather Station → SUBJECTS → COSMOS → ASTRONOMY → PLANET CLOCK → HORIZON. Read N/E/S/W around the large compass. Cyan markers are rise azimuths and orange markers are set azimuths. Choose ALL or a planet, click a ring marker to lock its dated USNO time and angle, or click one of the **five circular transit-altitude gauges** to focus that planet. TIMELINE returns to existing zoom/pan event chart.

## VERIFY

- `tests/weather/test_cosmos_concentric_compass_v3b.js` covers five distinct ring radii; unchanged cardinal azimuth orientation; identical bearings on all five planets remaining selectable by exact source ID; missing and out-of-range transit altitudes; bounded degree-to-arc transformation; source isolation; clickable Qt interaction and unchanged single USNO source.
- The original `tests/weather/test_cosmos_planet_horizon_v3a.js` click fixture now supplies the marker's actual planet when determining its 2D position, because actual hit-testing is now planet-lane aware. Original cardinal geometry assertions still remain.
- The existing GitHub workflow runs V3b alongside V3a and V2b/V2c/V2d and COSMOS compatibility checks. Passing CI is source/regression validation, **not** native Quickshell rendering or pointer acceptance.

## WATCH OUT FOR

- Concentric rings are an instrument layout only; they must not be mistaken for planetary orbits or distances. Source azimuth still determines angular position. The independent small gauge arc represents 0–90° *transit altitude*, not azimuth or current altitude.
- Identical rise and set events **within the same planet** can still share a 2D location; use the source list or timeline in that rare case. The different planets' same-direction markers are separated on purpose without falsifying their angles.
- Source `TRANSIT` is a provider-calculated event at a specified local civil date and observer inputs, not live optical measurement. Missing-data failure must stay honest.
- Verify the 194px compass row/73px gauges, GohuFont small degrees/clock labels, 8px marker hitboxes, selected ring glow, Star scrollbar and parent Flickable on actual Fedora at current station size. There are no local writes or Quickshell restarts in this branch.
- All new work is limited to existing Horizon QML/policy, their tests/CI and this handoff. No collision with the other worker's SUBJECTS/CLASSIC migration, MAGICK JPL/astrology calculators, shared services or Stage Director.

## CHECKLIST

- [x] Check V3a merge and current source ownership in GitHub
- [x] Add five honest concentric display rings
- [x] Convert five altitude readouts into clickable circular gauges
- [x] Preserve exact true-north angles, source dates, and single collector
- [x] Add source-level and data-integrity tests
- [x] Extend existing COSMOS CI
- [ ] Final PR-head CI green
- [ ] Native Quickshell Canvas/ring/click testing
- [ ] Operator visual acceptance

## NEXT

Review PR and CI; do not merge or deploy without authorization. Once installed, verify that all five planets' rise markers remain individually clickable even when their azimuths coincide. Check missing-altitude empty rings, tap-to-filter behavior, source/date badges, text clipping and the timeline return control. Revisit the more elaborate JPL planetary motion/alignment wheel in a coordinated future Lane B milestone rather than manufacturing orbit data from USNO rise/set events.

## DECISIONS

Operator preferred richer circular instruments over adding more square cards. This implementation introduces **real-data circles**, not arbitrary decorations, while keeping the existing astronomical calculations and ownership boundaries intact. Technical completion != user acceptance.
