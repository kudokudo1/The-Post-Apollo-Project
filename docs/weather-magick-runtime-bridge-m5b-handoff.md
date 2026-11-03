# Weather StationW // MAGICK M5b On-Demand Runtime Bridge

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Backends and Visual Integration
ASSIGNMENT // Connect merged M4/M5a source-backed celestial data to MAGICK routes via a single on-demand Quickshell runtime owner
ROLE // External Hospital-compatible development worker, no verified live Hospital registration
PHASE // Isolated GitHub implementation and CI verified, operator acceptance and live Fedora runtime verification pending
BRANCH // feat/weather-magick-m5b-runtime-bridge-20261103
BASE // main at 9ad91af922a9b8fa6ca05c3a4fee940be7a7fa4c, with M5a PR #1135 merged
OWNER BOUNDARY // Do not change COSMOS collectors, CLASSIC routing, Stage Director, CPU++ Settings, Weather archive writers, or external Python environments without a separate scope

## IMPLEMENTATION

M5b uses the **existing** JPL/Skyfield M4 producer and the **merged** M5a QML visualization. There is exactly one new runtime calculation service and zero timers or recurring pollers.

- New services/weather/CelestialVisualService.qml: one Quickshell.Io Process owned by the persistent StationSubjectNavigator, not by individual MAGICK page instances.
- The service is active only on MAGICK astrology routes (charts, zodiac, aspects, retrogrades) and runs **only when the CALCULATE button is pressed**.
- New configuration reading from Quickshell.env:
  - POST_APOLLO_CELESTIAL_KERNEL: explicitly provided path to an existing local JPL .bsp ephemeris.
  - POST_APOLLO_CELESTIAL_PYTHON: optional explicit interpreter with Skyfield installed; defaults to python3, no install performed here.
- An on-demand query uses the user's already existing Station UTC clock as its date source but never infers a local timezone or geographic coordinates.
- The initial view uses a fixed 29-day window (-14 to +15 UTC days around the calendar date), a 12-hour sample step, and exactly two bodies. Charts/zodiac/aspects use Moon and Sun; retrogrades uses Mercury and Sun.
- No external network request is made by the runtime solver. The kernel is read locally and source provenance is returned from the merged M4 backend.
- The service strictly bounds output length (524288 chars), parses the JSON, checks the query frame/body IDs and source fingerprint, and exposes one read-only visualData value. The M5a presentation policy validates the full series before drawing.
- Page switches or changed UTC day/kernel configuration clear stale results without automatically triggering more calculations. In-flight jobs are stopped when the visual route becomes inactive.
- The same service reference is passed through StationWorkspaceSurface to its MAGICK pane and directly to the existing INDEX-mode MAGICK pane. There are no duplicate graph backends or redundant collectors.
- StationMagickSubjectPane uses existing routes and headers, a visible status label, an explicit CALCULATE button, and the existing StationMagickCelestialInstrument with wheel/aspect/motion defaults.
- Existing COSMOS SKY observational references remain in their own routes. Non-astrology MAGICK routes remain explanatory placeholders, not automated mystical readings.
- M4 CLI gains a **bounded --query-json argument**, allowing Quickshell.Process to pass the well-formed JSON request as a single argv element without shell quoting, temporary request files or writes. The original --query file/stdin modes remain intact.

Touched files:
- scripts/weather/celestial_visual_data.py
- services/weather/CelestialVisualService.qml (new)
- widgets/weather/StationSubjectNavigator.qml
- widgets/weather/StationWorkspaceSurface.qml
- widgets/weather/StationMagickSubjectPane.qml
- widgets/weather/StationMagickSubjectPanelPolicy.js
- tests/weather/test_magick_celestial_bridge_m5b.js (new)
- tests/weather/test_celestial_visual_cli_m5b.py (new)
- .github/workflows/weather-magick-runtime-bridge-m5b.yml (new)
- docs/weather-magick-runtime-bridge-m5b-handoff.md (this file)

## HOW TO USE

No local installation, process restart or production activation has occurred from this GitHub branch.

After operator-approved integration and local configuration, launch Quickshell with:
- POST_APOLLO_CELESTIAL_KERNEL pointing to an existing JPL .bsp file (for example de440s.bsp);
- POST_APOLLO_CELESTIAL_PYTHON optionally pointing to a Python interpreter that has Skyfield 1.55 available.

Then open SUBJECTS > MAGICK > ASTROLOGY. The existing ASTROLOGY tab enters magick/astrology/charts; INDEX can expose the zodiac, aspects and retrogrades routes.

On a supported route, the status bar shows one of:
- SET POST_APOLLO_CELESTIAL_KERNEL (AND SKYFIELD)
- UTC CLOCK UNAVAILABLE
- READY // SELECT LOAD CALCULATION
- JPL CALCULATION RUNNING
- JPL BACKEND UNAVAILABLE // CHECK PATH + SKYFIELD
- M4 RESPONSE INVALID OR INCOMPLETE
- SOURCE-VERIFIED JPL DATA LOADED

Press CALCULATE to generate the source-stamped chart data. When ready, use existing M5a wheel, motion, aspects, scroll-to-zoom, pan, click-to-lock, TIME navigation, UNLOCK and RESET controls.

Do not expect automatic background updates; each calculation requires a button click, and leaving the route clears transient results.

## VERIFY

On the pre-document implementation head 95da0823e5ffc0a2b3c195dc33ab919986fca5a4:
- GitHub validate: success.
- GitHub bridge-contracts: success.
  - M5b Node route/ownership/transport checks: 5/5.
  - Python bounded --query-json and stdin compatibility: 4/4.
  - Existing M5a visual contract: 8/8.
  - Existing MAGICK G1 and COSMOS V2R regression suites: each 6/6.
  - Existing M4 isolated graph-data checks: 10/10 (real kernel cases skipped without MAGICK_M1_KERNEL).
- GitHub jpl-to-station-contract: success, actual DE440s downloaded *only to the disposable runner*; M4 CLI invoked using --query-json, then its resulting actual JSON passed to the M5a visual data validator: 1/1 passed with no skip.

Run from repository root:

    node --test tests/weather/test_magick_celestial_bridge_m5b.js
    python3 -m unittest discover -s tests/weather -p 'test_celestial_visual_cli_m5b.py' -v
    node --test tests/weather/test_magick_celestial_visual_m5.js
    node --test tests/weather/test_magick_subject_panels_g1.js
    node --test tests/weather/test_cosmos_visual_interactions_v2r.js

The GitHub workflow test verifies command and data-contract behavior, **not actual Quickshell runtime rendering, focus handling, data delivery after process exit, mouse scrolling or pointer hit-testing**. Those remain acceptance checkpoints before claiming this works in the operator's running station.

After adding this documentation, recheck final PR head, all checks and mergeability. Do not infer completion from a previous commit's CI result.

## WATCH OUT FOR

- No real charts appear until a local JPL kernel and Skyfield interpreter are available in the running Quickshell process environment. This branch does not download, install or configure those prerequisites.
- Quickshell.env reads variables from the Quickshell process environment. An already-running instance does not retroactively inherit variables from a separately opened terminal.
- Python runs as argv array, never as a shell command. The JSON query includes UTC date and body IDs only; no personal birth/location/sensitive records.
- The M4 event search is bounded and not exhaustive; grazing-contact candidates and retrograde station timing remain approximations with documented limitations.
- Zodiac wheel here uses geocentric apparent ecliptic longitude with tropical reference sectors, **not** true 3-D star positions, an astrological chart with houses, or a causal claim about human behavior.
- Calculated output provenance is source-identified, not independently cryptographically authenticated or verified against a separate Horizons engine.
- The MAGICK visual route replaces the earlier USNO observation panel on the charts route only, but the USNO integration under COSMOS remains unchanged. Other MAGICK routes retain their existing observational or reserved states.
- The existing M5a QML component is reused without modification; size/clipping of the nested view and actual mouse gesture behavior must be checked in a disposable Qt/Quickshell runtime before operator acceptance.
- Source-displaying QML may reveal a generic backend error rather than detailed stderr; investigate CI/local logs rather than silently falling back to guessed positions.
- Fedora and the live Quickshell process were not modified by this GitHub task. A merged PR by itself still does not install changes on the operator machine.

## CHECKLIST

- [x] Verified M5a merged; rechecked current main and concurrent Weather work
- [x] Single source owner in persistent SUBJECTS navigator
- [x] Opt-in explicit kernel and interpreter, manual-only calculation
- [x] M4 argv JSON transport, no shell or temporary request files
- [x] Both MAGICK layout paths connected to the same service
- [x] Status and CALCULATE action on supported astrology routes
- [x] No invented/unverified chart data
- [x] M5b contract tests, existing MAGICK/COSMOS regression, real-JPL data flow CI
- [ ] Recheck final PR-head CI after handoff commit
- [ ] Operator acceptance and authorized merge
- [ ] Local prerequisites approved and configured
- [ ] Actual Qt/Quickshell render + click/scroll/drag test in disposable session
- [ ] Operator acceptance of live Station appearance and behavior

## NEXT

First obtain PR acceptance and merge authorization. Then, under a distinct local-machine approval, configure a local Skyfield Python interpreter and official JPL ephemeris. Run a disposable Quickshell instance and verify complete visual delivery, route switching, source status, mouse zoom, drag-pan, clipping and no duplicate processes. Only then activate in the operator's regular Station.

Longer term: add operator-controlled historical time range and body selectors, richer source/precision inspector and full planetary/heliocentric orbital views. Never merge unrelated COSMOS/CLASSIC work into this change.

## DECISIONS

This implementation uses one explicitly triggered Process and no additional poller or cache writer. Backend and UI concerns remain separated, no personal MAGICK journal or divination inference is added, and no live Hospital registration or local system changes are claimed.
