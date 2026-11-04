# MAGICK M5j // Wheel Input Stability and Zodiac Focus Emphasis

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Visuals
STAFF ROLE // External Hospital-compatible development worker, no live Hospital registration verified
ASSIGNMENT // Fix operator-reported jittery zodiac wheel/map input and increase selected-sign prominence while dimming idle signs
PERMISSION // GitHub-only bounded implementation, no merge or local Fedora write/restart
BASE // main 548c73a094158cd7a001edffc8a4d8ac37ad1693
BRANCH // fix/weather-magick-m5j-wheel-drag-focus-20261104
PREVIOUS // M5i zodiac vectors PR #1176 merged and operator screenshot confirms signs and timeline handle working

## IMPLEMENTATION

The original wheel/relations MouseArea mapped the pointer's absolute X coordinate to a timestamp across the entire M4 viewed range on drag; even a short gesture could jump to a distant time. Additionally, an unlocked wheel changed its hovered sample as the mouse moved, causing frequent full glowing Canvas repaints and a shifting wheel even without an intentional scrub. These are observed mechanisms in current QML, and credible causes of the reported jitter. Native mouse hardware/frame-time verification remains pending.

Only three presentation files changed:
- widgets/weather/StationMagickCelestialVisualPolicy.js: new pure \`wheelDragIndex\` uses the sample at press time plus a symmetric **12px per actual M4 sample** change, bounded by the zoomed view's sample indices. Right/left half-steps are symmetric; no interpolation, extra JPL calls, or timeline changes.
- widgets/weather/StationMagickCelestialInstrument.qml: new gestureStartIndex captures the visible sample on press; wheel and RELATIONS drag use delta X relative to original press instead of current canvas X. Hovering over WHEEL/RELATIONS does not scrub time; CHART hover inspection remains intact. Lock/repaint state changes only when the selected source sample changes. Changing mode clears prior chart-only hover, and pointer exit respects active presses. Existing click-to-select body, wheel-to-zoom, drag-to-pan on charts, explicit timeline slider and EVENT/TIME controls remain.
- widgets/weather/StationMagickZodiacVectorPolicy.js: introduces pure \`appearance(selected)\` styles, with idle chips slightly muted and smaller and active one drawn at ~23% larger chip radius and ~28% larger symbol scale, stronger ink and halo. Wheel draws eleven idle signs first and selected sign last so it is legible even with tight neighboring labels. All signs keep original 30-degree tropical sector positions and actual M4 planetary data.

No new QML MouseArea overlay, provider, process, timer, storage, mouse speed setting, or new visual/ephemeris data source.

## HOW TO USE

After operator review and authorized merge/deployment through the normal local process:

Weather Station > SUBJECTS > MAGICK > ASTROLOGY > CALCULATE > ZODIAC.

- Move mouse across wheel without pressing: the selected time should remain stable.
- Click a measured planet marker: it becomes the selected body; its underlying zodiac symbol becomes the brightest/largest sign.
- Drag horizontally starting anywhere in the chart: the current sample advances in small steps relative to *where you pressed*, not an absolute jump to the pointer's X coordinate. The release retains the last selected sampled time.
- Scroll to zoom the viewed timeline; drag remains bounded to the current visible M4 window.
- RELATIONS view uses the same stable fine scrub, while the dedicated glowing timeline thumb remains the coarse/absolute scrub mechanism.
- The other 11 zodiac symbols remain readable but softer. No font installation needed.

## VERIFY

New tests:
- tests/weather/test_magick_wheel_interaction_m5j.js: symmetric left/right gesture thresholds, no press-origin jump, zoom bounds, invalid source input, correct QML gesture and hover wiring, style contrasts and preservation of body selection/zoom/timeline.
- tests/weather/test_magick_wheel_focus_m5j_pixels.py: rasterizes the **same Leo symbol** in idle and selected states at compact size using appearance policy values, verifying both remain visible and selected symbol has larger/brighter actual pixels.
- tests/weather/test_magick_zodiac_visible_m5i.js updated to require the new style-based renderer without weakening the old 12-glyph/pixel preservation contract.
- .github/workflows/weather-magick-wheel-interaction-m5j.yml: Node gesture and visual tests, font-independent 12-sign raster check, M5h/M5g/M5f/M5d/M5a/M5b/M5c/HOME regressions.

Initial tuned implementation commit 16c0facc813f9394bb8581497f7720ecd48f8374: GitHub 3/3 checks passed (wheel-gesture-and-focus, font-free-compact-render, validate). These check data logic, QML source wiring, and raster visibility; they do **not** measure actual Quickshell pointer latency, GPU paint time, or Sway mouse grab behavior.

## WATCH OUT FOR

- Wheel scrub now moves ~1 source sample per 12 horizontal pixels. Intentional precision trade-off: timeline thumb covers coarse whole-period navigation. Actual M4 sample cadence remains 12h; no continuously interpolated celestial position is invented.
- QML Canvas still redraws glowing art for each *changed* sample. This patch removes redundant hover and same-sample repaints, but further performance work requires local frame-time profiling if native jitter remains.
- Chart-mode hover/time inspection is preserved. Only wheel/relations modes stop unsolicited hover scrubbing.
- The largest selected glyph chip can visually overlap neighbors at extreme compact dimensions but is intentionally drawn last; its center/source longitude remains unchanged.
- Live current widget is not changed by a GitHub PR. Operator must merge and deploy locally under established separate approval before accepting native behavior.
- This job does not modify global input/mouse Settings++, Stage Director, W2a HOME, COSMOS, weather provider sources, CLASSIC/SUBJECTS migration, JPL/Skyfield installation or terminal embedding.
- Previous PR #1176's real pixel visibility acceptance is grounded by operator screenshot; M5j native scroll/drag/glow feedback remains open.

## CHECKLIST

- [x] Reconstructed current main/head, previous PR merge and concurrent Weather PR ownership
- [x] Identified direct absolute-position-to-time jump and idle hover repaint mechanisms
- [x] Implemented bounded sample-relative drag with symmetric thresholds
- [x] Removed unsolicited wheel/relations hover scrubbing without disabling intentional clicks
- [x] Dimmed idle zodiac signs and emphasized selected sign with source-linked position intact
- [x] Added source-contract tests, compact raster and legacy checks
- [ ] Final PR-head checks/rebase status
- [ ] Operator authorized merge and local deployment
- [ ] Native pointer and compact display acceptance
- [ ] Frame-time profiling if native drag remains jittery

## NEXT

Open M5j as an isolated draft PR and verify final checks against its final commit. With operator-authorized merge/deploy, test (1) non-pressed wheel mouse movement, (2) left/right drag origin continuity, (3) scroll zoom and bounded drag, (4) click planet selection and selected glyph growth/glow, (5) timeline thumb and event marker click regressions. If jitter remains, capture Quickshell/Sway diagnostics and profile Canvas redraw rather than changing global mouse sensitivity.

## DECISIONS

Use wheel-specific fine scrubbing anchored to the active sample, while retaining the existing timeline slider for absolute coarse movement. Keep source calculations and selected sector identity exact; introduce no second input layer or changes to shared/global services. No merge, local system change, or live Hospital connection is claimed.
