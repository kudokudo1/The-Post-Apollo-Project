# Hospital // Weather Station V4f Free HELIO Camera

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / MAGICK temporary bridge
STAFF ROLE // Nurse 2, external Hospital-compatible
PROVIDER // OpenAI ChatGPT
CONNECTION // External; no live Hospital registration verified
ASSIGNMENT // Fix HELIO frozen-center camera and constrained close/far zoom
PHASE // GitHub draft, native desktop acceptance pending
BRANCH // fix/weather-magick-v4f-helio-free-camera-pan-zoom-20261105

## IMPLEMENTATION

The operator provided native Fedora/Quickshell screenshots. Earlier V4e Neptune containment works, but the HELIO solar system remains stuck around the Sun and scrolling hits a narrow zoom range. Inspected current main and Syntagma AGENTS, Hospital reporting/permissions, current owner branches and MAGICK code. V4e PR #1313 merged; no open MAGICK/Weather PR at preflight.

Root cause: ordinary left-drag was dedicated to changing UTC samples, not the camera. The wheel zoom range was hard-clamped to 0.4..5, and the orbital visualization's center was fixed in policy geometry.

The source-derived geometric JPL XYZ coordinates, measured AU, frame, UTC grid, provenance, 10-body atlas and 2-body pair calculations are unchanged.

- StationCosmosHeliocentricPolicy.js now owns pure camera pan, pointer-anchored zoom over 0.02..160, focus-to-source-body and camera-origin calculations. The original position()/hit() routines remain compatible with prior callers, while new optional pan parameters shift only screen coordinates. V4e edge markers and click targets use the same camera transform, even when the Sun itself is outside the viewport.
- StationCosmosHeliocentricPane.qml adds two pan offsets and moves its Sun, rings, source rays and selectable markers together. Normal left-drag is now two-axis spatial panning. Shift+left-drag still changes source UTC. Wheel zoom preserves the world point under the cursor. Double-click a real source body or edge indicator to center it; double-click blank chart to restore scale=1 and camera pan=0,0. Source highlighting and geometry remain intact.
- Existing compact MAGICK toolbar, TOP/TILT, ALL AU/INNER, parent layout, SUBJECTS routes, JPL service, Source collection, network and storage are unchanged. No local machine writes, subprocesses, polling or Quickshell restarts.

## HOW TO USE

After authorized GitHub merge and separate approved local installation:

Weather Station > SUBJECTS > MAGICK > Celestial Reference > CALCULATE > HELIO.

Drag the chart with the left button to pan freely. Hold Shift and drag to scrub real time samples. Scroll in/out at the mouse pointer to zoom from 0.02 to 160. Double-click a planet or OUT arrow to center that source body at the current magnification. Double-click empty plotting space to reset to the Sun-centered camera. All source AU values remain accurate.

## VERIFY

- tests/weather/test_cosmos_heliocentric_camera_v4f.js validates the old camera origin, expanded zoom range, cursor-anchor invariance in TOP/TILT, horizontal/vertical panning, Neptune focus at 160, camera movement past 10,000 pixels, clickability of offscreen markers after panning, and QML gesture hookups.
- Updated V4e source-contract test to accept optional camera arguments while preserving old projection behavior.
- Existing Weather COSMOS relationship network workflow runs V4a-V4f and M4/M5 source/interaction regressions. Check exact final GitHub head workflow status before claiming success.
- Automated source tests do NOT prove Qt native input delivery, smooth panning or rendered size. User desktop inspection remains an independent acceptance gate.

## WATCH OUT FOR

Ordinary drag controls camera position; Shift-drag controls time. These remain distinct. Zoom is finitely bounded to prevent degenerate render geometry, but the new range is much wider. At extreme zoom, overlapping labels or offscreen arrows may still require a later V5 decluttering pass. No fake JPL sources or interpolated orbital tracks are added.

Current MAGICK worker ownership and Hospital Room require rechecking on return. User has not approved local Fedora mutations or merging this draft. No live Hospital connection is asserted.

## CHECKLIST

- [x] Current main, V4e and Hospital authority read
- [x] Diagnose fixed center and zoom clamping
- [x] Pure camera pan/zoom/focus geometry implemented
- [x] Drag pan, Shift time scrub, pointer zoom, double-click focus/reset wired
- [x] Existing source data and parent layout preserved
- [x] Numerical, gesture and regression tests added
- [ ] Final PR-head CI
- [ ] Authorized merge and local deployment
- [ ] Native interaction verification
- [ ] Operator final acceptance

## NEXT

Check all CI on exact PR head and correct failures. After authorized merge and local installation, verify pointer-centered zoom in TOP/TILT, the limits in both directions, smooth two-axis panning, Shift-time scrub, edge arrow focus and blank-chart reset. The returning MAGICK worker should reacquire latest Hospital Room/Assignment and GitHub main rather than treating this handoff as live state.

## DECISIONS

Fix the movable HELIO viewing camera, not the accurate ephemeris or newly completed MAGICK menu geometry. Preserve all original data and the existing V4e source-honest clipping.
