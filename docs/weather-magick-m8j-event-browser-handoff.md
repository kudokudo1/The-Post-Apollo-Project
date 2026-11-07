# 🏥💜 MAGICK M8j // Source-Verified Event Browser, Paging and Inspector

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station > MAGICK > Astrology > MULTI > Event Browser
STAFF ROLE // DOC, external OPEN AI // CHATGPT; Hospital-compatible only (no live registration verified)
ASSIGNMENT // Improve the already accepted M8h browser for high event counts, retaining old click-to-WHEEL behavior
BASE // main c0a6712aa62b9b3b614f0442506255a7d34a54db
BRANCH // feat/weather-magick-m8j-event-browser-20261107
PERMISSIONS // Isolated GitHub implementation, tests and draft PR; no Fedora, SwayPX, local Quickshell, merge, production activation, or user acceptance

## IMPLEMENTATION

- M8i PR #1424 is still OPEN DRAFT. It modifies the numerical station finder. M8j deliberately DOES NOT touch `scripts/weather/celestial_transit_multi.py`, its Python tests, the JPL source, or the cross-process service. There is no numerical ownership collision.
- `StationMagickTransitEventBrowserPolicy.js` is a pure read-only projection of **already validated M8h JPL events**. Adds bounded 12-event paging, total/range/page counts, aspect-family and prograde/retrograde/direct/stationary filters, and a source-bound inspector of exact UTC, planet, aspect angular residual, or station estimated angular velocity.
- `StationMagickTransitMultiPane.qml` preserves all accepted WHEEL / TIMELINE / MULTI modes, 1–3 transit body selection, chart, source search and original row-click-to-WHEEL action. Existing ALL/ASPECT/STATION, body and chronological filters remain. New aspect and motion filters operate on the existing validated result, without additional Python work.
- A PREV/NEXT bar shows 12 records maximum and the total. Filter changes reset to page 1. Graph markers follow the same filtered event set. Importantly, an aspect filter in ALL mode **does not hide stations**, because a station has no aspect family.
- A separate INFO button on an event row opens a compact inline inspector **without navigating away**. A click on the rest of the row retains the accepted behavior of returning to WHEEL. Exact event timestamps remain seconds-resolution in the browser. The details label numerical **bracket ≤1s** for aspect crossings and **bracket ≤60s** for station estimates, without claiming observational uncertainty.
- No new backend, no data storage, no personal chart saved, no new network sources, no location inference or automatic monitoring. All controls are read-only projections of the same authenticated source payload.

## HOW TO USE

After independent review, explicit operator merge/deployment and native acceptance:
1. Weather Station → MAGICK → ASTROLOGY → NATAL → TRANSITS → MULTI; calculate natal and SEARCH the chosen UTC range/planet pairs.
2. Continue to use ALL / ASPECT / STATION, planet filter and OLD→NEW / NEW→OLD to narrow events.
3. Use **ASPECT** filter to cycle individual conjunction/sextile/square/trine/opposition types. Use **MOTION** to isolate retrograde/direct/prograde entries.
4. Use PREV/NEXT to inspect 12 results per page. The display shows current record range and total.
5. Press INFO beside an event to view the exact source UTC, chosen planet, residual or estimated station velocity. Press the event row (not INFO) to open the existing WHEEL at the nearest minute, preserving the exact source UTC as M8h already does.

## VERIFY

- `tests/weather/test_magick_event_browser_m8j.js`: deterministic 29-event fixtures verify 12/12/5 page boundaries, no source mutations, ascending/descending, combined aspect/motion/station/planet filters, empty results, safe invalid filters and zero-source state, station versus aspect details, and preservation of the old WHEEL event callback.
- `tests/weather/fixtures/M8jNativeEventBrowserShell.qml` and `scripts/weather/verify_magick_native_m8j.sh`: actual Quickshell/Qt offscreen execution inside disposable HOME/XDG roots. Feeds synthetic source-shaped model through the existing strict M8h response validator. Exercises 29-event pagination, filters, INFO without wheel navigation, chart event selection, and zoom/FIT.
- `.github/workflows/weather-magick-m8j-event-browser.yml`: new browser JavaScript test plus M8h/M8g/M8c regressions and a native QML job. Check exact PR-head CI before reporting a pass.
- A direct V8 smoke check of the new policy constructed 29 sample events with three pages, expected station subset and inspection, verifying no accidental source mutation. This is not a real DE440s test.
- Existing merged M8h and open M8i numerical test/process source are unchanged. Fedora operator native visual fit is not established by isolated CI.

## WATCH OUT FOR

- MORE FILTERING IS NOT MORE EPHEMERIS DATA: the result set remains capped by M8h's existing three-transit-body, 31-day, 150-event and 30/60-minute search contracts. Browser filters work only within the already computed, source-validated dataset.
- INFO's numerical time bracket is not physically measured event-time accuracy. Station velocities are derived from a centered finite difference and remain estimates. The M8i numeric reliability improvement stays a separate unmerged PR.
- Results are ephemeral and session-only. Paging and inspection never write birth records, profiles, journals, Calendar/TASKS or logs.
- Small native panels may require subsequent fit/interaction refinement; offscreen Quickshell is not proof of the user's running Fedora widget fitting correctly.
- This branch does not depend on M8i's merge to run because it modifies only the browser policy/pane/tests. Do not silently merge either branch or install the UI.

## CHECKLIST

- [x] Current Syntagma AGENTS, working guide, Hospital protocol checked
- [x] Reconstruct exact main HEAD and M8i open-draft ownership
- [x] Keep new M8j edits disjoint from M8i's numeric station source
- [x] Implement read-only pagination, filters and source inspection
- [x] Preserve old MULTI row-click-to-WHEEL path and all accepted modes
- [x] Add deterministic JS test, disposable native Quickshell fixture, CI workflow
- [ ] Verify exact PR-head CI and repair any failures
- [ ] Independent second reviewer
- [ ] Operator merge, Fedora visual review, user final acceptance

## NEXT

Check CI, repair only necessary M8j code or test issues and perform independent review. Once operator accepts this branch, future separately scoped work can add denser multi-natal-body comparisons after station CPU-performance verification; avoid modifying M8i's numeric work here.

## DECISIONS

No shared backend or user-data changes. Preserve current accepted source and QML navigation. Honor operator-only merge and live activation. Do not claim Hospital registration or Fedora acceptance. Avoid arbitrary new events, interpretations or other non-JPL astronomy claims.
