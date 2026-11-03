# Weather Station // V1 Interactive Observational Chart (COSMOS)

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station / Subject Visual Intelligence V1
PROVIDER // OPEN AI // CHATGPT, external Hospital-compatible
CONNECTION // EXTERNAL, not registered live
ASSIGNMENT // Reusable, genuinely interactive time-series graph based on existing recorded observations
STATE // CODE IMPLEMENTED ON ISOLATED BRANCH, CI AND MERGE PENDING
SOURCE ROADMAP // docs/weather-subjects-visual-intelligence-future-worker-roadmap-2026-11-03.md

## IMPLEMENTATION

V1 provides a first usable interactive chart in COSMOS rather than a
separate demo screen, fabricated graph, or second NOAA collector:

- `StationInteractiveSeriesPolicy.js`: pure bounded observation model,
  6h/24h/48h window filtering by **observedAtMs**, independent display
  of **receivedAtMs**, duplicate resolution by newest receipt, rejection
  of nonnumeric/future/corrupt rows, axis padding for constant/negative
  values, globally capped peak-preserving downsampling, and gap
  detection based on actual input intervals rather than interpolating
  across missing observations. Computes actual screen x/y and nearest
  recorded sample/time for inspection. Exports no network/storage APIs.
- `StationInteractiveHistoryChart.qml`: Post-Apollo colored QtQuick Canvas
  chart, independently scaled solar-wind and IMF Bz series, actual
  sample time on X, 6H/24H/48H buttons, Bz toggle, mouse hover
  crosshair, click-to-lock sample, unlock control, numeric value
  inspection, sample freshness and transparent no-data feedback.
  The two Y axes are independently normalized and **explicitly
  labeled**; do not compare their rendered heights as if units matched.
- `StationSpaceWeatherTimelinePane.qml`: read-only adapter to existing
  `WeatherLiveHistoryStore.samples("space-wind","global",nowMs)`
  (payload field `solarWindSpeed` in KM/S) and
  `samples("space-imf","global",nowMs)` (payload field `bz` in nT).
  Reuses the store revision and existing StationSpace instruments
  below the new chart.
- `StationCosmosSubjectPane.qml`: only the already-authorized COSMOS
  leaf routes `cosmos/space-weather/overview` and
  `cosmos/space-weather/history` mount the enhanced chart+instrument
  combination. All other COSMOS routes and CLASSIC maintain their
  previous source/page dispatch.

### Observable behavior

- If no actual samples are available in the selected window, say
  `NO RECORDED SAMPLES IN THIS WINDOW`.
- A single observation can be drawn as a point; never fabricate a line.
- Solar wind and IMF Bz have **different units**, each scaled on its
  own data range; toggling Bz never changes recorded values.
- A cursor/locked reading selects the nearest real timestamp, not a
  synthetic interpolation.
- The chart breaks strokes over provider gaps, rather than connecting
  hours of missing readings.
- 48h is the maximum actual history retention for these two sources.
  3d/7d chart options are deliberately absent.
- Source age uses the actual **observation clock**, not the local
  fetch/receive time. A threshold of 45min is used here, mirroring
  established solar-wind/IMF freshness policy.
- No hidden refresh timer, provider request, forecast projection,
  persistence update, or filesystem save occurs.

## HOW TO USE

After separately authorized local update:
Weather Station > SUBJECTS > COSMOS > SPACE WX.
A new solar-wind / IMF-Bz timeline appears above the existing space
weather instruments. Use 6H/24H/48H, toggle BZ ON/OFF, hover over a
point to see its observation date/time and numeric reading, click to
lock, UNLOCK POINT to resume hover. COSMOS > INDEX > SPACE WEATHER >
HISTORY also uses the same visual. Existing SPACE content remains
scrollable beneath it.

This is one real graph foundation, not the entire V1/V2/V3 chart set.

## VERIFY

Node focused source tests are in
`tests/weather/test_visual_series_v1.js`. Workflow
`.github/workflows/weather-visual-series-v1.yml` also runs COSMOS,
MAGICK, W1/W1r navigation and subject contracts. The repository's
global Weather teardown and other checks should be green.

Because remote source tests do not render a running Qt scene, CI alone
does not prove Canvas draws or mouse coordinates are perfect on Fedora.
A real Quickshell visual+mouse test requires separate operator approval.
Never claim local visual acceptance from GitHub CI.

## WATCH OUT FOR

- Numeric solar wind and IMF observations depend on the existing
  current source, sample retention and successful storage; data may
  be missing, stale or sparse.
- Hover picks an actual nearest sample. Bz and wind are not necessarily
  recorded at the same instant, so both may show unavailable unless
  within the permitted inspector tolerance. Their heights are not
  same-unit comparisons; correlation remains a separate analysis.
- Chart can be used only where the existing COSMOS reader already
  wires `liveHistoryStore`, not as an independent process.
- No new ephemeris, planetary wheel, astrology or source-wide graphic
  appears in this phase.
- No HOME, CLASSIC, W2 favorites, Stage Director, map provider or
  terminal hosting file was modified.

## CHECKLIST

- [x] AGENTS/OPERATE and source/PR preflight
- [x] Pure timestamped series and real gap/axis model
- [x] Interactive Canvas chart using existing controls
- [x] Narrow COSMOS integration with no new collectors or writer
- [x] Node regression tests and CI workflow
- [ ] Latest CI all green
- [ ] Merge into main under the previously established verified-merge authorization
- [ ] Actual Fedora Quickshell mouse/visual acceptance

## NEXT

After V1 verified merge, expand across WEATHER with real 48-hour
series and forecast-vs-observation semantics; then lunar/celestial
phase/position graphics and MAGICK lens contracts. Do not modify
the other worker's HOME/CLASSIC transfer in this lane. Require
source-backed ephemerides before any alignment/retrograde graphic
claims actual planetary geometry.

## DECISIONS

A small authentic COSMOS 48h time-series chart takes precedence over
multiple demo/fake graph placeholders. Future terminal rendering
will consume the same read-only sample model, not QML/Canvas code or
another NOAA request. Operator acceptance is separate from technical
completion.
