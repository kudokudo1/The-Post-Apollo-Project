# Weather StationW // MAGICK M5c Date and Planetary Pair Controls

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK visual controls
STAFF ROLE // External Hospital-compatible worker; live registration not verified
ASSIGNMENT // M5c user-controlled UTC navigation and body-pair selection
BASE // main at 3b261ac18b9a337fd301cc2ace6b3b4a985df2bf
BRANCH // feat/weather-magick-m5c-time-bodies-20261103
OWNER // Existing root-owned CelestialVisualService only. No new provider, scheduler, cache or storage owner
STATE // Draft implementation with CI pending; operator's first M5b live wheel render reported successful

## IMPLEMENTATION

The existing M5b visual service remains the one and only on-demand celestial calculation owner in WeatherStationW. M5c extends it with a pure bounded policy at services/weather/CelestialVisualQueryPolicy.js for:
- Explicit UTC navigation in 30-day increments and a TODAY reset.
- One selected UTC target date for the 14-, 29-, or 90-day historical/future series (using 12-hour samples and respecting M4's <=721 point limit).
- Six exact-body, two-target JPL pairs: Moon/Sun, Mercury/Sun, Venus/Mars system barycenter, Jupiter/Saturn system barycenters, Uranus/Neptune system barycenters, Moon/Pluto system barycenter.
- Source formats remain post-apollo.weather.celestial-visual-data.v1, geocentric apparent true-ecliptic-of-date.
- Maximum date offset +/-3650 days from the root-provided UTC day. This is a bounded interface window, NOT the JPL kernel's entire historical coverage.
- A no-guess query/result matcher requiring the requested pair, UTC start/end, sampling step, M4 coordinate frame, provenance hash and event selection.
- Each change invalidates old results and cancels any in-flight computation through the existing onCurrentKeyChanged lifecycle; no automatic recalculation occurs.

Changes:
- New services/weather/CelestialVisualQueryPolicy.js.
- Updated services/weather/CelestialVisualService.qml with new pairPreset, dateOffsetDays and spanDays state, protected query creation and mismatch refusal.
- Updated widgets/weather/StationMagickSubjectPane.qml with two compact controls: previous/today/next UTC navigation and previous pair/next pair/span cycle. Existing CALCULATE remains the only trigger.
- New tests/weather/test_magick_celestial_query_m5c.js tests pure UTC arithmetic (DST/leap-year boundaries), exact NAIF naming, valid body/date pairs, no stale replay and actual QML handler wiring.
- New tests/weather/test_magick_celestial_query_m5c_jpl.js tests source-stamped M4 JSON for selected pairs.
- New .github/workflows/weather-magick-time-bodies-m5c.yml rechecks prior M5a/M5b/Weather/COSMOS/HOME contracts and real JPL DE440s runs.

No change to M0–M4 planetary calculations, Station's global weather location, COSMOS/CLASSIC migrations, SETTINGS++, Stage Director, terminal system, personal journaling or symbolic interpretation.

## HOW TO USE

After approved integration to the operator's live machine and restart through the existing launcher:

SUBJECTS > MAGICK > ASTROLOGY > CHARTS (or zodiac/aspects/retrogrades)

- UTC date row: ◀ 30D / current UTC target day / TODAY / 30D ▶.
- Body row: ◀ PAIR / pair label / PAIR ▶ / SPAN 14D/29D/90D. Each SPAN click cycles.
- Click CALCULATE after choosing options. Source-only charts appear only on successful JPL output.
- Opening retrogrades defaults to Mercury/Sun; other astrology routes default to Moon/Sun.
- The graph's existing sample stepping, click-to-lock, drag-pan and scroll-to-zoom remain.

No automatic downloads or installer are included. The required existing POST_APOLLO_CELESTIAL_KERNEL and optional POST_APOLLO_CELESTIAL_PYTHON environment variables retain their M5b behavior. The eventual production Backend Manager should make this setup automatic for end users, but is not implemented by this change.

## VERIFY

Commands from repository root:

    node --test tests/weather/test_magick_celestial_query_m5c.js
    node --test tests/weather/test_magick_celestial_bridge_m5b.js
    node --test tests/weather/test_magick_celestial_visual_m5.js
    node --test tests/weather/test_home_deck_w2a.js

The dedicated GitHub workflow obtains official DE440s only within a disposable runner and tests both Venus/Mars and Jupiter/Saturn barycenter pairs over a 90-day window, passing the produced M4 JSON through M5's source validation.

Numerical source tests are not evidence that the new buttons fit, are clickable, or scroll safely in the actual Quickshell widget. The operator's previous screenshot verified first M5b wheel drawing, not these new M5c controls.

## WATCH OUT FOR

- **Barycenter identity:** Mars, Jupiter, Saturn, Uranus, Neptune, Pluto *system* barycenters are not silently labeled as exact planetary mass centers. The displayed pair labels include SYS.
- Every pair has exactly two bodies to preserve M4 event search and chart-contract bounds. Six presets are a first UI; arbitrary body selection requires a separate future interface.
- All selections are UTC. Local clock time, IANA timezone, birth charts, sidereal zodiac, houses and local topocentric sky require separate explicit contracts.
- Date changes clear old source data and require another CALCULATE click. This prevents false charts but may feel manual until future scheduling is approved.
- M4 aspect event searches have incomplete sampling guarantees; M3 grazing events remain candidates under stated angular tolerance.
- This is a GitHub-only source change. The operator's live Fedora, Quickshell environment and JPL files are not modified.
- One shared root owner still serves both WORKSPACE and INDEX MAGICK panes. Do not clone new Process children into either view.
- The new rows make the panel taller. Native click/scroll/focus and clipping verification are pending in the actual Station.

## CHECKLIST

- [x] Current main and active PRs checked; unrelated Weather provider-health work remains separately owned
- [x] Single-service M5c UTC/pair/span logic
- [x] Clickable controls with explicit data invalidation and CALCULATE gating
- [x] No speculative positions or silent center/barycenter substitution
- [x] Isolated policy tests plus end-to-end real JPL workflow
- [ ] GitHub CI confirmed against final PR head
- [ ] Operator acceptance and authorized merge
- [ ] Local M5c runtime geometry/input test
- [ ] Final acceptance
- [ ] Production backend auto-provisioning, separate future scope

## NEXT

First verify and review M5c; merge only under operator authority. Then check the two new control rows in a disposable or operator-approved live session, including side-by-side WORKSPACE/INDEX, disabled/unavailable paths, source correctness after changing dates, Moon/Sun and barycenter presets, zoom/pan, and whether scroll reaches all controls.

Follow-on M5d can improve zodiac-wheel scale, graph labels, source details, planetary relationships and historical selectors. Add automatic end-user Skyfield/kernel provisioning through a separate Settings++/backend-manager assignment rather than burying installation inside the visual component.

## DECISIONS

Backend-first validated M0–M4 remain authoritative. The operator reported M5b wheel visibly working. No local install, process restart, forced PR merge, live Hospital registration, symbolic causation model or personal-data journal was added here.
