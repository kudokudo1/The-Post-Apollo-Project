# Weather Station // M28-R Earth-weather versus COSMOS boundary correction

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Weather Station CLASSIC → SUBJECTS semantic/visual migration  
ASSIGNMENT // Return terrestrial weather from the M28-P COSMOS full view to proper WEATHER routes without deleting original visuals  
STAFF // External Hospital-compatible Doctor, OPEN AI // CHATGPT, not live Hospital-registered  
BASE // GitHub `main` `6e5db43fbc5d82ce3cf8e7107909b5dc8e1ab395`  
CONSTRAINTS // No new data providers, no local Fedora/Sway/Quickshell modification, no CLASSIC deletion or Stage Director activation

## IMPLEMENTATION

Operator review of the M28-P native COSMOS **SKY // ALL** screenshot shows an incorrect taxonomy: the old CLASSIC `StationSky.qml` combines local **Earth weather** (current condition, air, humidity, pressure, cloud, wind, hourly/daily forecast and photo-light) with **astronomy** (Sun/Moon ephemeris, eclipses, meteor showers, celestial navigation, ISS and planet clocks). M28-P deliberately unfiltered all 14 sections to restore their visibility, but did so under COSMOS. That was not the requested domain separation.

**M28-R** changes only the existing route filtering and presentation:

- **COSMOS → ASTRONOMY** (unchanged internal `cosmos/sky/full` compatibility path) now shows its eight astronomical groups: `header`, `astronomy`, `moon`, `iss`, `eclipses`, `celestial-fix`, `planet-clock` and `meteor`. Its original existing source contracts remain, and it presents `LOCAL REFERENCE READY/WAITING` instead of misleading `WEATHER ONLINE` in the astronomy header. No `current`, `atmosphere`, `hourly`, `daily`, `runtime` or `twilight/photo-light` rows appear there.
- **WEATHER → NOW + AIR** (`weather/conditions/current`) reads the same original `StationSky` and now shows `header`, original `runtime` source timestamps, `current` (including AQI, humidity, wind and conditions) **and** `atmosphere` (pressure, visibility, clouds, precip, UV). Its deeper `weather/conditions/air` and `weather/conditions/pollen` routes retain their original `StationGround` air PM/gases/pollen renderers.
- **WEATHER → FORECAST** (`weather/forecasts/hourly`) now shows **hourly + daily forecasts together**, and the same original `twilight`/photo-light solar-time calculations and artwork. Separate `weather/forecasts/daily` and `weather/forecasts/air` still work through INDEX.
- **WEATHER → OVERVIEW** already uses the original `StationHome` snapshot, official NWS alerts and locally relevant conditions and next-hours summaries, without injecting COSMOS Kp/Space streams. Its source and rendering ownership are unchanged.
- **COSMOS → SPACE // ALL** retains all 17 of the original `StationSpace` section types, including NOAA SUVI solar imagery, Kp historical graphs, space-weather forecasts, X-ray curves and aurora. These are **space weather**, which is in-domain for COSMOS.
- The existing dedicated COSMOS Sun → Twilight / Photo Light deep INDEX leaf routes remain as astronomy cross-references to the Sun's position. The complete COSMOS ASTRONOMY page itself no longer presents those local weather-light windows, which now have a prominent main WEATHER forecast home.

This partitions all 14 **original SKY** section types without losing a section: eight astronomical types in COSMOS and six terrestrial types in WEATHER. `StationSky` itself remains one original shared component with one selected route-scoped loader. No additional collector, cache, image transport, archive writer, terminal process or duplicate persistent data is introduced. M0's 103 historical route mappings and CLASSIC's unfiltered original page are unchanged.

## HOW TO USE

After merge and separately authorized local application:

1. Open Weather Station → **SUBJECTS → WEATHER → NOW + AIR**: current temperature/condition, atmosphere and quality/health status in its original full-width scroll view. Detailed particulate/gas/pollen routes are in **INDEX → WEATHER → CONDITIONS**.
2. **WEATHER → FORECAST**: original hour-by-hour and daily forecast artwork/cards, followed by local twilight/photo-light windows. Detailed air-quality forecast remains **INDEX → WEATHER → FORECASTS → AIR QUALITY**.
3. **WEATHER → OVERVIEW**: current weather, alerts, relevant conditions, short-term forecast and adaptive overview.
4. **COSMOS → ASTRONOMY**: celestial ephemerides, moon, eclipses, meteor showers, ISS and planet clock. No terrestrial weather observations or forecast cards.
5. **COSMOS → SPACE // ALL**: solar wind, NOAA space weather, solar imagery, geomagnetic/Kp graphs and cosmic forecasting.
6. **CLASSIC** remains available as a fallback and visual comparison until the operator accepts these changes on Fedora.

## VERIFY

- `tests/weather/test_weather_cosmos_domain_separation_m28r.js`: derives 14 unique SKY sections from actual QML and checks **every one has exactly the intended complete-view domain**, route and source admission; Earth-weather current/atmosphere/runtime are in NOW, hourly/daily/twilight in FORECAST; astronomical ones in COSMOS only; all 17 SPACE families remain COSMOS.
- Adjusted original `tests/weather/test_cosmos_full_visual_parity_m28p.js` to test the **union across correct destinations**, not incorrectly assert all 14 terrestrial/astronomical types appear in COSMOS.
- Adjusted `tests/weather/test_weather_subject_panels_m2a.js` to require daily and twilight in the selected WEATHER FORECAST route and atmosphere in NOW.
- Dedicated `.github/workflows/weather-terrestrial-cosmos-boundary-m28r.yml` reruns the source partition and M28-P, M2a, M28-F/G/L, W1 and navigation contracts. Broader native source/CI remains a separate gate.
- GitHub automation verifies section policy and source wiring. It does not prove local image downloads, font legibility, screenshots, pointer scrolling, freshness or final operator acceptance.

## WATCH OUT FOR

- This fixes the root **classification** error, not the larger unfinished CLASSIC → SUBJECTS visual parity audit. The 103/103 mapping tally remains a route provenance count, not full UI acceptance.
- Original `StationSky` still calculates sunrise and solar context using the shared WeatherService's location/time reference. That is input data for astronomical calculations; the COSMOS observatory does not display weather forecast rows.
- The COSMOS deep Sun/Twilight leaf remains, since it is a solar astronomy reference. If the operator wants it removed there entirely, that is an additional INDEX provenance/route reassignment, not the terrestrial **main** view bug.
- The original single `StationCosmosSubjectPane` and `StationWeatherSubjectPane` loaders determine which shared renderer exists. The weather service itself is globally shared, and this change adds no new polling interval.
- A concurrent PR #1161 owns the planet-clock USNO row-model policy/test, **not these route or StationSky files**. Recheck current HEAD and PR files before merge.
- Never erase CLASSIC or overwrite the running user's local Quickshell without separate authorization.

## CHECKLIST

- [x] Inspect operator's screenshots and identify terrestrial cards in COSMOS.
- [x] Read Syntagma AGENTS and Hospital-compatible protocol.
- [x] Audit current route/pane policies, source activation and concurrent Weather owner.
- [x] Move native main-view section visibility to WEATHER without duplicating service owners.
- [x] Keep all original SKY sections, all SPACE sources, astronomy visuals and CLASSIC fallback.
- [x] Add exact source-derived regression test, amend old parity assumptions and dedicated CI.
- [ ] Verify final PR head and repair any CI regressions.
- [ ] Merge bounded GitHub PR if required checks green and ownership clean.
- [ ] Operator compare real WEATHER/COSMOS native screenshots, scroll, source state and pointer controls.
- [ ] Continue M28-Q remaining CLASSIC visual/rendered control audit before retirement.

## NEXT

Verify on Fedora that WEATHER NOW and FORECAST render the relocated terrestrial sections and that COSMOS ASTRONOMY no longer shows them. Revisit how AIR forecast is surfaced from the main WEATHER rail after actual pointer acceptance. Continue full rendered-content parity coverage for GROUND, MAP, NEWS and RADIO; do not use a navigation count as retirement approval.

## DECISIONS

COSMOS means celestial/outer-space and space-weather observations. WEATHER means local Earth atmosphere, sky conditions, air quality, meteorological forecasts and local photo-light. EARTH remains geography, environmental events and maps. The operator is final authority; source changes are reversible; no live Hospital registration or final DONE is claimed.
