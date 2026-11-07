# 🏥💜 MAGICK M8m // MATRIX Heatmap, UTC Event Timeline and Expandable Inspector

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station > MAGICK > ASTROLOGY > TRANSITS > MATRIX visual refinement
STAFF ROLE // DOC / external OPEN AI // CHATGPT; Hospital-compatible, NOT live-registered
ASSIGNMENT // Heatmap, visual event timeline and expandable detail panel using the accepted M8l JPL result. User decides final acceptance through visual approval; no independent review required for this sequence.
BASE // main c8d8b25eb7369e27733620095301b6f4c37fcc6f at branch creation
BRANCH // feat/weather-magick-m8m-matrix-visual-browser-20261107
SCOPE // One new pure JS visual policy, one existing MATRIX QML pane, JS tests, disposable real Quickshell QML fixture, CI, handoff.
PERMISSIONS // GitHub-only bounded implementation and testing. No local Fedora filesystem, packages, Quickshell restart, merge, production activation, or live Hospital registration.

## IMPLEMENTATION

- Retains accepted WHEEL, TIMELINE, MULTI and MATRIX route, existing private JPL source/contract, 4x4 maximum, original numeric CPU budgets, source-identical observer/kernel, event counts, and dedicated UTC date controls.
- Adds `StationMagickTransitMatrixVisualPolicy.js`, a read-only projection of the **already strictly M8l validated** MATRIX response. This library performs NO new astronomical calculation or user data persistence.
- MATRIX cell counts become an interactive source heatmap with stable bins **0 = quiet / 1-2 = cyan / 3-4 = yellow / 5+ = orange**. Magenta still indicates the explicitly selected cell, and every cell retains the actual numeric source count. A station is never represented as a natal-pair aspect count.
- Below the matrix, a compact UTC time axis plots validated event timestamps in separate **moving-body lanes**. Yellow vertical markers show aspect crossings; orange circles show moving-body stations, with day labels derived from the exact source UTC window. Pair and event-kind filters are applied to the marker set, and clicking a marker opens the inspector without launching any process or changing the WHEEL chart. A scrollable grid region contains the matrix, legend and timeline if the available panel is small; the event browser stays separately scrollable.
- Event list gains a dedicated **INFO** action beside each row; the original row click still opens WHEEL at the nearest UTC minute. INFO reveals a larger, dismissible inspector overlay with exact source UTC, planet pair or moving-body station, direction, angular residual or finite-difference station velocity, original numerical root bracket and an independent WHEEL action.
- The inspector plots **sampled moving-body apparent ecliptic longitude** using the same returned verified source sample points, with optional natal-reference horizontal line and the exact event-time vertical marker. It unwraps longitudes crossing 360 degrees and includes +/- zoom and FIT. The graph is NOT an independently recomputed exact-second ephemeris curve: the exact contact time is from the root finder and the moving positions are sampled values.
- Does not touch `scripts/weather/celestial_transit_matrix.py`, `CelestialTransitMatrixService.qml`, shared Colors/ActionButton, TASKS, Settings++, Location, natal chart storage, or any live desktop state.

## HOW TO USE

After a separately authorized merge and deployment: Weather Station → MAGICK → ASTROLOGY → NATAL, calculate a JPL natal chart; enter TRANSITS → MATRIX. Choose natal/moving bodies, UTC search range, 30/60-minute cadence and aspects, then SEARCH. Cell fill indicates the number of detected exact angular contacts; numbers are still visible. Click a colored cell to filter the event list and time axis to that natal/transit pair. On the time axis, click a yellow or orange marker to inspect its source event; or press INFO on any event row. Use +/- and FIT in the inspection panel to zoom the sampled longitude. CLOSE returns to MATRIX; WHEEL or a normal event-row click opens the original minute-rounded chart while keeping exact source event UTC labeled.

## VERIFY

- `tests/weather/test_magick_matrix_visual_m8m.js`: stable heatmap bins, authenticated source cell counts, exact UTC day/planet lanes, event-kind/pair filters, distinguish stations with no natal pair, inspect source UTC/angle/rate/bracket, unwrap 358→1-degree apparent longitudes without a 360-degree display jump, zoom around exact event, no mutation/storage and old wheel navigation.
- `tests/weather/fixtures/M8mNativeMatrixVisualShell.qml` plus `scripts/weather/verify_magick_native_m8m.sh`: real Qt/Quickshell QML fixture under disposable HOME/XDG paths with source-shaped synthetic JPL response, tests 4x4 workload, 16 matrix cells, source heatmap tiers, UTC lanes, INFO selection without WHEEL navigation, visible detail geometry/zoom, station inspector with no natal attribution, original WHEEL callback.
- `.github/workflows/weather-magick-m8m-matrix-visual.yml`: new JS source contract and actual offscreen Quickshell job plus M8l, M8k and M8j regressions. Check final head results before claiming success.
- Real Fedora/SwayPX UI is not directly modified or inspected. Actual JPL kernel numerical comparisons were outside this UI-only assignment.

## WATCH OUT FOR

- Visual bins are counts of **source-detected crossings**, not their importance, severity, spiritual causation or personal relevance. Red remains reserved for destructive actions.
- The time axis marks exact returned event UTC and labels source days. The inspected longitude curve uses sampled tracks and must not be mistaken for a continuous high-precision astronomical trace.
- A numerical 1-second bracket for aspect crossing and 60-second bracket for finite-difference station search is not guaranteed observational accuracy. Station search can miss very brief reversals. Existing WHEEL still calculates nearest UTC minute.
- Visual grid may scroll on small panels. QML offscreen CI proves component structure and signals, not actual Fedora panel geometry, mouse feel or operator acceptance.
- No independent reviews will be requested for this sequence, per operator. Automated regression and explicit user visual approval still apply. Merges/desktop deployment remain separate operator permissions.

## CHECKLIST

- [x] Read AGENTS, Hospital and Post-Apollo guide; verify current main/merged M8l/no competing MAGICK PR
- [x] Implement source-derived heatmap, no changes to JPL backend or pair counts
- [x] Implement UTC event lanes and individual source marker inspection
- [x] Implement expandable view, sampled longitude graph and original WHEEL handoff
- [x] Add deterministic JS, disposable native QML and CI workflow
- [ ] Final PR-head CI, repair any real defects
- [ ] Operator merge decision and native Fedora visual approval (sole acceptance authority)

## NEXT

Verify all GitHub Actions and repair only M8m source/UI defects. Prepare operator-facing visual test path. After user approves live M8m, consider event-density legibility and performance if actual screenshots expose issues. Do not broaden into additional natal/transit numerical computation without a new assignment.

## DECISIONS

M8l remains accepted baseline. M8m is **visual-only** and uses verified source events, not generated/imagined astronomy. User's visual approval is the final acceptance gate for this MAGICK work; no independent second-worker review requirement. No silent merge or local desktop writes, no live Hospital registration.
