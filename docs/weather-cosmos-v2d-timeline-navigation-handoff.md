# Hospital // Weather Station COSMOS V2d — Local-Day Timeline Navigation

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence Lane B
STAFF ROLE // Nurse 2, external Hospital-compatible
ASSIGNMENT // Add truthful zoom, drag pan, ruler and marker continuity to the existing COSMOS Planet Clock
GIT // feat/weather-cosmos-v2d-time-window-navigation-20261104
STATE // GitHub draft / verification pending; no live registration, local installation, or operator acceptance
ROADMAP // docs/weather-subjects-visual-intelligence-future-worker-roadmap-2026-11-03.md

## IMPLEMENTATION

The existing USNO date-scoped planetary event clock already shows five planets and real rise/transit/set markers. Its 24-hour plot is too compact to inspect nearby times precisely. This V2d milestone improves VISUAL INTELLIGENCE only, not navigation or source collection.

- Adds **6H / 12H / 24H** clickable local-day viewport presets in the existing ruler's 80px left slot; default remains 24H.
- Mouse wheel over an event lane or a marker zooms the 24→12→6-hour range, or zooms out 6→12→24. Zoom is anchored to the pointer's local civil minute (marker wheel uses the exact event minute).
- Left-button horizontal drag on *blank lane background* pans the reduced window; clamped to the same civil day. Marker areas remain separate click-to-lock and hover targets.
- PREV/NEXT retains original V2c behavior but now automatically reveals the chosen real event if it lies outside the current zoom window.
- Ruler labels and grid ticks are generated from the actual current time window. Center positions are tied mathematically to the source markers' clickable shells.
- Source rows and original absolute event minute values are NEVER rewritten, interpolated, lengthened or backfilled. Events outside the chosen window are hidden, not marked unavailable. There is no new ephemeris, process, collector, timer or storage writer.
- Keeps the original 414px instrument footprint and `StationSky.qml` mount exactly as they were. Only standalone `StationCosmosPlanetEventClock.qml` and its pure `StationCosmosPlanetEventPolicy.js` are modified, plus dedicated tests/CI and this handoff.
- No changes to HOME, CLASSIC migration, the SUBJECTS left rail, INDEX, MAGICK JPL engine, or Stage Director.

## HOW TO USE

After review, merge and separately approved local installation:

1. Weather Station → SUBJECTS → COSMOS → ASTRONOMY → PLANET CLOCK, or INDEX → COSMOS → PLANETS AND STARS → PLANET RISE/SET.
2. Select 6H, 12H or 24H next to the ruler, or scroll over an event lane to zoom.
3. Drag horizontally on an empty portion of a lane to pan. The ruler adjusts to real local clock times. Dragging on an event marker does not pan.
4. Hover/click an R/T/S marker to inspect. PREV/NEXT cycles *real* events and reveals a hidden event by panning the viewport to it; UNLOCK resumes hover.

## VERIFY

- `tests/weather/test_cosmos_planet_viewport_v2d.js` exercises 6/12/24-hour bounds, tick labels, source data immutability, pan edges, selective marker display, marker/ruler hitbox matching, automatic event revelation and real QML interaction hooks.
- Existing V2b/V2c, COSMOS V2/V2r, C1 and W1r regressions are run by `.github/workflows/weather-cosmos-planet-events-v2b.yml`. One obsolete V2c test prohibition of any wheel handler is updated because the explicit user preference now requires wheel zoom; safety checks against independent processes/stores remain.
- GitHub PR head and CI must be freshly checked before integration. CI code contracts do not validate actual Quickshell load, wheel delivery, drag versus parent Flickable, GohuFont tick clipping, or native pointer hitbox behavior.
- The user's earlier screenshot verifies V2b markers, not V2c/V2d native acceptance.

## WATCH OUT FOR

- These are USNO rise/transit/set event *times*, NOT positional ephemerides or a continuous arc. A 6-hour view will intentionally hide events outside its range; the provider still has them.
- The overlay's use of `MouseArea.preventStealing` makes horizontal drag useful, but a parent scrolling Flickable and input containment may interact differently on the live desktop. Native testing is mandatory.
- Chart `onWheel` consumes scroll only when hovering the lane/marker. Scroll elsewhere on the Station remains under the existing parent widget.
- Source/date changes reset the clock to 24 hours; absent data remain unavailable, not fabricated.
- If labels or hit boxes are clipped at the actual 1000px window / left rail, adjust this component and its tests, not the shared menu geometry.
- The MAGICK M4/M5 JPL visualization remains separate. Do not use rise/set times as ecliptic alignments.

## CHECKLIST

- [x] Verify V2c is merged and review current isolated component
- [x] Check open Weather PR ownership
- [x] Implement bounded viewport projection and dynamic source time ruler
- [x] Add local mouse wheel + blank-lane drag, preserve marker selection
- [x] Add read-only regression suite and workflow
- [ ] PR-head CI success
- [ ] Operator-approved live Fedora Quickshell render/pointer testing
- [ ] Visual layout and interaction acceptance by operator

## NEXT

Check PR-head CI and conflicts; keep draft until reviewed. Once merged under proper authorization, test at the actual station dimensions: 24H→12H→6H, drag to reach late and early events, wheel zoom when over markers, PREV/NEXT auto-reveal, correct labels and click-to-lock. If that succeeds, begin a separate, coordinated COSMOS/MAGICK graphical data reuse milestone; do not duplicate the JPL service.

## DECISIONS

Lane B owns the visual interactive instrument only. No organization changes, no new data-fetch logic, no local machine mutation, no merge or activation from this draft.
