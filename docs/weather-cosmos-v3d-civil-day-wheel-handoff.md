# Hospital // Weather Station COSMOS V3d 24-Hour Planet Event Wheel

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence, Lane B
STAFF ROLE // NRS-2, external Hospital-compatible; no live registration
PROVIDER // OPEN AI // CHATGPT
ASSIGNMENT // V3d interactive, source-backed circular 24-hour planetary event view
STATE // Draft PR, review/CI/native acceptance pending
ROADMAP // docs/weather-subjects-visual-intelligence-future-worker-roadmap-2026-11-03.md

## IMPLEMENTATION

- Verified merged V3c PR #1194, current source ownership, and new CLASSIC-source-removal PR #1195. No competing COSMOS open PR at start of assignment. The independent MAGICK JPL pipeline still owns ecliptic position, aspect and solar-system renderers.
- New `StationCosmosPlanetDayWheelPolicy.js` translates *only real dated USNO MRST rise / transit / set event times* into a clockwise 24-hour polar display: **00 at top, 06 at right, 12 at bottom, 18 at left**. Five concentric radial lanes identify Mercury (inner), Venus, Mars, Jupiter and Saturn (outer). Ring radius is a categorical UI lane, **not orbital distance, geographic bearing, local altitude, sky position, or historical planetary trajectory**.
- Strictly validates civil date, source, event ID, planet, kind, HH:MM and minute equality. Invalid, wrong-day, malformed, unavailable and continuously above/below-horizon provider results yield no plotted points. Event sort preserves actual local minute and source-backed event identity. Bounded QML list-like arrays are supported, with hard 15-event cap and no writes.
- New `StationCosmosPlanetDayWheel.qml` draws five cyan/magenta highlight rings and color-coded R (cyan rise), T (magenta transit), S (orange set) event markers. Real per-planet and per-kind filters are clickable, marker hover/click-to-lock works, empty rings click to select/unselect a planet, PREV/NEXT traverse real chronological events, UNLOCK clears selected state. Inspector shows exact original date, source and time.
- The existing `StationCosmosPlanetEventClock.qml` gains a **DAY RING** button beside HORIZON. The existing `StationCosmosPlanetHorizonPane.qml` gains a DAY RING button too. A sibling internal view consumes the existing `clock.rows`, `clock.selectedPlanet`, `clock.selectedKind` and `clock.sourceReady`. The original 414px root, V2d Timeline, V3a/b Horizon and V3c Compare views remain present. No new outer SUBJECTS route or navigation policy.
- No changes to `StationSky.qml`, global navigation, HOME, CLASSIC migration, services, ephemeris bridge, source fetchers, persistent stores, Stage Director or local Fedora files.

## HOW TO USE

After review and merge under operator authorization, and separately approved local installation: Weather Station → SUBJECTS → COSMOS → ASTRONOMY → PLANET CLOCK → **DAY RING**. Also accessible through HORIZON → DAY RING. Choose ALL or one planet and ALL EVENTS / RISE / TRANSIT / SET. The circular angle means local event time, not compass direction. Click a colored marker to inspect its original USNO event; tap an empty circle to filter that planet; PREV/NEXT cycle actual dated events and UNLOCK resumes hover. TIMELINE and HORIZON return to the other existing instruments.

## VERIFY

- `tests/weather/test_cosmos_planet_day_wheel_v3d.js` validates midnight/noon/06/18 geometry, strict datetime and minutes, five concentric identity radii, 15 collocated real events remaining independently selectable, empty-ring click hit-testing, source/date corruption refusal, bounded QML list integration, chronology, QML action handlers and single existing USNO provider.
- Existing `.github/workflows/weather-cosmos-planet-events-v2b.yml` now triggers for both new source files and runs V3d alongside V2b/V2c/V2d/V3a/V3b/V3c, prior COSMOS V2/V2r/C1 and W1r regressions. PR head status must be checked.
- Native QML rendering (real canvas, fonts, input propagation, parent scroll containment, geometry at actual station width) remains UNVERIFIED until operator desktop test. Code CI cannot prove the buttons or markers receive actual mouse events.

## WATCH OUT FOR

- Do not call this an orbital clock, ephemeris position wheel or planetary aspect: the angular coordinate is time-of-day for a discrete rise/transit/set calculation; different markers can refer to different moments. The existing MAGICK JPL source and associated M4/M5 relationship instruments are separately owned.
- Concentric rings are display lanes, not radial planet measurements. No interpolation or fake motion between events.
- The 414px fixed-host and narrow left-rail screen should be verified for tick labels and hit areas; ring marks are 5px radii with 8px hit tolerance. Native-scale users may want a larger interactive compass or detachable fullscreen view in a later milestone.
- The parent header is denser with the new DAY RING shortcut. If it clips at actual station width, adjust the isolated title/control composition, not SUBJECTS global placement.
- Preserve CLASSIC migration ownership and source-consumer separation; no new timers, Process, network, storage writes, location lookups or user machine updates are authorized by this draft.

## CHECKLIST

- [x] Verify V3c merged and current code baseline
- [x] Add strict source-only 24-hour polar data adapter
- [x] Implement interactive five-planet circle and honest markers
- [x] Wire internal DAY RING switch; preserve previous views
- [x] Add unit/contract regressions and CI trigger
- [ ] Final GitHub CI green
- [ ] Native Fedora/Quickshell visual and mouse test
- [ ] Operator acceptance

## NEXT

Check dedicated CI and other repository checks. If green, keep PR draft for review/merge decision; no automatic production activation or local installation. Once installed, inspect midnight/06/12/18 orientation, identical event times on five rings, filter, empty-ring click, lock/unlock, PREV/NEXT, source/date status and return to original timeline/horizon.

After native acceptance, a coordinated MAGICK-JPL read-only shared-visual contract could support a true ecliptic zodiac/alignment display; do not build a second astronomy calculation engine without the owning worker.

## DECISIONS

Continue **Lane B** only. User likes circles that convey relationships. The V3d wheel makes *actual local civil-time events* spatially scannable while preserving astronomical distinctions and all existing worker ownership. Technical merge/test completion is not user acceptance.
