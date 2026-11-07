# 🏥💜 MAGICK M8f // Source-Sampled Transit Timeline and Refined Aspect Crossings

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station MAGICK > Natal/Transit Analytic Engine
ASSIGNMENT // Bounded source-driven continuous sampled transit timeline and precise angular crossing search
STAFF // External DOC, OPEN AI CHATGPT; Hospital-compatible, not live-registered
BASE // main a43421f605d7aa187a092461585ba7dd0169002d (M8d merged)
BRANCH // feat/weather-magick-m8f-source-transit-events-20261107
SCOPE // Additive Python source engine + isolated unit/CI tests. No UI integration, desktop edits or storage.
PERMISSIONS // GitHub-only source/tests/docs + draft PR; operator controls merges/native activation and acceptance.

## IMPLEMENTATION

- `scripts/weather/celestial_transit_timeline.py` reuses M8b `celestial_solver.py` Skyfield/JPL targets to recompute one natal body longitude and sample one selected transit body over an explicit 1-minute-aligned UTC interval of at most **31 days**.
- Exact ephemeris identity is checked against the previously validated M8b natal chart's SHA-256. If the installed kernel differs from the natal source, the request fails instead of silently comparing different ephemerides.
- The observer is supplied explicitly with latitude and longitude, elevation fixed to 0 m; no GPS inference, Home default, weather provider or implied event timestamp. Both positions use topocentric apparent true-ecliptic-of-date longitude.
- Search samples at user-selected **30 or 60 minutes** to generate a bounded source trajectory. Display/output samples are thinned to ~6-hour intervals, preserving the endpoints. This is a sampled trajectory, not a continuously evaluated numeric plot.
- A phase-unwrapping step safely handles 359°→0° and retrograde movement. Crossing branches are searched for conjunction 0°, sextile ±60°, square ±90°, trine ±120°, opposition 180°; sign-bracketed events are refined by numerically bisecting the JPL longitude function to a **1-second time bracket**. Returned events include UTC timestamp, source angle residual, aspect name and prograde/retrograde direction.
- Input arrives as one bounded JSON line on standard input; the process does not save natal records or invoke downloads. Computed output is JSON to stdout with SHA/source, observer and explicit limitations. A CLI invocation always requires `--kernel` pointing to a known local BSP.
- There is no Quickshell user-facing timeline UI, caching, implicit periodic polling, journaling, calendar task, or event notification in this PR.

## HOW TO USE

After authorized merge and environment configuration, a separate short-lived caller supplies one JSON line to:
`python3 -B scripts/weather/celestial_transit_timeline.py --kernel /path/to/de440s.bsp`

Required request:
```json
{
  "format": "post-apollo.weather.magick-transit-timeline.m8f.v1",
  "natal_epoch_utc": "2000-03-21T15:20:00Z",
  "start_utc": "2026-11-07T00:00:00Z",
  "end_utc": "2026-11-14T00:00:00Z",
  "latitude_deg": 38.9,
  "longitude_deg": -76.8,
  "expected_ephemeris_sha256": "<SHA-256 of actual installed natal BSP>",
  "natal_body": "venus",
  "transit_body": "moon",
  "sample_minutes": 60,
  "aspects_deg": [0, 60, 90, 120, 180]
}
```
**Important:** these values are schema examples, not anybody's actual birth data or predicted events. A real source request must use the event's genuine UTC/location, actual kernel hash and chosen bodies.

## VERIFY

- `tests/weather/test_magick_transit_timeline_m8f.py` uses synthetic analytical trajectories to check minute-accurate known crossing times, retrograde crossings, wraparound, two directed aspect branches, opposition, multiple repeated crossing deduplication, stationary/no-crossing cases, 31-day and body/UTC limits, no unknown NAIF names, SHA matching, and no recording/network code.
- `.github/workflows/weather-magick-m8f-transit-search.yml` runs those tests plus the existing M8b natal geometry tests on the exact PR head.
- Synthetic test functions DO NOT validate a real de440s JPL numerical result. Full verification requires the permitted, installed Skyfield/JPL BSP in an authorized disposable environment, independent comparison, and native desktop UI acceptance.
- M8e PR #1411 separately established an actual offscreen Quickshell QML date/location/transit native test **PASS**, but that is not the operator's local Fedora desktop. M8f does not alter or bypass that gate.

## WATCH OUT FOR

- This is an exact numerical refinement of **sign-changing aspect crossings**, not an exhaustive search for tangential/grazing contacts when a body touches an angle and turns around between samples.
- Search is bounded to at most 31 days and one transit vs one natal body, with sample step 30/60 minutes; extreme motion/large jumps fail closed.
- Refined root timing to a 1-second numerical bracket does **not** imply observational or physical accuracy of 1 second. Ephemeris/coordinate accuracy and birth-event timing still limit the result.
- Astrology aspect families are *conventional angle labels* attached to measured astronomical longitudes. There are no causal claims or predictive interpretations.
- Transit and natal longitude use the **true ecliptic of their respective dates**, which is not the same as relative motion in an inertial 3D frame. Input elevation fixed to zero.
- A signed crossing can be repeated by retrograde movement; all distinct crossings remain in the result. Source result is ephemeral, no background jobs, notifications, user data files, personal journal, or external network.
- No UI, local Fedora, running Quickshell, production activation or merge is changed. UI wiring must wait for independent/native operator acceptance and clear permissions.

## CHECKLIST

- [x] M8b/M8c/M8d merged into GitHub main; check collisions with M8e verification PR
- [x] Add separate bounded exact-JPL-source search engine
- [x] Source SHA and observer consistency
- [x] Continuous sampled trajectory and 0/60/90/120/180 crossing searches
- [x] Bisection with 1-second UTC bracket and residual reporting
- [x] Strict privacy, UTC, bounds and source tests
- [x] Dedicated CI workflow
- [ ] Exact final PR-head CI and independent review
- [ ] Real BSP comparison under isolated testing
- [ ] Native Fedora layout/zoom/transit acceptance
- [ ] Operator merge/activation decision
- [ ] Future MAGICK timeline UI and richer multi-body event search

## NEXT

Review CI; fix any failing numerical test or source logic. Keep the PR as a draft source-only milestone until the M8e native review and Fedora acceptance gates. Once permitted, integrate an explicit selected-body timeline and event table into existing MAGICK > Astrology > TRANSITS, using new source service with stdout size/cancellation bounds, no hidden storage.

## DECISIONS

No invented transit event time. Keep the M8c single-instant snapshot as-is. Use JPL source values, not decorative clock drawings. Search precision is a numeric bracket, not a spiritual forecast or claim of exhaustive event discovery. Operator remains final authority for merge, deployment and acceptance.
