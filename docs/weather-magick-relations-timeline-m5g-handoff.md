# Weather StationW // MAGICK M5g Relationship Dial and Event Timeline

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Visuals
ASSIGNMENT // M5g two-body relationship visualization and clickable source-event timeline
STAFF ROLE // External Hospital-compatible source worker; no live Hospital registration verified
BASE // main da3ee6915bdaaf0910a0a44785c512f7869772f0; M5f PR #1157 merged
BRANCH // feat/weather-magick-m5g-relations-timeline-20261103
PHASE // Draft GitHub implementation, verification and operator acceptance separate
SCOPE // Existing M5 presentation consumer only; no JPL/Python backend, Weather sources, COSMOS, Stage Director, Location, Settings++, archives or local Fedora edits

## IMPLEMENTATION

The existing MAGICK M4 graph producer supplies two bodies. M5g uses precisely that supported scope rather than inventing additional planets.

RELATIONS is a fourth instrument view:
- Displays shortest geocentric apparent ecliptic-longitude separation from M4's actual pairwise relationship sample, on a 0°–180° arc gauge.
- Uses reference ticks at 0°, 60°, 90°, 120° and 180° for the standard interpretive aspect classifications, not physical forces. The marker is the actual M4 separation and the label only names aspects present in the M4 sample.
- Body colors/labels stay linked to the source, with SYS retained for planetary-system barycenters.
- Clicking the left or right side selects one of the actual two bodies; dragging scrubs actual sample timestamps; scrolling zooms the existing sample range.
- The arc is an *angular separation ruler*, not an orbital map or a local sky scene.

A thin M4 event timeline strip now appears beneath the instrument chart in all modes:
- Source events are chronologically sorted, clipped to the currently viewed sample time bounds and categorized by M4 metadata: yellow crossing, magenta estimated station, orange grazing candidate.
- Clicking a tick selects that actual M4 event and locks the display to the nearest existing measured sample, which may be earlier/later than the calculated event timestamp.
- Clicking away from a tick picks the nearest actual source sample at that time position. Selection is strictly bounded by the current visible window.
- The selected event tick is highlighted and a white focus dot marks the nearest selected sample.
- Existing EVENT previous/next, TIME arrows, modes, axis, provenance and sample inspection remain intact.

Mode labels are now ZODIAC, MOTION, ASPECTS, RELATIONS to fit the compact rail. The chart height has been modestly reduced to accommodate the 21px event strip within the same instrument height; the outer SUBECTS navigation and layout are untouched.

Changed:
- widgets/weather/StationMagickCelestialVisualPolicy.js
- widgets/weather/StationMagickCelestialInstrument.qml

Added:
- tests/weather/test_magick_relations_timeline_m5g.js
- .github/workflows/weather-magick-relations-timeline-m5g.yml
- docs/weather-magick-relations-timeline-m5g-handoff.md

No new Process, polling timer, network call, downloaded kernel, storage file, user location inference, predictive reading or personal journal.

## HOW TO USE

After operator-authorized merge, local update and normal Quickshell restart:
1. Weather Station > SUBJECTS > MAGICK > ASTROLOGY > CALCULATE.
2. Select RELATIONS. The 0–180° gauge shows the actual source-measured longitudinal separation and body pair.
3. Click the left/right body label or drag horizontally for another sampled time.
4. Click a colored event tick to inspect a specific calculated event and its nearest real planetary sample. Click elsewhere along the strip to pick a sample.
5. EVENT and TIME arrows, zoom, pan, UNLOCK and RESET retain their earlier behavior.

The normal-launch local MAGICK JPL/Skyfield discovery remains unchanged.

## VERIFY

Implementation head after compatibility correction: 1573aa674dc9290e0cb29648a3ebab7ab2dfadfd. All nine corresponding GitHub check jobs passed, including actual JPL DE440s / M4 JSON to M5g validation inside a disposable CI runner, M5a/M5b/M5c/M5d/M5e/M5f, HOME and COSMOS regressions.

The first run identified a changed graph repaint hook breaking the original M5a contract. It was corrected without weakening earlier tests. The original graph repaint handler remains and new timeline invalidation uses the appropriate data/view/event state changes.

M5g tests validate:
- Exact source pair separation and identity; 0°–180° arc geometry; fixed traditional reference angles.
- Sort and time-range clipping of source events and provenance of each marker.
- Separate crossing, station and grazing candidate categories.
- Click hit thresholds and deterministic nearest real source sample mapping.
- Source-unavailable state and actual QML input handlers.
- JPL 29-day Moon/Sun data: every M5g separation equals M4, every drawn event maps to a real M4 event, and no fabricated sub-sample positions.

Commands from repo root:

    node --test tests/weather/test_magick_relations_timeline_m5g.js
    node --test tests/weather/test_magick_chart_legibility_m5f.js
    node --test tests/weather/test_magick_celestial_visual_m5.js

GitHub tests do not prove actual Quickshell Canvas pixels, clipping or native pointer behavior. Live UI acceptance remains separate.

## WATCH OUT FOR

- The relational arc is an ecliptic longitude gap, not a 3D sky separation, heliocentric orbit diagram, birth chart or physical influence map.
- M2/M3 search is finite-sampled. Narrow aspects can be missed; station times are estimates, and tangent candidate events can be near misses within tolerance.
- Event timestamps are calculated separately from source sample timestamps. M5g never fabricates a planetary position at an unsampled time.
- The 21px event strip may crowd on longer 90-day windows. Its 10px nearest-hit priority and compact window styling need real native verification. Clicking elsewhere selects an actual M4 sample.
- Full multi-body relationship networks require separate M4 request/event-capacity design. The current first graphical relationship instrument deliberately uses the existing pair and avoids extrapolation.
- The chart is slightly shorter; verify all bottom inspector and action rows remain accessible in the compact window.
- No local machine changes or Quickshell restart were made by the source work; merge and live activation require operator authorization.

## CHECKLIST

- [x] Verify merged M5f PR #1157 and current main/ownership.
- [x] Add source-backed two-body RELATIONS mode and actual angular reference.
- [x] Add interactive M4 event timeline across chart modes.
- [x] Preserve sample/event time distinction and correct metadata.
- [x] Backwards-compatible event/render tests and real JPL source check: 9/9 initial implementation jobs successful.
- [ ] Verify checks on final PR-head commit after documentation.
- [ ] Operator acceptance and merge.
- [ ] Native compact Quickshell rendering/click/scroll verification.
- [ ] Iterative design polish from operator screenshots.

## NEXT

Review M5g, merge only under operator authority, and after approved local deployment test both body selection, drag time scrubbing, timeline event hit testing and existing EVENT/TIME navigation. Then expand toward multi-body graph contracts and more elaborate visual modes, without claiming causal astrological effects.

## DECISIONS

GitHub-only presentation addition. Existing JPL single backend, source provenance, and current MAGICK/COSMOS/HOME ownership boundaries remain authoritative. No local writes, production activation or live Hospital registration.
