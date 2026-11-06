# 🏥💜 MAGICK M7a // Five-Track Functional Foundations

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station MAGICK Five-Track Development
ASSIGNMENT // First bounded implementation of lunar/solar calendar, planetary timing, event-chart setup, symbolism and temporary journal
DOCTOR // Nurse 2 (external Hospital-compatible)
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE (no live registration verified)
PHASE // GitHub draft and source regression verification; operator acceptance distinct
BRANCH // feat/weather-magick-m7a-five-track-foundations-20261106
RECOVERY // Earlier M6j Tarot art/close PR #1382 confirmed merged; no open MAGICK or Weather PRs returned at preflight. Current main remains source truth.

## IMPLEMENTATION

User explicitly authorized starting the five feature families. Consulted current Syntagma AGENTS and Hospital Agent, Authority and Reporting protocols; inspected real MAGICK SubjectPanelPolicy, SubjectPane, M30 Moon/Solar layout, M6d planetary-hours source, WeatherService dailyForecast and current astrology, Agrippa and grimoire components. All changes target only Weather Station MAGICK, with a single isolated branch and no cross-repository writes. This is a broad assignment, but the five slices remain separately testable and do not change shared WeatherService or CelestialVisualService ownership.

**Track 1 // Lunar & Solar Calendar**: Replaces the literal `PRACTICE CALENDAR // NOT CONNECTED` placeholder with a compact selectable weather-forecast date grid and two source-derived bar series: provider daily moon illumination and sunrise-to-sunset fraction. The pure `StationMagickForecastCalendarPolicy.js` validates consecutive provider-local dates (max 14), moon-phase labels, illumination 0-100 and parseable sunrise/sunset. Missing values stay missing. This is **not** a full lunation ephemeris, event-UTC predictor, equinox/solstice calculation, ritual event list or personal calendar store. Uses existing WeatherService dailyForecast only. The original MOON and SOLAR + SEASONS SKY instruments remain mounted at the same tabs.

**Track 2 // Planetary Timing**: The previously informational `magick/planetary/timing` route now gets its own source-backed `StationMagickTimingAtlasPane.qml`, date buttons and a 24-segment day/night chart. It calls the existing M6d `StationMagickPlanetaryHoursPolicy.js` for every original sunrise/sunset/next sunrise hour boundary and named Chaldean weekday ruler. New `StationMagickTimingAtlasPolicy.js` only checks available consecutive forecast dates and sums real source ruler counts; it never creates separate solar calculations or favorable/causal electional predictions. **DST offset uncertainty** remains explicit because the provider gives localized clock labels, not per-event offset-aware UTC instants.

**Track 3 // Astrology Event Setup**: Adds `EVENT SETUP` to existing standalone ASTROLOGY header and a temporary `StationMagickEventChartSetupPane.qml` overlay. Date and clock use explicit UTC; coordinates are typed by the operator (no location service), and tropical/sidereal and whole-sign/equal house-model choices are selected only as *draft metadata*. Pure `StationMagickEventChartSetupPolicy.js` validates Gregorian dates, clock and coordinates. It does **not** calculate a natal event chart, ascendant, houses, multi-body ephemeris, sidereal conversion or aspects; existing JPL pair calculation is preserved. Data is not sent to a service, saved or synced. This avoids falsely treating a source pair as a complete ten-body birth chart.

**Track 4 // Symbolism**: Activates `magick/divination/symbolism` with a read-only search/filter/planet map and chapter references. `StationMagickSymbolismPolicy.js` reads the already-source-labelled M6e Agrippa Book I chapter 23-29 catalogue instead of inventing an unverified universal symbolic taxonomy. Every highlighted connection means a literal identical term in the SAME category for multiple source planets. The interface gives historical references only, no tradition-independent spiritual/medical influence claims. Future multi-tradition sourcing remains another assignment.

**Track 5 // Grimoire Scratchpad**: Activates existing `magick/grimoire/journal` as a plain-text temporary scratchpad. Pure `StationMagickJournalDraftPolicy.js` bounds title (96 chars) and note (2048 chars) and displays only a local word count and preview. `StationMagickJournalDraftPane.qml` keeps text in QML memory only, explicitly labels it UNSAVED, discards it when the screen hides and requires a two-click CLEAR DRAFT confirmation. **No file, SQLite, export, cloud, key, encrypted store, telemetry or recoverable history**. Persistent private notes, attachments, backup, retrieval, encryption, shared devices and consent will require a separate security and ownership assignment; do not silently extend this temporary UI into a durable writer.

All new panes reuse Post-Apollo Colors/GohuText/QuietText/ActionButton, and all routes reuse the existing StationMagickSubjectPane Loader. No Quickshell installation/restart, desktop changes, new network actor, Process, Timer, WebEngine, image import, alternate astronomy provider or public copyrighted art.

## HOW TO USE

After operator-authorized GitHub merge and separately approved local deployment:

1. **LUNAR + SOLAR > CALENDAR**: select a provider-forecast date, inspect Moon phase/illumination, day length, rise/set and two-source bars. No saved calendar events.
2. **INDEX > PLANETARY MAGICK > TRADITIONAL TIMING**: choose a forecast date with the following sunrise available, click hour 1-24 and inspect the historical ruler and actual provider-local start/end labels.
3. **MAGICK > ASTROLOGY > EVENT SETUP**: enter optional event UTC date/time and latitude/longitude; choose zodiac and house model. Inputs are validated, but the chart is explicitly NOT computed or saved; CLOSE returns to the unchanged current JPL chart.
4. **INDEX > DIVINATION > SYMBOLISM**: search/filter a sourced Agrippa term, choose a record and inspect planets and chapter references. No invented external canon.
5. **INDEX > GRIMOIRE > JOURNAL**: type a temporary title/note, inspect word count, and press CLEAR DRAFT then CONFIRM CLEAR to erase. Close/hide to discard. This is **not persistent**.

The exact navigation labels in the user's installed version must be checked at native review, because the repository may not be deployed to Fedora.

## VERIFY

- New `tests/weather/test_magick_five_track_foundations_m7a.js` covers five pure source/ephemeral policies, live route/QML wiring, forecast-day validation, phase/illumination/clock source fidelity, M6d ruler reuse, UTC input/date/location checks, exact Agrippa associations without false quicksilver equivalence, local journal no-persistence and ownership boundaries.
- Legacy `test_magick_subject_panels_g1.js` adjusted only for replacing the old nonfunctional CALENDAR placeholder; old COSMOS source tests stay.
- Existing `.github/workflows/weather-cosmos-jpl-network-v4a.yml` extended to run M7a with M4-M6j, V4a-V5b, other owner regressions.
- Exact-head GitHub CI, mergeability and current base comparison must be verified before reporting passing status. Source-level JavaScript/QML tests do not constitute native Qt rendering or operator acceptance.

## WATCH OUT FOR

This is an **initial implementation across five independent domains**, not a claim all five large requested feature families are complete. In particular, the forecast is a short outlook, not a true Moon-event calendar; daytime/nighttime Chaldean divisions are still DST-imprecise around offset changes; chart setup is merely a validated, temporary specification; symbolism is one explicitly identified historical edition, not all traditions; and journal contents are deliberately **lost on hide/restart**. A user wishing to keep notes must use a separately approved persistent storage system later.

Respect concurrent Hospital workers: no live registration or Room ownership was verified, so do not imply accepted handoff or authorization over WeatherService/JPL/process/SQLite/personal data. Recheck active PRs/main before merging or additional shared-QML work. No runtime image screenshots of the five new instruments have been seen. Native small-screen fit and focus behavior, especially on 400-500px panels, need testing. The existing Wild Unknown artwork remains unresolved and deferred by operator decision; Tarot is untouched by M7a.

## CHECKLIST

- [x] Verify main and no active MAGICK/Weather PRs at preflight
- [x] Read Syntagma and Hospital operating rules
- [x] Build source-only lunar/solar forecast calendar
- [x] Build traditional timing date/24-hour atlas from existing clock
- [x] Build temporary event UTC / house / zodiac setup with explicit source blockers
- [x] Build one-source historical symbolism view
- [x] Build temporary, non-persistent grimoire scratchpad
- [x] Add M7a tests and preserve original weather/MAGICK regressions
- [ ] All exact PR-head GitHub checks pass
- [ ] Operator-authorized merge and separate local deployment
- [ ] Native visual, click and privacy acceptance for five screens
- [ ] Later full event chart, multi-tradition sources, accurate DST source and persistent private journal

## NEXT

Open draft PR, run exact-head GitHub workflows and repair evidenced failures. After operator approval, install on Fedora in a separate authorized task and inspect all five screens, with special emphasis on whether unsaved journal text is actually discarded when navigating away. Future work should proceed as independent M7b-M7f milestones, one specialist-owned slice per source or storage boundary:
- Lunar Moon/event UTC provider integration for full lunation calendar; separately sourced equinox/solstice event instants.
- Planetary UTC-offset-aware solar event timing, then richer chart interactions.
- True chart computation from multi-body source, observer location and selected house/zodiac conventions with no fabricated conclusions.
- Additional identified public-domain/licensed traditions, comparing sources without treating them as universal facts.
- Privacy-preserving journal storage design with encrypted draft recovery, explicit permissions, backup/export and local-only behavior.

## DECISIONS

This branch is an authorized **initial functional foundation**, not completion or final acceptance of all five large feature families. Preserve user-facing existing COSMOS/JPL and M6g-J Tarot behavior. Never store sensitive grimoire text or personal event data as a side effect. Keep scientific source observations separate from historical/symbolic associations. No global Visual V3 or unrelated widget changes. The operator retains final authority over integration, desktop activation, and acceptance.
