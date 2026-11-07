# 🏥💜 MAGICK M8c // Dual-Epoch Natal + Transit Comparison

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station MAGICK / ASTROLOGY / Natal & Transit Comparison
ASSIGNMENT // Compare source-verified natal placements with manually chosen JPL transit UTC
STAFF // DOC, external OPEN AI // CHATGPT, Hospital-compatible but not live-registered
SCOPE // MAGICK chart comparison policy, QML wheel, bounded Astrology connection, tests, CI and handoff
BASE // main at 65ab38a0b3685c48ad77ad9940cae26efcf4ff21
PERMISSIONS // Bounded GitHub-only code, tests and draft PR. No desktop change, merge or production activation.

## IMPLEMENTATION

- M8b PR #1408 was merged into `main` before branching. There were no open MAGICK or transit PRs matching this work at preflight.
- The new `StationMagickTransitComparisonPolicy.js` accepts TWO complete M8b natal-chart payloads: the original natal UTC epoch and a separate explicit transit UTC epoch. It fails closed if their JPL/Skyfield engine, kernel SHA-256, exact NAIF target identities, topocentric observer coordinates, zodiac, house method or true ecliptic-of-date / apparent frames differ. It rejects an uncomputed/stale time, missing bodies, unsupported sidereal data, invalid UTC or invented positions.
- It calculates shortest signed same-body longitude shifts and cross-chart interpretive aspect tolerances (conjunction 0°, sextile 60°, square 90°, trine 120°, opposition 180°). The manually adjustable aspect orb is 1°–6°, and the results are ranked by closeness. This does NOT calculate the instant of exact contact, planetary causal effects, or a full transit chronology.
- **Reuse before invention:** a second isolated `CelestialNatalChartService` instance computes the transit chart at the chosen UTC instant. It reuses the existing M8b `celestial_natal_chart.py` and exact JPL targets; no second backend/provider, new data cache, web request, personal storage or invented location.
- The transit result uses the natal chart's **same observer coordinates**, which is explicitly labeled: topocentric transits at the natal location, not the user's current location. Both charts use tropical true ecliptic/equinox **of their respective dates**, not a precessed J2000 frame or sidereal model.
- Added `StationMagickTransitChartPane.qml`: a zoomable/pannable dual ring of natal placements (yellow inner) and transit placements (cyan outer). Selecting a transit target highlights only that target's aspects to natal targets to avoid a 100-line graph. Shows source epochs, observed longitude shifts, angular orbs, and the interpretation/precision limitation. User must enter explicit UTC date and time and click TRANSIT UTC to calculate. A manual orb control cycles 1°–6°.
- Updated `StationMagickAstrologyPane.qml` to let NATAL toggle to TRANSITS after a real natal chart is ready; NATAL returns to the natal wheel, PAIR remains the earlier M4 two-body instrument. A changed natal source clears the transit result and in-flight process. Closing/hiding transit mode also clears the transient calculation and transit input.
- No birth details are passed in process arguments; both existing M8b services send bounded JSON privately to Python stdin. No birth records, logs, database writes, automatic polling or new local installation.

## HOW TO USE

After operator-authorized merge/deployment:
1. Weather Station > MAGICK > ASTROLOGY > NATAL. Enter a tropical natal event and press CALCULATE NATAL using the existing M8b event form.
2. When the natal chart is ready, select TRANSITS. Enter the desired UTC date as YYYY-MM-DD and UTC time as HH:MM. The explicit observer is taken from the natal site's verified coordinates.
3. Press TRANSIT UTC. If the same local JPL kernel computes a complete second chart, the cyan outer ring appears around fixed yellow natal positions. Click a cyan body to inspect its longitudes, shortest signed movement and any cross-chart aspects within the selected orb.
4. Scroll or use +/− for zoom, drag to pan, double-click or FIT to restore the whole wheel. ORB cycles 1..6°, affecting only interpretive angular filtering; it does not recalculate planetary positions.
5. Select NATAL to return to the original natal wheel, or PAIR to leave the natal family for the original two-body JPL visualization.

## VERIFY

- `tests/weather/test_magick_transit_comparison_m8c.js`: synthetic deterministic fixtures verify exact UTC validation, source identity, observer consistency, leap-day/date rejection, NAIF labels, frames, ten bodies, angular wraparound, signed deltas, 0/60/90/120/180 aspect relations, orb bounds and explicit UI controls. Fixture angles are **test data**, not actual transit predictions.
- `.github/workflows/weather-magick-m8c-transits.yml` runs the new test and M8b, M8a, M7a and G1 regressions.
- Must verify exact PR-head GitHub CI and mergeability; then separately validate full natal/transit positions using an installed DE440s BSP, test the Quickshell input focus/zoom/hit testing/compact layout, and obtain operator acceptance.
- No claim of live BSP numerical output or native GUI pass is made from synthetic CI.

## WATCH OUT FOR

- This is **two-epoch comparison**, not a computed date/time of exact aspect, continuous transit tracking, forecast, electional recommendation or personal interpretation. It explicitly separates measured planetary angles from conventional astrological labels.
- Transit sites use natal location for numerical comparability. Real transits at the current location would require a separate explicit place selection and source agreement.
- True ecliptic/equinox of date changes with epoch. The wheel compares source-reported tropical longitude coordinates at two times; it is not inertial 3D displacement.
- Full natal service accepts only tropical zodiac and Whole Sign / Equal houses. Sidereal, other house systems, changing local timezone, transit calendar reminders, saving birth charts and personalized forecasts are not part of M8c.
- M8b source scope was preserved. GitHub workflow tests check code contracts, not native pixel fit.
- No local desktop modifications, merge or production activation. Operator has final authority.

## CHECKLIST

- [x] Current Syntagma/Hospital preflight and main merge check
- [x] Isolated M8c branch, no open MAGICK/transit PR collision
- [x] Reused M8b JPL engine for both explicit epochs
- [x] Strict same-source and same-observer validation
- [x] Cross-chart aspect and signed angular difference model
- [x] Dual wheel with manual UTC input, orb filter, zoom/pan and target selection
- [x] Added CI and regression tests
- [ ] PR-head checks and independent technical review
- [ ] Operator merge and authorized native deployment
- [ ] Native BSP cross-check and desktop acceptance

## NEXT

Verify CI and repair any regressions, then request independent review and operator merge decision. After native acceptance, a separate milestone can add explicit transit location, multi-day samples, exact aspect-contact searches, and more advanced chart presentation. Do not expand M8c into unrelated Calendar, COSMOS or profile storage work.

## DECISIONS

All geometry comes from explicit JPL source results. The existing private M8b service is reused rather than cloned. Inputs stay session-only. M8c remains a bounded read-only comparison with no claims of spiritual causation or astronomical prediction beyond measured positions.
