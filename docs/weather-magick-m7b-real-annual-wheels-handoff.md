# 🏥💜 MAGICK M7b // Annual JPL Lunar and Solar Wheels

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station MAGICK > Lunar + Solar > Annual Calendars
ASSIGNMENT // Source-accurate lunar daily/year wheel, solar 24-term wheel and calendar marker contract
STAFF // DOC (external Hospital-compatible ChatGPT, not live-registered)
BRANCH // feat/weather-magick-m7b-real-annual-wheels-20261106
BASE AT START // eeaad9ea2788eb48eb0b898ea0c17f7a1b054cbb
PERMISSIONS // Bounded GitHub code/tests/docs; no workstation changes or auto-merge

## IMPLEMENTATION

M7a PR #1389 was already merged. M7b adds a distinct on-demand year calculation to the existing local JPL/Skyfield installation without modifying the M5 paired-chart process, Weather forecasts, COSMOS collectors, or calendar writers.

- scripts/weather/celestial_annual_calendar.py loads exactly one explicit local BSP kernel, a bounded year (1901–2099), and an explicit IANA timezone. It samples the Moon at local noon for each date (365/366), calculates geocentric apparent Moon–Sun phase angle and illuminated fraction, locates principal lunar phase UTC events using Skyfield almanac.moon_phases, and locates 24 solar terms by 15-degree crossings of the Sun's apparent geocentric longitude in the true ecliptic of date.
- StationMagickAnnualAtlasPolicy.js validates provenance, exact daily coverage, phase bands, all 24 solar-longitude labels, and normal-calendar markers, failing closed on invalid data.
- CelestialAnnualCalendarService.qml uses an explicit CALCULATE YEAR action and reuses the existing installed Python/JPL kernel. It neither downloads kernels nor writes caches.
- StationMagickAnnualCalendarPane.qml adds LUNAR YEAR, SOLAR YEAR and retained FORECAST modes inside MAGICK > LUNAR + SOLAR > CALENDAR. The year wheels place data according to actual calendar dates. Moon YEAR shows one illumination tick per day plus major lunar events; Moon MONTH shows 28–31 individual discs. Solar YEAR shows 24 term nodes with four equinox/solstice nodes emphasized. Selecting displays the exact source date, UTC event time and solar longitude.
- The same annual JSON includes calendar_markers.daily_moon (date and daily phase) and calendar_markers.events (precise phase/solar-term UTC times). The separate Calendar/Planner interface is NOT modified in this PR.

## HOW TO USE

After separately authorized merge and desktop deployment:
1. Weather Station > MAGICK > LUNAR + SOLAR > CALENDAR.
2. Choose LUNAR YEAR / SOLAR YEAR / FORECAST.
3. Select year and explicitly enter an IANA zone such as America/New_York; default is UTC.
4. Press CALCULATE YEAR. This reads the existing local JPL kernel on demand.
5. Select a day, month, or term. MONTH shows the individually dated Moon icons.

## VERIFY

Synthetic Python contract tests cover leap years, IANA zone boundaries, all 24 solar-term identifiers, phase bands, and invalid provenance. JS policy tests check circle positioning, the required calendar markers, and preservation of Forecast and old MAGICK routes. New M7b GitHub workflow runs both plus M7a/G1 regressions. Synthetic tests do NOT establish actual ephemeris accuracy. Real-kernel comparisons and native Qt review are separate, pending checks. PR-head CI must be checked after opening.

## WATCH OUT FOR

- No installed BSP or Skyfield in GitHub CI: numeric reality must be checked against a real user-approved local ephemeris and authoritative source before accepted.
- No new weather provider; an on-demand annual process loads the same user-supplied kernel. Do not confuse the exact annual events with short-range weather forecasts.
- IANA timezone is explicitly UTC until a separately approved shared Settings zone integration. The source event is global UTC; the display local calendar day varies by selected zone.
- All 365/366 lunar days cannot be individually readable in a small annual ring; YEAR uses illuminating daily ticks and lunar events, MONTH uses individual discs. Moon discs are schematic illumination, not local optical orientation.
- Solar terms are named traditional seasonal markers based on solar longitude, NOT forecast weather.
- Normal Calendar markers are exported as a contract but are NOT yet rendered in the Calendar/Planner-owned interface, which needs its own ownership/integration check.
- No local Fedora, Quickshell, personal notes, databases, or cache changes. Native visual acceptance remains pending.

## CHECKLIST

- [x] Hospital/Syntagma preflight and M7a merge confirmed
- [x] Collision-isolated GitHub branch
- [x] Daily phase/illumination and exact lunar principal phase search
- [x] 24 ecliptic solar-term search and year-aware calendar event contract
- [x] Radial annual and monthly views; Forecast preserved
- [x] Node/Python source contract tests and isolated CI workflow
- [ ] PR-head checks / independent source review
- [ ] Operator merge decision
- [ ] Separate authorized deployment and real-kernel verification
- [ ] Native geometry/click/availability acceptance
- [ ] Coordinated Calendar/Planner daily marker UI integration

## NEXT

Open the draft PR; verify exact PR-head checks, repair any failures, then independently review numerical source and screenshot-based native acceptance. Calendar/Planner UI integration is a different bounded assignment across an ownership boundary.

## DECISIONS

The operator explicitly rejected inaccurate image-generated posters. Real numerical dates determine the wheel geometry and labels. Use one existing installed ephemeris, explicit year and zone, no fabricated event times, no automatic deployment, merge or completion claim.
