# Hospital // Weather Station COSMOS V2b planetary event clock

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence
STAFF ROLE // NRS-2 (external Hospital-compatible; no live registration claimed)
PROVIDER // OPEN AI // CHATGPT
ASSIGNMENT // V2b source-true five-planet event clock and clickable source inspector
PHASE // GitHub review / desktop acceptance pending
STATE // IN REVIEW (not user DONE)
SCOPE // COSMOS planet-clock route, standalone QML/pure policy/tests only
ROADMAP // docs/weather-subjects-visual-intelligence-future-worker-roadmap-2026-11-03.md

## IMPLEMENTATION

- Reuses the existing single \`UsnoPlanetRiseSetService\` owned by \`StationSky.qml\`. No collector, storage writer, timer or network source added.
- \`StationCosmosPlanetEventPolicy.js\` maps one exact local civil date's USNO MRST rise, transit and set strings to bounded minute markers for Mercury, Venus, Mars, Jupiter and Saturn. Invalid date, mismatched provider date, malformed time, missing planet and special continuous-above/below-horizon statuses fail closed; they never become invented samples.
- \`StationCosmosPlanetEventClock.qml\` draws a readable five-lane 00–24 local-day chart with cyan rise, magenta transit and orange set markers; five real clickable planet selectors, an ALL selector, R/T/S/ALL event filters, marker hover, click-to-lock source inspector, and UNLOCK. The source/date and partial/error state remain visible.
- A narrow ~1-component mount in the existing \`StationSky.qml\` COSMOS \`planet-clock\` route displays the graph before the original five USNO cards. No CLASSIC, WEATHER, HOME, MAGICK, Stage Director, service policy, collector or persistent state changes. COSMOS overview remains unchanged because the current C1 overview does not request the planet-clock source.
- This is **a dated event clock**, not a calculated altitude-vs-time trace. A rise event, transit event and set event are three separate dots. The line between them is intentionally *not* interpolated. No zodiac longitude, aspect/retrograde event, continuous visibility or exact sky position is inferred.

## HOW TO USE

After successful CI, merge under operator authorization, and **separately** approve/install on Fedora:

Weather Station → SUBJECTS → COSMOS → PLANETS + SKY → PLANET CLOCK.

- Click **ALL** or a planet to show the five lanes or one lane.
- Click **R // RISE**, **T // TRANSIT**, **S // SET** or **ALL EVENTS** to filter the real event markers.
- Hover or click a letter marker to inspect the official local civil time. Click locks the reading; **UNLOCK** resumes pointer inspection.
- The original USNO text cards remain underneath and show details.
- If the provider is unavailable or a planet did not return dated normal events, the chart shows unavailable / special status instead of a synthetic arc.

## VERIFY

- \`tests/weather/test_cosmos_planet_event_clock_v2b.js\`: strict \`HH:MM\` parsing, 24-hour x scaling, date checks, all-five named planets, out-of-chronological-order same-day events, wrong-day rejection, partial/special event statuses, invalid angle handling, QML MouseArea/ActionButton callbacks, sole source ownership and COSMOS-only route guard.
- Dedicated \`.github/workflows/weather-cosmos-planet-events-v2b.yml\` runs the V2b suite and prior COSMOS V2, V2r, C1 and W1r regressions.
- GitHub PR-head CI, exact branch status, Qt/QML loading, real mouse hit-testing, scroll fit and local provider availability must be verified independently. Source-level text tests alone are not a native rendering test.

## WATCH OUT FOR

- USNO's MRST output has one-minute timestamp precision. Do not silently imply second-level precision.
- Rise / transit / set can appear in a surprising chronological order within one date; this is expected. Never connect dots into a guessed continuous daily track.
- Polar/special provider statuses are not transformed into fictitious markers. Partial provider data are explicitly retained.
- \`StationSky.qml\` is a shared entry seam with the CLASSIC migration worker. This patch is an isolated COSMOS-only component mount. Before merging, reacquire main/PR overlaps and reconcile with the other owner's current work. No local Quickshell update is authorized here.
- A separate MAGICK M5a/M5b lane has a JPL-powered ecliptic wheel and on-demand bridge; do not reuse a USNO event clock as fake orbital coordinates or start another ephemeris engine.
- Height is 414px in the existing StationSky Flickable. Check 160px left rail, actual desktop glyph sizes, click hit boxes, hover stealing and scroll on operator machine before final acceptance.

## CHECKLIST

- [x] Recheck Syntagma AGENTS/OPERATE, prior V1/V2/V2r PRs and newer MAGICK/CLASSIC ownership
- [x] Reuse exact USNO daily records without new data ownership
- [x] Pure policy, interactive lane component and narrow route mount
- [x] Event-date and click contracts plus dedicated CI
- [ ] PR-head CI all green
- [ ] Main/parallel ownership collision check before merge
- [ ] Operator-approved local install, native QML and mouse test
- [ ] Operator visual refinement and acceptance

## NEXT

Confirm the new PR-head CI, correct only evidenced defects, review any current \`StationSky.qml\` overlap, then merge if authorized. Reverify actual local clickable controls. For the next visual upgrade, coordinate MAGICK's JPL/M4 graph source rather than building a second planet engine; future wheel/aspect work must keep ecliptic longitude distinct from local rise/set events.

## DECISIONS

V2b deliberately uses independent event markers, not fabricated planetary tracks. The new piece is COSMOS-only and retains original USNO cards. HOME, CLASSIC transfer and MAGICK JPL instrument ownership are not transferred to this worker. No local machine mutation, production activation or live Hospital registration is claimed.
