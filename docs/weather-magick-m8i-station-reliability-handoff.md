# 🏥💜 MAGICK M8i // Station-Reversal Reliability

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station > MAGICK > Astrology > MULTI > Station Numeric Reliability
STAFF ROLE // External Hospital-compatible DOC (OPEN AI // CHATGPT), not live-registered
ASSIGNMENT // Improve M8h's existing station search without reopening the accepted user interface
BASE // main c0a6712aa62b9b3b614f0442506255a7d34a54db at branch creation
BRANCH // fix/weather-magick-m8i-station-reversal-detection-20261107
SCOPE // One existing MAGICK Python source, isolated numeric tests, one CI workflow and this handoff
PERMISSIONS // Bounded GitHub implementation, CI, draft PR. No local Fedora/Quickshell writes, live upgrades, merge or production activation.

## IMPLEMENTATION

The accepted M8h station finder evaluated its centered apparent longitude rate at the user-selected 30- or 60-minute sample boundaries. If a planet reversed retrograde then direct (or the reverse) between them, both endpoints could show the same sign and the pair would disappear.

Updated `celestial_transit_multi.py`'s existing `find_stations()` rather than changing the UI or creating another service:
- Independently calculate 20-minute centered apparent longitude velocity on a bounded time grid spaced **no more than 15 minutes**, regardless of the 30/60-minute trajectory sample selection.
- Detect a rate sign reversal in each interval, then bisect the JPL-supplied velocity function until the numerical time bracket is at most 60 seconds.
- Handle stationary values exactly at grid nodes, which need verification against both neighboring samples.
- Recheck the rate five minutes before and after a refined candidate to reduce false station claims; deduplicate nearby repeated detections.
- Enforce at most 3000 station-rate grid samples. The existing 31-day source request and at most three moving bodies remain bounded.
- Keep the same M8h event JSON fields, `type: station`, `direction: direct|retrograde`, measured longitude, numerical UTC timestamp, rate and `uncertainty_seconds: 60`. A new informational `limitations.station_rate_scan_interval_minutes_max: 15` field describes the improved detection grid.
- Preserve the 20-minute centered-velocity method, JPL kernel hash, observer, exact NAIF targets, privacy, on-demand operation, 1/7/14/31-day ranges and five original aspect families.

## HOW TO USE

There is no new control. After operator-approved merge and deployment, use the already accepted:
Weather Station → MAGICK → ASTROLOGY → NATAL → TRANSITS → MULTI.
Select a natal body, one to three moving bodies, UTC date range and aspect filters, then SEARCH. The existing browser shows stationary/direction-change events. A 30/60-minute timeline cadence no longer by itself excludes a double reversal separated enough to be visible on the new 15-minute station grid.

## VERIFY

- New `tests/weather/test_magick_station_reliability_m8i.py` verifies two reversals hidden from the old 60-minute endpoint scan, two within a 30-minute interval, station exactly at a grid node, retrograde and direct labels, constant/linear no-false-event cases, 359°→0° wrap, rate-sample limits, output compatibility and private source constraints.
- Dedicated `.github/workflows/weather-magick-m8i-station-reliability.yml` runs the new tests alongside unchanged M8h, M8f and M8b Python regressions.
- Existing accepted UI and M8h JavaScript contract are intentionally unchanged. The additional limitations field does not change existing required result keys.
- Check exact PR-head GitHub workflow results before claiming the test gate passed.
- Native Fedora/SwayPX and real kernel source comparisons remain separate gates; synthetic polynomials prove numerical corner cases but not live astronomical accuracy.

## WATCH OUT FOR

- This reduces, but **does not eliminate**, missed reversals. Two events inside one 15-minute station-scan interval can still be missed. The 20-minute centered finite difference also smooths very short movements.
- A 60-second *numerical bracket* is not an observational 60-second accuracy claim. Topocentric apparent longitude may differ from other chart definitions, and event dates depend on the input observer and precise kernel.
- This change evaluates more rate samples (at most 3000 points per moving body) and therefore may increase computation time in the longest 31-day/three-body search. Retain source cancellation and no automatic polling.
- No natal records, event data, profile, TASKS, Settings++, local desktop files or source caches are written.
- M8h is already live and operator accepted. Keep it untouched on the desktop until explicit separate deployment authorization. This new M8i branch is an additive accuracy correction.

## CHECKLIST

- [x] Read current Syntagma AGENTS / Hospital protocols
- [x] Verify current main and no competing open MAGICK/transit PRs
- [x] Preserve existing M8h user-visible interface and source contract
- [x] Implement bounded 15-minute station-rate subsampling
- [x] Add exact-node handling and independent direction verification
- [x] Add double-reversal/numerical regression tests and CI
- [ ] Exact PR-head CI success
- [ ] Independent second technical review
- [ ] Real DE440s source/CPU-performance verification
- [ ] Operator merge/deployment authorization and acceptance

## NEXT

Inspect exact GitHub CI; correct source/test problems if necessary. Keep M8i draft and isolated until the operator approves an appropriate merge/deployment gate. After scientific and performance verification, consider future user-visible velocity curves and more powerful stationary-contact analysis as a separate assignment.

## DECISIONS

No UI redesign or silent scope expansion. Keep the accepted WHEEL/TIMELINE/MULTI controls and existing M8h private protocol. Only advance numerically source-backed astronomy. No live Hospital registration, workstation writes, or implied final operator acceptance.
