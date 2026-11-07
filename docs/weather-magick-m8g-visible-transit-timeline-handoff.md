# 🏥💜 MAGICK M8g // Visible Transit Timeline and Refined Aspect Event Selection

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station MAGICK > Astrology > Transits > Timeline
STAFF // DOC, OPEN AI / CHATGPT (external Hospital-compatible; no live registration claimed)
ASSIGNMENT // Show JPL-sourced M8f timeline and exact-crossing events inside existing MAGICK transit instrument, preserve natal and two-body modes
BASE // main 8ba6f300d1c8cfdeb673d531e3e09c5986edea09 (M8e native verification and M8f numerical source already merged)
BRANCH // feat/weather-magick-m8g-transit-timeline-ui-20261107
PERMISSIONS // Bounded GitHub code/tests/docs + draft PR, no local Fedora changes, merges, restart or production activation

## IMPLEMENTATION

- `StationMagickAstrologyPane.qml` now hosts two views inside existing **TRANSITS**: WHEEL retains the M8c two-epoch natal/transit circular chart, and TIMELINE is an independent graph/list panel. Original pair-JPL, natal setup, date steppers and private processes are unchanged.
- `CelestialTransitTimelineService.qml` reuses the M8f `scripts/weather/celestial_transit_timeline.py` source-only backend and the existing installed Skyfield/Python/JPL-path policy. One user SEARCH action produces a short-lived bounded JSON stdin request with no personal data in argv, browser, saved files, logs or network. Cancels source process and clears in-memory data when the owner leaves TRANSITS or the natal chart changes.
- `StationMagickTransitTimelinePolicy.js` constructs a strict 1/7/14/31-day source request, explicitly UTC midnight start, 30 or 60-minute search steps, one natal target and one transit target, standard five angular aspects, original observer and kernel SHA-256. Exact NAIF identities are checked. The returned model is admitted only when source hash, observer, times, bodies, sample counts, longitudes, and contact names/refinement metadata agree. Invalid/incomplete payloads remain unavailable.
- `StationMagickTransitTimelinePane.qml` provides BODY selectors, existing TASKS-style UTC date steppers/TODAY, selectable span and cadence, SEARCH, a zoom/pan/FIT sampled angular curve, and a scrollable list of refined UTC event times and prograde/retrograde direction. The event list is computed from real M8f output, not decorative phase artwork.
- Selecting a refined contact returns to WHEEL by invoking the existing private natal/transit chart calculator at the **nearest whole UTC minute**. The source event's exact seconds remain in the chart readout and are **not** presented as though the chart's minute-rounded position is exact.
- No new static images, automatic background searches, notifications, calendar writes, saved birth records, location inference, new ephemeris/download or source-provider ownership changes.

## HOW TO USE

After operator-approved merge and native deployment: open Weather Station > MAGICK > ASTROLOGY > NATAL, enter real UTC birth/event date/time and correct birthplace coordinates, press CALCULATE NATAL, then TRANSITS > TIMELINE. Select one natal target and one transiting target, choose a UTC start date with month/day/year spinners, choose 1/7/14/31 days and 30/60 min cadence, then SEARCH. Scroll/zoom the curve; click an event row or event marker to return to WHEEL. Event's exact UTC and the nearest-minute wheel distinction remain visible. WHEEL/TIMELINE switches do not alter the natal chart.

## VERIFY

- `tests/weather/test_magick_transit_timeline_ui_m8g.js`: synthetic exact-source request/response fixtures, source matching, date limits, NAIF, observer, kernel hash, 31-day durations, sample-count and relative-longitude consistency, invalid contact rejection, UTC second-to-minute conversion, privacy, control wiring and preservation of older modes.
- `tests/weather/fixtures/M8gNativeTransitShell.qml` and `scripts/weather/verify_magick_native_m8g.sh`: real Quickshell offscreen and disposable XDG roots. Actual QML instantiation, valid synthetic JPL-shaped response through the service's response validator, plot, zoom/FIT and exact-contact selection/nearest-minute signal. The Python process is **not** launched, because there is no private operator BSP in CI.
- Dedicated `.github/workflows/weather-magick-m8g-transit-ui.yml`: JS test plus M8c/M8b/M8d regressions and separate native QML job. Check final PR-head status.
- Real operator Fedora/Quickshell panel visual acceptance and independent physical DE440s numerical comparison are **not** established by CI. Treat the separate M8e native PR (merged) as an isolated test, not user acceptance.

## WATCH OUT FOR

- Search works only when a full M8b natal chart and source-matched locally configured BSP exist. Missing kernel or input shows unavailable rather than fake trajectory.
- The M8f backend searches **sign-changing crossings** using 30/60-minute samples, then refines a crossing time to a one-second *numerical bracket*. Tangential/stationary grazing contacts are not guaranteed; one-second numerical precision is not astronomical accuracy.
- Timeline graph is a **sampled source-backed ecliptic longitude** curve, not a literal continuously solved physical trajectory or scientific claim of astrology's causal effects.
- Each search covers one natal target vs one transit target, up to 31 days. A high-level future multi-body/all-aspects planner is not implemented.
- Explicit UTC is used, with the natal chart's original observer location, and true ecliptic/equinox of the respective date. No HOME/IP/GPS inference in the timeline search.
- Source response and event list remain session-only. Under the current M8b minute-only chart contract, selecting an exact-second event triggers a **nearest-minute** chart, not the exact event instant. UI names both. A future second-precision chart engine is a separate numerical/contract assignment.
- No local machine writes, migrations, merges, or user acceptance. Don't deploy while other Weather Station workers own live runtime state.

## CHECKLIST

- [x] Re-read Syntagma AGENTS and Hospital compatibility rules; verify main, merged M8e/M8f, and no competing MAGICK PR
- [x] Reuse existing M8b/8c/8f source/process/date UI
- [x] Strict same-kernel natal-bound timeline request and validated output
- [x] Interactive source curve and exact aspect event list
- [x] Event handoff to original wheel at nearest UTC minute with precise source readout
- [x] Contract tests, native QML fixture and dedicated CI workflow
- [ ] Final PR-head GitHub checks and independent second review
- [ ] Native real BSP data comparison on authorized isolated runtime
- [ ] Operator merge, Fedora UI geometry, zoom, input, performance and final acceptance

## NEXT

Review exact CI and fix any regressions in this branch, preserve draft until operator merge decision. After native acceptance, consider explicit transit-site override, shorter event windows or a source-verified seconds-level chart engine as separate assignments. Do not add unrelated COSMOS/calendar/profile storage.

## DECISIONS

SOURCE FIRST // event timestamps always come from numeric JPL crossing search, never illustrations.
PRIVACY // no stored birth data, stdout bounded and stdin-only requests.
INTEGRATION // existing WHEEL and PAIR remain operational; TIMELINE is a mode.
AUTHORITY // operator controls merges, live deployment, and final acceptance.
