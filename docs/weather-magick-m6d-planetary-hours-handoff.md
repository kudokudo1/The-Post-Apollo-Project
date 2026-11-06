# 🏥💜 Hospital // MAGICK M6d Chaldean Planetary-Hours Clock

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / bounded MAGICK feature expansion
ASSIGNMENT // M6d provider-sourced traditional planetary-hours clock
STAFF ROLE // Nurse 2 (external Hospital-compatible)
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE; no live Hospital registration verified
PHASE // Isolated GitHub draft, CI verification pending, native acceptance separate
BRANCH // feat/weather-magick-m6d-planetary-hours-clock-20261106
RECOVERY // M6c PR #1357 confirmed merged as 4004b31ca7437dc549129150898719bfe7d3d5ff at preflight; no open MAGICK/Weather PRs then

## IMPLEMENTATION

Re-read Syntagma AGENTS, applicable Hospital ownership/reporting protocols, current WeatherService forecast fields, WeatherCyclePolicy astronomy data, StationSky solar geometry, current MAGICK routes and existing tests. The operator requested continued MAGICK feature expansion, and M6d is a bounded traditional planetary-hour instrument, not a new weather collector or full ritual-planning engine.

- New pure \`widgets/weather/StationMagickPlanetaryHoursPolicy.js\` consumes only the existing \`WeatherService.dailyForecast\` (provider location-local solar times) and \`WeatherService.localObservationDateTime\`. It requires two valid, consecutive forecast civil dates with valid sunrise, sunset and next-day sunrise; it refuses invalid, missing or polar/no-rise windows rather than fabricating a solar day.
- Computes **12 equal wall-clock daylight segments** between source sunrise and sunset, then **12 equal wall-clock nighttime segments** between the same-date sunset and next-date sunrise. Night values crossing local midnight are labelled \`+1D\`. Displays forecast date and source-local event times.
- Implements explicitly named **Chaldean weekday/planetary-hour convention**: weekday first ruler Sunday Sun, Monday Moon, Tuesday Mars, Wednesday Mercury, Thursday Jupiter, Friday Venus, Saturday Saturn; then repeat Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon. Hour ruler is a cultural/traditional attribution, not astronomy, fate, auspiciousness or evidence of causal effects.
- The source API only supplies local \`HH:MM AM/PM\` events, NOT offset-aware UTC event instants. A night that crosses a DST change cannot be assumed to be equal elapsed SI hours. The UI and result contract explicitly say \`CIVIL CLOCK // DST TRANSITIONS NOT RESOLVED\`, and show clock-time references only. No PC timezone is substituted for a remote weather location.
- New \`StationMagickPlanetaryHoursPane.qml\` shows a **24-segment circular interactive dial** with bright day sectors, subdued night sectors, ruler-colored segments and selected index. Click or wheel the ring and use \`◀ HOUR\`/\`HOUR ▶\` to inspect rulers and source-local start/end labels. The observation-local timestamp is at most an initial *source snapshot* selection; no live/current-state claim. \`OPEN SOLAR SOURCE\` navigates to the existing \`cosmos/sun/twilight\` reference.
- \`StationMagickSubjectPane.qml\` now mounts the HOURS page at the existing deep route \`magick/planetary/hours\` without changing LENSES, ASTROLOGY, HELIO or global menu/navigation and without adding a Timer, Process, web access, location collector, saved records or background calculation.
- \`StationMagickSubjectPanelPolicy.js\` replaces the obsolete \`no division connected\` note with exact implemented scope and DST/tradition limitations, retaining the \`cosmos/sun/twilight\` source reference. Historical index route stays intact.

## HOW TO USE

After authorized GitHub merge and separately approved Fedora installation, Weather Station > MAGICK > INDEX > PLANETARY MAGICK > HOURS (or the existing HOURS link). Wait for the normal Weather forecast to load. The clock uses its selected location's **provider-local forecast date** and two consecutive valid solar-event days. It shows 12 daylight and 12 night sections. Click a segment, scroll on the ring or use the HOUR buttons to select a ruler/time slot. OPEN SOLAR SOURCE jumps to the existing observed SUN/TWILIGHT instrument. When data is missing, the instrument shows an unavailable status and does not invent sunrise, next sunrise or a night ruler window.

## VERIFY

New \`tests/weather/test_magick_planetary_hours_m6d.js\` checks weekday ruler order across all seven days, 24 exact traditional divisions, sunrise/sunset/next-rise continuity, midnight labels, source-local observation selection, date validity/leap days, unsupported solar conditions, 24-sector hit-test geometry, fail-closed source data, QML route/wheel/controls and no new side-effect/source actor.

The original \`test_magick_subject_panels_g1.js\` contract is updated only for the now-implemented HOURS note; existing historical route and source mapping remain. Added the M6d suite to existing COSMOS JPL/MAGICK workflow so previous M4–M6c and V4–V5 tests still run. Exact PR-head CI must be verified before claiming green; Qt native font/visual fit and real data behavior remain separate from source tests.

## WATCH OUT FOR

**Critical timing caveat:** local-source clock labels alone cannot resolve UTC offset changes during a DST transition. The M6d overnight segments are equal *local civil-clock intervals*, not guaranteed equal real elapsed durations around a DST jump. Do not describe those as precise astronomical minutes, fixed-length elapsed hours, or exact civil UTC timestamps. To remove this limitation in a later M6e-like timing refinement, request per-event offset-aware UTC sunrise/sunset event timestamps from an approved existing provider or establish a location-specific timezone source, with explicit user scope and verification.

High latitudes may have missing sunrise/sunset; M6d refuses those cases instead of assigning arbitrary 12/12. Forecast data can be cached or stale; no \`OPEN NOW\` claim. A traditional ruler is symbolic and convention dependent; no causal, medical or financial reading is inferred. This does not implement correspondence libraries, tarot, birth records or personal journals.

Do not merge without operator authorization, write to the Fedora desktop, restart Quickshell, assume production activation, or claim live Hospital Room ownership. If another MAGICK worker resumes, re-check GitHub HEAD and current Room owner.

## CHECKLIST

- [x] Verify M6c merged and no active MAGICK/Weather PR collision
- [x] Read Syntagma and current Weather forecast/solar source contracts
- [x] Implement pure 24-hour weekday sequence and fail-closed solar data
- [x] Mount circular source-backed HOURS screen and selection controls
- [x] Preserve existing source, menu and separate scientific/cultural claims
- [x] Add contract tests and workflow integration
- [ ] Exact-head GitHub CI and PR mergeability
- [ ] Authorized merge and separate local deployment
- [ ] Native provider-local solar clock and operator visual acceptance

## NEXT

Check all workflow results on PR head and repair evidenced failures. After authorized merge/deployment, inspect 24 sectors, next-day sunrise, ring click/pan, ruler sequence and provider-local data at the user's chosen station location. Next bounded feature M6e: sourced correspondences and explicit tradition/edition labels; any natal event chart, Tarot or personal journal must receive separate inputs, licensing/storage and permissions.

## DECISIONS

Keep Visual V5 accepted circular palette and defer cross-instrument Visual V3. No second solar data source or JPL process. Use an explicitly named Chaldean tradition and be scientifically clear that provider-local civil-clock night timing is DST-unverified. Stop at a useful read-only traditional clock rather than expanding into unsourced interpretations or persistent user data.
