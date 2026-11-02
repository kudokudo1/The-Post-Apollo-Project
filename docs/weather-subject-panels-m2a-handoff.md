# Weather StationW // M2a WEATHER panel reuse

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station / Subject Migration M2a
WORKER // External Hospital-compatible ChatGPT
ASSIGNMENT // First live WEATHER subject panels from existing GROUND and SKY
STATUS // Draft PR, no local installation or runtime acceptance

## IMPLEMENTATION

13 approved existing M0 WEATHER routes now display actual working GROUND or
SKY panel sections via one `StationWeatherSubjectPane.qml`. The six subjects,
breadcrumbs and CLASSIC handoff from M1 remain unchanged.

Route to source:
- CONDITIONS / CURRENT, ATMOSPHERE => original SKY current/atmosphere rows
- CONDITIONS / AIR, POLLEN => original GROUND particulate, gas and pollen rows
- FORECASTS / HOURLY, DAILY => original SKY forecast cards and hour inspector
- FORECASTS / AIR => original GROUND Open-Meteo 12-hour air forecast
- WATER / RIVERS => original GROUND NWPS gauge, nearby compare, hydrograph,
  flood context, and precip relationship **in one panel**
- WATER / MARINE, COAST => original NDBC and CO-OPS panels
- HAZARDS / ALERTS, LIGHTNING, HEAT-FIRE => existing official NWS, nowCOAST,
  and NWS heat/fire-weather panels

The new `subjectRoute` input on StationGround and StationSky defaults to the
empty string; CLASSIC continues rendering **all its original sections** and
triggering exactly its prior sources. A fixed route filters section visibility,
without copying its data binding or control implementation.

`StationWeatherSubjectPanelPolicy.js` owns route→page/section mapping and
source activation rules. Historical forecast, relations, WEATHER overview,
weather-map rendering, and deep river subroutes are intentionally not claimed
as migrated yet. Those routes still show M1's honest classic-page handoff.

## HOW TO USE

Once PR is reviewed, merged and installed on desktop:
Open Weather Station > SUBJECTS > WEATHER.
Choose CONDITIONS, FORECASTS, WATER or HAZARDS and select one of the 13
supported routes. Its real existing instruments/controls appear in place.
Use UP/breadcrumbs to navigate. Choose CLASSIC to use the original complete
eight-page interface.

The live RIVERS parent contains the full original river instrument; its
deeper GAUGES/NEARBY/FLOOD/HYDROGRAPH links remain reserved for later actual
subsection extraction. This is intentional, not a claim that those subpanels
already exist.

## VERIFY

Focused Node tests cover route mapping, parent/source preservation,
visibility gating, safe CLASSIC defaults, and no new network or archive writer.
The existing Weather Station teardown workflow is also expected to run.
Quickshell graphical behavior and source availability on Fedora are **not**
verified by offline CI tests.

## WATCH OUT FOR

- Do not create separate WeatherService, NwsOfficialAlertSource,
  LightningSource, RiverSource, NDBC/CO-OPS collectors.
- In CLASSIC, no old section is hidden and astronomy services keep their
  established activity. In filtered WEATHER/SKY routes, the six astronomy
  fetchers are disabled. NDBC/CO-OPS only run on matching marine/coast routes.
- Shared NWPS/Lightning sources activate for only their relevant subject route;
  seismic stays CLASSIC-only until EARTH migration.
- Do not change NWS official pinned alert location semantics.
- MAP radar rendering, news→MAP handoff, event dossier/archive and
  Stage Director/Kitty geometry remain separate and untouched.
- Full WEATHER organization will require a later M2b for the overview,
  weather maps, historical forecast and analyses.

## CHECKLIST

- [x] Recheck current main/M1 merge and owner PRs
- [x] Pure filtered route policy
- [x] Filter existing panels with CLASSIC fallback
- [x] Reuse existing shared provider objects
- [x] Live route loader inside M1 subject browser
- [ ] Focused and full Weather CI verified
- [ ] Operator review and merge
- [ ] Local desktop visual acceptance

## NEXT

Verify GitHub CI. Fix any source or contract failures only, then seek the
operator's acceptance. Follow with actual WEATHER map/history/overview
subsections, not the cross-domain EARTH or MAGICK migration.

## DECISIONS

No local desktop changes, no archive schema edits, no production activation,
no merge and no live Hospital registration. The source-first architecture
and single-provider ownership remain canonical.
