# Weather StationW // MAGICK M5f Graph Legibility and Geometry

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Visuals
STAFF ROLE // External Hospital-compatible source worker; live Hospital registration not verified
ASSIGNMENT // M5f polish first live M4/M5 graph instrument with readable chart coordinates and body labels
BASE // main at 1bbdcdaaf09c90fd972988d2576fe9bf4f6a56b8 (M5d PR #1155 merged, M5e normal launcher merged)
BRANCH // feat/weather-magick-m5f-chart-legibility-20261103
PHASE // Draft PR and automated verification; operator live visual acceptance remains separate
SCOPE // Existing M5 presentation policy and standalone instrument only; no new service/backend, archives, astronomy calculations, location system, navigator or terminal work

## IMPLEMENTATION

The M5d instrument correctly displays source-backed celestial positions but in compact mode the graph axes overlap lines, the time dimension has no ticks, and body identifiers near the wheel can collide. M5f addresses those source-reading problems without changing the data.

Changes:
- widgets/weather/StationMagickCelestialVisualPolicy.js
  - chartLayout(width,height): bounded plot region with a distinct degree gutter, a legend strip, a UTC date axis, preserving a minimum plot area.
  - plotX, plotY, plotFraction: same coordinate transform used by Canvas drawing and actual mouse selection.
  - shortBodyName: explicit compact body labels; labels for Mars, Jupiter, Saturn, Uranus, Neptune and Pluto barycenters include SYS, not a misleading exact mass-center claim.
  - legendRows: returns actual bodies or relationships with their existing series colors; does not invent a value or model.
  - wheelLabels: positions short text near mathematically untouched angular markers and staggers colliding labels, clamped within canvas bounds.
- widgets/weather/StationMagickCelestialInstrument.qml
  - Chart Canvas reserves a real left margin for 0–4 degree ticks, a top strip for series colors/names and a bottom strip for three UTC timestamps.
  - Lines use source series colors with selected body emphasis; actual focus samples receive visible point markers.
  - Event-marker and focus strokes respect the adjusted plotting geometry; events still come directly from M4 and M5d.
  - Pointer hit mapping in chart mode uses the same plot rectangle, avoiding axis gutters choosing incorrect samples.
  - Wheel placement keeps real ecliptic longitude angles fixed. Text alone is repositioned; no orbital data or longitude values are changed.
- tests/weather/test_magick_chart_legibility_m5f.js (new) covers chart bounds, y/x coordinate projection, click-to-sample parity, actual body colors and barycenter names, wheel angle preservation, and QML handlers.
- .github/workflows/weather-magick-chart-legibility-m5f.yml (new) runs the above with earlier M5a/M5b/M5c/M5d/M5e/HOME contracts and optional real-JPL data flow.

No changes to M0–M4 numerical engine, source provenance, date/body controls, MAGICK interpretations, Quickshell root-owned JPL service, persistence, Settings++, Weather sources, Stage Director or source installers.

## HOW TO USE

When this PR has been accepted and merged, the operator's ordinary local update/restart procedure applies; do not duplicate the running Quickshell process.

Open SUBJECTS > MAGICK > ASTROLOGY > CALCULATE. Select MOTION CURVE or ASPECT GRAPH to see visible chart axis labels, UTC time ticks, a matching legend and focus-point indicators. Existing click-to-lock, mouse wheel zoom, drag pan, EVENT navigation, body selection, UNLOCK and RESET are preserved. The wheel uses abbreviated body labels, including SYS for barycenters.

## VERIFY

Developer checks from repository root:

    node --test tests/weather/test_magick_chart_legibility_m5f.js
    node --test tests/weather/test_magick_celestial_visual_m5.js
    node --test tests/weather/test_magick_event_inspector_m5d.js

CI checks source-presentation consistency using JPL DE440s **only in disposable GitHub runner** and rechecks previous MAGICK/HOME controls.

No claim of live Quickshell pixels, layout appearance or pointer behavior until confirmed in the operator's running compact Station. The painter's content may elide or collide on very narrow viewports, and this must be checked visually.

## WATCH OUT FOR

- UTC labels are derived from existing M4 sample timestamps. Degree units apply to apparent geocentric true-ecliptic-of-date longitudes and longitude separations, *not* sky-plane 3D angular distance.
- Motion charts show unwrapped ecliptic longitude to avoid false jumps at 360°; this is a visual continuity representation. Curves may legitimately reverse during retrograde motion.
- Labels that mention SYS identify **system barycenters**, not precise planetary centers. The marker angle always remains the actual M4 longitude.
- Focus dots denote sampled values only. Events are still calculated times and may be between samples. Station times are finite-difference estimates and tangent events may be candidates.
- Only currently available source rows are plotted, with no interpolation, extrapolation, polling, network call or invented planetary data.
- Real runtime rendering/click acceptance and operator merge approval remain separate gates.
- No local Fedora files, installed dependencies, launcher settings or running Quickshell process were changed by this GitHub task.

## CHECKLIST

- [x] Latest main and active Weather PR preflight; M5d and M5e merged
- [x] Source-aware readable chart gutters, UTC x-axis, and body/relationship legend
- [x] Shared canvas/pointer coordinate transformation
- [x] Collision-aware wheel labels with unchanged angular markers
- [x] Existing sample/event/zoom/mode controls preserved
- [x] M5f tests and isolated real-JPL regression workflow
- [ ] Final PR head CI all green
- [ ] Operator acceptance / authorized merge
- [ ] Native Quickshell visual/input check at compact and expanded sizes
- [ ] Further visual design pass based on operator screenshots and measured readability

## NEXT

After M5f verification, review, merge approval, and separately approved local deployment, test native chart ticks, pointer selection, overlap and scaling. Continue expanding the visual language only after preserving the known good data-presentation seam. Automatic first-time installation for non-developer Weather Station users remains a separate MAGICK Backend Manager milestone.

## DECISIONS

Presentation-only improvement. Numerical source truth and current architecture remain unchanged. No new source service, background work, local machine writes, PR merge or production activation undertaken. Operator retains final acceptance authority.
