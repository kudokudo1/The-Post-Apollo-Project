# Hospital // Weather Station V4g HELIO / NETWORK regression recovery

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / temporary MAGICK bridge
STAFF ROLE // Nurse 2, external Hospital-compatible, no live registration verified
ASSIGNMENT // Repair the blank HELIO Canvas and missing compact NETWORK buttons
PHASE // GitHub draft, native acceptance pending
BRANCH // fix/weather-magick-v4g-helio-blank-network-modes-20261105

## IMPLEMENTATION

On 2026-11-05 the operator supplied two Fedora/Quickshell screenshots showing ASTROLOGY > HELIO completely blank despite its visible TOP/TILT/ALL AU/INNER toolbar, and NETWORK showing a relationship ring without the older CHORDS/DEPTH controls. Current main was inspected; V4f PR #1316 was merged; no competing open Weather/MAGICK PR was returned.

Two independent root causes were verified:
1. The V4f cameraOrigin function returned an object containing cx, cy and r, but not ready. HELIO Canvas.paint expected a ready flag and returned before any drawing. The policy now returns ready:true for valid camera geometry; the Canvas checks for null geometry during early QML Loader mounting.
2. The completed compact MAGICK reformat split NETWORK and HELIO into separate top-level tabs, hid the original inspector in compact mode, and forced NETWORK to display CHORDS. DEPTH remained implemented but unreachable. A compact CHORDS/DEPTH toolbar was restored within NETWORK's own plot, leaving HELIO as its separate main tab. A child signal requests the mode through instrument.networkMode so the parent's displayMode binding survives switching between NETWORK and HELIO.

Only HELIO policy/pane, NETWORK chart, celestial instrument, dedicated regression test, existing workflow and this handoff changed. No menu routes/geometry, JPL data, source process, other widgets, local Fedora files or Quickshell restarts were changed.

## HOW TO USE

After authorized merge and separately approved local install: open MAGICK > ASTROLOGY > HELIO. The source-verified Sun and planets should draw again. Check TOP/TILT, ALL AU/INNER and camera pan/zoom. Switch to NETWORK; the small CHORDS and DEPTH buttons should show two distinct diagrams. Switch to HELIO and back; NETWORK should remember which submode was selected. The old full/noncompact inspector still has its original three-way controls.

## VERIFY

New tests/weather/test_magick_helio_render_network_modes_v4g.js checks the exact formerly missing readiness flag, null/invalid camera geometry, HELIO Canvas guard, retained camera drawing, CHORDS/DEPTH toolbar source and parent signal wiring, standalone HELIO mode, existing noncompact inspector and no additional process/network. Existing Weather COSMOS V4a-V4f plus MAGICK M4/M5 tests run in the original workflow, now extended with V4g.

CI status on exact PR head must be confirmed before declaring automated verification. GitHub CI cannot directly confirm native Qt Canvas rendering or actual mouse interaction.

## WATCH OUT FOR

The operator's compact menu reformat is complete and deliberately preserved. Full inspector remains hidden in compact mode, with targeted visible controls instead. Source JPL coordinates and frames are unchanged. Native visual confirmation remains required; no Hospital registration, local deployment or final operator acceptance is assumed.

## CHECKLIST

- [x] Current GitHub and ownership reviewed
- [x] HELIO early-return rendering regression repaired
- [x] Missing compact NETWORK CHORDS/DEPTH controls restored
- [x] HELIO standalone tab and existing instrument retained
- [x] Regression and CI workflow updated
- [ ] Exact PR-head CI green
- [ ] Authorized merge and separate deployment
- [ ] Native visual test and operator acceptance

## NEXT

Verify CI and fix evidenced failures only. Review PR, obtain appropriate merge approval, and separately install on Fedora with operator approval. Check HELIO vs original blank screenshot and NETWORK mode switching vs original missing-buttons screenshot. The returning MAGICK worker must reacquire the latest Room/Patient/Git state.

## DECISIONS

A bounded repair of two proven regressions, not a redesign. Keep new MAGICK navigation and full source-verified JPL/UTC/camera capabilities unchanged.
