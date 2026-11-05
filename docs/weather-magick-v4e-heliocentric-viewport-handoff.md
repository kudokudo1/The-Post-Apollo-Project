# Hospital // Weather Station MAGICK V4e viewport containment

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station / COSMOS + temporary MAGICK Visual Intelligence
STAFF ROLE // Nurse 2, external Hospital-compatible (not live registered)
ASSIGNMENT // Protect HELIO/outer-body rendering after the completed MAGICK menu reformat
PHASE // GitHub isolated draft review; native operator acceptance pending
BRANCH // fix/weather-magick-v4e-heliocentric-viewport-containment-20261105

## IMPLEMENTATION

The operator supplied multiple native Fedora/Quickshell screenshots of MAGICK instrument modes, confirmed the graphs/controls visually pass, and noted Neptune or farther bodies can escape the limited HELIO viewing frame at some zoom modes. The operator then confirmed that the separate MAGICK menu reformat has finished. Re-checked the current main branch (including newly merged compact-mode instrument/toolbar), PR #1266 merged, and no open Weather/MAGICK PRs at preflight.

The verified source math, M4/JPL kernel, ten-body heliocentric atlas, source/UTC identity, timeline controls and MAGICK menu geometry are untouched. This is a drawing-only containment patch.

- widgets/weather/StationCosmosHeliocentricPolicy.js keeps the original source-exact \`position()\` calculation. New pure \`viewport()\` derives safe dimensions from canvas size: the new compact MAGICK page uses the full available Canvas, and noncompact mode reserves the existing right-side inspector. \`viewportMarker()\` clips only **display coordinates** and returns an explicit \`offscreen:true\` directional marker when a body's real projected position lies outside the safe plot. \`labelPosition()\` keeps long system-barycenter names inside the current plot width. \`visibleHit()\` uses the same bounded visual position so an edge indicator remains clickable. The original \`hit()\` and \`position()\` contracts remain intact.
- widgets/weather/StationCosmosHeliocentricPane.qml clips Canvas drawing to that actual plotting rectangle, including expanded zoom rings and source rays, and uses directional triangular pointers for offscreen bodies rather than drawing displaced planet dots. Source AU and XYZ remain unchanged in the existing body inspector. Selected/hovered markers retain highlight, pointer drag remains source-time navigation, and mouse wheel remains spatial zoom. Source body text gets an explicit OUT suffix if its actual projection is beyond the safe plotting rectangle.
- widgets/weather/StationCosmosCelestialNetwork.qml binds only \`compactPlot: graph.compactMode\`, reusing the completed MAGICK page geometry without changing menu controls, compact toolbar, source ownership or outer navigation.
- No SUBJECTS, MAGICK Overview/SubjectPane, StationSky, global header, Stage Director, backend, CSS/theme, persistent store, Quickshell restart, or local Fedora mutation.

## HOW TO USE

After authorized review/merge and separate local installation: open Weather Station > SUBJECTS > MAGICK > Celestial Reference > CALCULATE > HELIO. In ALL AU, move through sampled times and zoom strongly with the mouse wheel. In INNER 4 AU, Neptune, Pluto and other bodies outside the radial window should no longer draw beyond the box. Instead, their source-relative direction appears as a clickable edge pointer marked OUT; exact source distance and XYZ can still be selected in the existing body list. TOP/TILT and CHORDS/DEPTH switch as before.

## VERIFY

- tests/weather/test_cosmos_heliocentric_viewport_v4e.js checks compact and noncompact plot rectangles, Neptune/Pluto on opposite sides of a 4-AU radial view, high zoom and tilt bounds, exact retention of original projected coordinates/AU, edge hitboxes and painted long-label containment, as well as no new providers, timers or network.
- Existing V4a-V4d and MAGICK M4/M5 regression suites continue in .github/workflows/weather-cosmos-jpl-network-v4a.yml, now including the V4e test. PR-head CI is not a native Qt Canvas screenshot; actual rendering and clip/pointer delivery still need a desktop pass.
- Visual comparison should use the operator's new, finished compact MAGICK layout, not an obsolete CLASSIC layout. Check Neptune and Pluto at ALL and INNER, with maximum spatial zoom, including TOP and TILT. Confirm no body lines/labels overlap the header, footer or inspector and the real AU values are unchanged.

## WATCH OUT FOR

**An edge marker is not a planet at that edge.** The triangle points toward a real source-calculated position that lies beyond the selected plotting window; it does not compress, round or relocate the astronomical coordinate. Do not infer that INNER displays the true distance of Neptune/Pluto within 4 AU. A long SYS label can be horizontally fitted; the body list keeps the full identifier and exact measured value.

The revised menu geometry is owned by a separate worker and is intentionally unchanged. The operator authorized temporary cross-MAGICK visual work while the old MAGICK worker was unavailable, but did not authorize changes to the local live desktop or an unreviewed production activation. No live Hospital registration claimed.

## CHECKLIST

- [x] Current main/PR status checked after MAGICK menu move
- [x] Safe compact/noncompact plot geometry without changing parent layout
- [x] Directional edge markers for Neptune/Pluto and zoom overflow
- [x] Shared drawing/click geometry and bounded long labels
- [x] Tests and existing workflow updated
- [ ] Final PR-head CI and mergeability verified
- [ ] Operator-approved merge and separately authorized installation
- [ ] Native Fedora high-zoom and inner-system visual recheck
- [ ] Operator final acceptance

## NEXT

Run PR-head CI and correct any demonstrated source/contract failures only. The operator can review and merge when authorized. After deployment, inspect HELIO ALL AU and INNER 4 AU at extreme zoom/tilt and compare to the prior Neptune screenshot. Later V5 graphics improvements should be separately scoped and avoid modifying the newly finished MAGICK layout.

## DECISIONS

Freeze newly completed parent menu layout. Preserve true JPL data and user-tested native graph behavior. Fix geometric overflow only in the drawing boundary, with explicit offscreen direction markers rather than invented positions or hidden bodies.
