# 🏥💜 Hospital // MAGICK V5b HELIO AU + Sampled Motion

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / temporary MAGICK bridge
STAFF ROLE // Nurse 2, external Hospital-compatible, not live registered
ASSIGNMENT // First source-true radial scale and selected-body sampled motion in the approved V5 HELIO interface
PHASE // Isolated GitHub draft / CI review; separate native operator acceptance
BRANCH // feat/weather-magick-v5b-helio-au-sample-traces-20261106
RECOVERY // V5a PR #1333 merged a2d18241cd23f50de67e2d458bb5b4efc57c4319; native operator reports "MUCH BETTER (caps was used with intent)"

## IMPLEMENTATION

The operator expressly approved the V5a visual design with screenshots at several native zoom levels and acknowledged the proposed V5b continuation with "okay." Rechecked Meta-Apollo-Logos-Syntagma AGENTS and Hospital/permissions/working guide, current GitHub main and active PRs. No open MAGICK/Weather PRs found at preflight. This bounded follow-up is a new visual implementation assignment, not an assumption of live Hospital ownership or a request to rewrite source contracts.

- Existing HELIO Canvas (widgets/weather/StationCosmosHeliocentricPane.qml) had four rings drawn at 1/4 increments of camera radius, but they were not numbered in AU. New widgets/weather/StationCosmosHelioScaleMotionPolicy.js calibrates those rings to the **existing active JPL source domain**, showing real AU labels. ALL gives quarters of current outermost source Sun-distance; INNER gives 1, 2, 3, 4 AU rings (where the source max is >= 4 AU). Camera pan/zoom moves these same physical rings; camera pixels are never relabelled as AU.
- The existing validated 10-body multi-epoch Sun-centered data contract contains up to 181 exact UTC samples per celestial body, so no new provider or JPL process is needed. The pure policy verifies the selected exact body, source kernel name and hash, geometric Sun origin, true-ecliptic-of-date frame and full UTC ordering before extracting a bounded window of at most **25 original source positions** centered on the current sample. No interpolated coordinates or fabricated orbital track.
- The diagram shows small, discrete cyan past-sample and magenta future-sample dots for the selected source body only, using the same 2D camera projection, AU scale, TOP/TILT, clipping and source coordinates as the existing point. Close subpixel dots are skipped for visual clarity, without modifying source data or selected time.
- A small footer within the plot explicitly reads "JPL UTC SAMPLES // NO INTERPOLATED ORBIT". These are sparse point samples expressed in **true ecliptic of date**, not a physically continuous or fixed-inertial Kepler orbit. A true physical orbital trail would need a separate clearly identified fixed frame and checked track.
- All V5a label collision priority, selected body JPL/AU plaque, V4f camera drag/zoom, time scrub, and V4g NETWORK/HELIO and compact MAGICK layout remain unchanged. No QML timer, subprocess, network, database, new window, local Fedora edits or Quickshell restart.

## HOW TO USE

After review, authorized merge and separately approved local deployment: Weather Station > MAGICK > ASTROLOGY > HELIO, then CALCULATE using the existing local JPL kernel if needed. In ALL AU, numbered rings correspond to quarters of the real outermost source AU radius; in INNER 4 AU, they are 1/2/3/4 AU. Select a planet using the existing markers or body inspector: small cyan/magenta dots depict source positions **before/after the selected UTC sample**. The exact source time, frame and body remain unchanged when moving the camera. Drag to pan, wheel zoom, Shift+drag to scrub samples, double-click body to focus, double-click background to reset as before.

## VERIFY

- New tests/weather/test_cosmos_helio_au_motion_v5b.js checks known 4 AU and 40 AU graduations, zoom-independent AU values, accurate bounded 25-source-position extraction and timeline endpoints, real source frames/fingerprints/UTC consistency, malformed/stale input refusal, no continuous orbit or extra provider, and unchanged V4f/V4g/V5a camera/label bindings.
- Existing .github/workflows/weather-cosmos-jpl-network-v4a.yml runs V5b with all earlier V4a–V5a and M4/M5 source regressions. Verify exact PR-head CI before reporting green.
- GitHub source/Node tests do not prove native Qt Canvas text layout or readability with GohuFont. Operator's screenshot review remains necessary before declaring V5b visually accepted.

## WATCH OUT FOR

These discrete data points are not a continuous orbit. In the true-ecliptic-of-date frame, coordinate axes change slightly between timestamps. Never present this point cloud as a fixed-inertial physical trajectory or infer a velocity from its onscreen slope. V5b does not change physics or astronomical accuracy, and it does not multiply JPL calculations. At low zoom outer-planet motion may be subpixel and sampled dots deliberately suppress to avoid clutter; deeper zoom reveals them. The selected body's current sample remains the ordinary clickable planet marker.

The source domain for ALL is the verified outermost body at the selected UTC sample; it changes only as source geometry changes. INNER remains 4 AU when sufficiently populated. Existing camera is finite 0.02–160 and should not be expanded for this work.

No source changes on the user's live desktop, no merge or production activation. Hospital external only; returning MAGICK worker must reacquire current Room/Patient/Git state.

## CHECKLIST

- [x] Current GitHub/source/owner audit; V5a native acceptance checkpoint read
- [x] Calibrated AU ring policy and source-verified selected-body sampled dots
- [x] Preserved camera, existing JPL schema, menu and label clarity
- [x] Dedicated source, window, ruler and presentation regression tests
- [x] Workflow wiring
- [ ] Exact PR-head checks green
- [ ] Operator-authorized merge and separately approved local deployment
- [ ] Native GohuFont label/readout inspection, sample behavior, and user acceptance

## NEXT

Verify GitHub PR exact-head checks, repair only evidenced failures, then leave draft for operator review. On approved local installation, test ALL/INNER at both zoom extremes, selected Earth/Moon versus Neptune, time scrub and source-offline behavior. The next richer visual milestone could add explicit fixed-frame trajectories as a new independent scientific product, but is **not authorized or included** in V5b.

## DECISIONS

V5a operator-approved label contrast and circular language remain baseline. V5b adds only physically labelled AU graduations and discrete, honestly described source samples. Do not invent or infer orbital tracks and do not expand the existing MAGICK layout or process graph.
