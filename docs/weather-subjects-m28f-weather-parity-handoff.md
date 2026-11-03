# Weather Station // M28-F WEATHER native parity and source route correction

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Weather Station / CLASSIC → SUBJECTS full capability migration  
DOCTOR // External Hospital-compatible ChatGPT  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL; no confirmed live Hospital session or assignment registration  
ASSIGNMENT // Reconcile existing HOME/GROUND/SKY/MAP WEATHER controls with native SUBJECTS routes without cloning providers or prematurely retiring CLASSIC  
BASE // `main` at `bb84a7a9bf02e273748f9ece40cbc7d227c50c25`

## IMPLEMENTATION

Existing `StationWeatherSubjectPane` already loads the original filtered `StationHome`, `StationGround`, `StationSky` and weather-only `StationDiscovery` components. `StationWeatherSubjectPanelPolicy.js` defines the exact existing section map and `needsSource` activation guards. M2a/M2b and M27-A implemented these earlier; M28-F reconciles their now-established source wiring with M28-D's INDEX cutover ledger.

Two actual navigation mistakes were found and corrected in `StationSubjectNavigationPolicy.PANELS`:

- `ground-coastal-relationship` incorrectly sent users to `weather/history/relationships`, whose current pane is the HOME AQI relationship display, **not** the original `StationGround` coastal relation. Corrected to `weather/history/relationships/coastal` (`coastal-rel`).
- `ground-marine-relationships` had the same incorrect landing; corrected to `weather/history/relationships/marine` (`marine-rel`).

Exactly 30 source-backed controls are now explicitly classified as **wired in SUBJECTS**, extending the existing `WIRED_IN_SUBJECTS` table with milestone `M28-F`: six HOME weather-summary/history/alert/relevance controls, sixteen GROUND air/water/alerts/hazards/relationship controls, five SKY observation/forecast/inspector controls, and three WEATHER-only original MAP radar/fallback/smoke layers. The explicit source-to-section table in the regression test is the admission record.

The existing deep INDEX now automatically offers native **OPEN SUBJECTS // ...** destinations for these exact proven routes, deduplicated by leaf; all other unreviewed historical CLASSIC source links remain. No provider, terminal actor, archive, FileView, duplicated compositor window, or local runtime was changed.

## HOW TO USE

After separate merge and local deployment, open Weather Station → SUBJECTS → WEATHER. Direct working routes already exist in the left family and bottom submode navigation. The detailed header **INDEX** lets you inspect the full route tree and select **OPEN SUBJECTS // ...** for classified native controls.

For coastal and marine relationships, use **WEATHER → HISTORY → RELATIONSHIPS → COASTAL** or **MARINE**, respectively. They now lead to the original StationGround pressure/water-level and wind/wave-height relationship instruments, not the HOME AQI relationship pane.

Original CLASSIC remains accessible for unreviewed controls until complete parity and operator acceptance.

## VERIFY

- `tests/weather/test_index_weather_cutover_m28f.js`: 30 exact IDs and real native leaf destinations; correct active page and filtered section; source-specific marine/coastal activation; preserved HOME ranker, NWS, river, buoy, coastal, lightning, heat/fire, air, hourly inspector, daily, weather map functions; negative controls that must **not** be silently certified.
- Historical M28-D regression updated so its source-map preservation assertion continues to hold while later independent WEATHER cutovers are allowed. M28-A/B/C and M28-E RADIO milestone tests remain intact.
- New `.github/workflows/weather-subjects-weather-parity-m28f.yml` runs the new exact parity contract plus the original M0/M1, M2a/M2b, W1/W1r and M28-D/E integration checks.
- CI evidence: **pending at PR creation**. These are source and route contracts; no live Fedora, NOAA/WTTR, NWS, MPD, Sway, or visual operator acceptance is claimed.

## WATCH OUT FOR

This classification means real route/section/source **wiring exists** in the repo, not that a provider always returns observations or every original interaction has been accepted on the operator's workstation.

`home-quick-conditions` maps to SKY CURRENT, not the original HOME QUICK combined wind/humidity/UV view. `home-aqi-humidity` and `home-aqi-wind` currently target the parent WEATHER history relations; their correct leaf selection and behavior need a separate review. Those are left **unreviewed**. So are HOME source-health, cross-domain SPACE/MAGICK, earthquake source, WATCH video, and all other uncategorized controls. Do not remove their CLASSIC access.

Only 30 existing mapped IDs are promoted in this increment. Preserve the original event/dossier storage and Stage Director/Kitty ownership. Independent Social/CPU++/MAGICK changes are not part of this branch.

## CHECKLIST

- [x] Read Syntagma authority and Hospital behavior; inspect current main, active Weather PRs, source components and previous parity contracts.
- [x] Fix two incorrect GROUND relationship landings.
- [x] Account for 30 exact source-backed native WEATHER panel controls without duplicating old pages.
- [x] Keep all remaining CLASSIC source links and old source provenance.
- [x] Extend dedicated regressions and durable handoff.
- [ ] Verify exact-head GitHub CI; fix bounded failures.
- [ ] Operator review/merge and separate desktop update.
- [ ] Runtime test at least one source section from each family, with source-unavailable states.
- [ ] Continue remaining source-by-source capability audit and final CLASSIC retirement gates.

## NEXT

After all final-head CI passes, merge under current approved repository workflow. Continue M28-G with COSMOS and SPACE/SKY sections and examine HOME QUICK and AQI cross-domain relations separately; do **not** promote a route merely because its name exists. Reconcile the complete map before deleting old CLASSIC loader and navigation.

## DECISIONS

Operator's existing SUBJECTS-first architecture remains authoritative: seven top-level families and cross-domain ownership preserved; no duplicate fetchers/stores/terminal actors, no local workstation modifications, no silent host restart or git pull, no final CLASSIC deletion without full reviewed parity. Final DONE belongs to the operator.
