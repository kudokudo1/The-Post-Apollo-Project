# 🏥💜 MAGICK M8h // Multi-Planet Transit Atlas and Event Browser

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station MAGICK / Astrology / Multi-Planet Transit Expansion
STAFF ROLE // External Hospital-compatible DOC (OPEN AI // CHATGPT)
LIVE HOSPITAL CONNECTION // Not verified, no registration claimed
ASSIGNMENT // Operator approved feature expansion #4: multi-planet trajectories, aspect filters, direct/retrograde station analysis, fuller event browser
BASE // main at ae620576f1a8af99b5d7896ea573975125b7c6e2
BRANCH // feat/weather-magick-m8h-multi-transit-events-20261107
PERMISSIONS // Isolated GitHub code/tests/docs and draft PR only; no workstation writes, merges, production activation or ownership of other Weather/COSMOS work

## IMPLEMENTATION

- `scripts/weather/celestial_transit_multi.py` reuses M8f's sign-bracketed angular aspect crossings and M8b's Skyfield/JPL topocentric apparent longitude calculation with the exact source SHA-256. One explicitly requested natal body is compared with one to three selected moving bodies, using one installed BSP and observer. One search can cover 1/7/14/31 days at 30/60-minute source cadence, sampling each moving body independently.
- The five traditional aspect families are individually selectable, applied to the **backend request**, and validated again upon return. No client-only fake filter pretending a source was calculated.
- Station estimates: bracketing of a 20-minute centered finite-difference longitude velocity, then numerical refinement to a 60-second search bracket. A direction change from negative to positive indicates **direct**, positive to negative **retrograde**. The method explicitly does not guarantee detecting every rapid double reversal or tangential grazing aspect near a stationary body; station time is an estimate, not one-second astrophysical certainty.
- `StationMagickTransitMultiPolicy.js` fail-closes on wrong ephemeris hash, observer, tropical/ecliptic frame, NAIF identifiers, output body list, sample count, observed angular values, UTC window, unsupported aspect/station event or precision metadata. Event browser data is derived from validated source records.
- `CelestialTransitMultiService.qml` uses a separate private, one-shot cancellable process whose command line carries only executable/script/kernel; explicit event dates/location pass via bounded JSON stdin. Output is bounded and never saved to local profile, TASKS, journal, external site or logs.
- `StationMagickTransitMultiPane.qml` provides a source-backed three-line graph, compact source planet/aspect selectors, task-style UTC date field, 1/7/14/31-day spans, search button, zoom/pan/FIT, station/aspect browser filters, per-planet filtering and chronological/reverse ordering. A selected event opens WHEEL at the nearest UTC minute with the original refined/estimated event UTC and selected body intact.
- `StationMagickAstrologyPane.qml` adds MULTI beside WHEEL and TIMELINE only inside the existing TRANSITS deck. Earlier M8c/M8g routes and all natal/event input remain intact. `StationMagickTransitChartPane.qml` distinguishes an estimated station from a numerically refined aspect crossing and displays the chosen body.

## HOW TO USE

After separately authorized merge and native deployment:

1. Weather Station → MAGICK → ASTROLOGY → NATAL, enter the actual event UTC time and coordinates, calculate JPL natal chart.
2. TRANSITS → MULTI. Choose an explicit UTC starting date using the shared TASKS arrows/TODAY control, choose 1/7/14/31 days and 30/60 min source cadence.
3. Select a natal reference body with arrows, and turn on **one to three** transiting bodies using the compact planet buttons. Use CONJ/SEXT/SQR/TRIN/OPP to select the aspect families that the backend will search. At least one aspect must remain selected.
4. Press SEARCH. The graph renders the validated body lines and event markers. Mouse wheel or +/- zooms; drag pans; FIT restores the whole range.
5. Event browser filters: ALL / ASPECT / STATION, ALL BODIES or one selected moving body, and OLD→NEW / NEW→OLD ordering. Click a row or event marker to return to WHEEL. The original event UTC is preserved; the separate chart calculation runs at the nearest whole UTC minute. Choose WHEEL or TIMELINE to return to old displays.

## VERIFY

- `tests/weather/test_magick_transit_multi_m8h.py`: UTC/source/body bounds, independent analytic direct/retrograde stationary turning points, no false stationary detection on constant/linear motion, three-line aggregation, source-driven aspect filters, source privacy and existing numerical search reuse.
- `tests/weather/test_magick_transit_multi_ui_m8h.js`: validated three-line source fixtures, exact NAIF checks, mismatched hash/location/UTC/body/event/source rejection, aspect and station browsing, graph geometry, event time rounding, old mode preservation and no QML persistent/network side effects.
- `tests/weather/fixtures/M8hNativeMultiTransitShell.qml` with `scripts/weather/verify_magick_native_m8h.sh` loads real Quickshell/Qt in a private offscreen environment. Tests chart-verified synthetic response parsing, 3-line geometry, event filters, sort, zoom/FIT, event body & timestamp handoff. CI does not run real JPL kernels or the live desktop.
- `.github/workflows/weather-magick-m8h-multi-events.yml` runs Python, Node and real offscreen native QML independently, plus prior M8f/M8g/M8b/M8d regressions. Check exact PR-head workflow status before claiming success.

## WATCH OUT FOR

- These aspects and station labels are traditional astrological angular conventions attached to measurable ecliptic positions, not evidence of a physical predictive or causal mechanism.
- This is **1 natal body vs up to 3 moving bodies**, not a 10×10 all-body search. The limit bounds CPU, numerical complexity, event count and private output. A complete all-planet planner needs explicit performance/security limits and additional operator approval.
- The source samples every 30/60 minutes. It refines sign-changing aspect crossings to a one-second time bracket, while stations are 20-minute centered-velocity estimates with a 60-second refinement bracket. Tangential aspects and very short double stationary reversals may be missed.
- Uses explicit natal-site observer coordinates, not a live device GPS fix. Explicit UTC is mandatory; historically correct birth/event location still matters.
- A click on an aspect/station returns the WHEEL at the nearest whole UTC minute; the source event UTC with seconds remains displayed. This is not an exact-second chart.
- No local Fedora/SwayPX, real DE440s numerical output, screenshot review, mouse-gesture desktop validation or operator final acceptance has been performed through this GitHub workflow.

## CHECKLIST

- [x] Recheck Syntagma and Hospital preflight, source ownership and exact main SHA
- [x] Verify merged M8g and no competing open MAGICK/transit PR
- [x] Implement bounded 3-body JPL event source and finite-difference station search
- [x] Add selectable aspect filters and source-validated results
- [x] Add event browser, source curve, native UTC date controls and event→wheel handoff
- [x] Add Python/Node/offscreen-Quickshell tests and CI
- [ ] Verify exact PR-head CI and resolve failures
- [ ] Independent second technical review
- [ ] Real DE440s comparison and Fedora native UI acceptance
- [ ] Operator merge and live deployment decision
- [ ] Operator final acceptance

## NEXT

Inspect CI against the latest PR head and repair only true source, QML or test failures. Keep draft/unmerged pending independent review and user authorization. A follow-on milestone may improve high-density multi-line legibility and multi-natal-body event planning, but must preserve verified source and CPU caps.

## DECISIONS

Operator approved skipping directly to feature expansion #4, not bypassing merge/deployment safety gates. Reuse exact JPL numeric source and TASKS date controls; no fake sky chart or image generation. Keep existing WHEEL and TIMELINE intact and separate. Hospital state/room are externally compatible, not live registered.
