# Weather Station // M28-G COSMOS SKY/SPACE parity

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Weather Station / CLASSIC → SUBJECTS full capability migration  
DOCTOR // External Hospital-compatible ChatGPT  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL; no confirmed live Hospital attachment  
ASSIGNMENT // Reconcile the original SKY astronomical and SPACE solar-weather controls into existing native COSMOS routes, preserving the current data source controllers  
BASE // main at `0c1b039e19e6d4bd7c5f5b595a577a406b7e6c60`

## IMPLEMENTATION

`StationCosmosSubjectPanelPolicy.js` already routes the original `StationSky` and `StationSpace` source-section components to 20 native COSMOS destinations. These components carry the original USNO, NASA, IAU and NOAA SWPC provider admission gates, preserve their original data timing, and share the root `SpaceService`. The current `StationCosmosSubjectPane` displays STAR/SKY and SPACE within a single overview, or a filtered specific pane for a leaf.

A more recent `StationSpaceWeatherTimelinePane` wraps the **unchanged original StationSpace** under the observed solar-wind/IMF historical chart on the COSMOS space-weather overview and history routes. The original panels therefore remain accessible; the chart does not own new collectors or displace the old instruments.

M28-G adds 23 exact source-wired IDs to the INDEX migration ledger:

- 10 SKY controls: Sun/Moon astronomy, ISS passes, USNO Moon, NASA eclipses, celestial fix, planetary rise/set, IAU meteors, twilight, photo-light, current Sun.
- 13 SPACE controls: core geomagnetic/solar, solar-wind context, NOAA scales, solar cycle, Kp history and forecast, SUVI, aurora, X-ray, flares, watch products, warning validity, bulletins.

All point to already known native COSMOS leaves (no new navigation destinations), using the existing M28-D deduplicated **OPEN SUBJECTS // ...** buttons.

**Not classified:** `home-space-weather` (original HOME quick card still requires semantic parity), `space-field-times` (TOOLS source-time/provenance, not a COSMOS pane), plus unrelated EARTH, NEWS and MAGICK controls. The historical M1 source map and all still-pending CLASSIC shortcuts remain unchanged.

The M28-F historical test now asserts its exact 30 original IDs without freezing the overall registry at 46; current total after M28-G is 69 of 103 source-wired, leaving 34 for review.

## HOW TO USE

After merge and separately authorized workstation deployment: Weather Station → SUBJECTS → COSMOS. Use the main family rail and the SUN, MOON, PLANETS + SKY, EVENTS, SPACE WX bottom routes to inspect original SKY/SPACE data. The deep header INDEX offers native destinations for the exact reviewed controls. It does not launch external browsers or start independent solar data collectors.

SPACE WX → OVERVIEW and HISTORY show the new recorded-series graph with the original source-context sections still below it. NOAA and astronomical availability depend on real providers; the route does not claim live observations or a confirmed visible ISS pass.

## VERIFY

- `tests/weather/test_index_cosmos_cutover_m28g.js`: exact 23 control IDs, COSMOS valid leaf routes, route-specific filtered sections, six SKY and seven SPACE source gates, original source components, timeline wrapper retention, no duplicate source owner, unreviewed controls remain accessible, invalid-route refusal.
- Re-run original M0/M1, COSMOS C1, W1 and M28-D/E/F tests through dedicated `.github/workflows/weather-subjects-cosmos-parity-m28g.yml`.
- CI pending creation; no local Fedora/Quickshell native layout, provider connectivity, Stage Director integration or operator visual acceptance has been proven by this branch.

## WATCH OUT FOR

- C1 consciously co-locates several instruments: SUN/POSITION includes the original Sun+Moon summary; PHOTO LIGHT shares twilight; MOON/POSITION and constellation references share celestial-fix. This classification means those original instruments are still accessible, not that new specialized cards are complete.
- NOAA SUVI is manually requested; eclipse dates are global dates without local visibility claims; ISS geometric passes are not confirmed optical sightings.
- Source availability and missing-data conditions remain observable, not papered over by fake values. Other MAGICK ephemeris work is owned separately and not part of M28-G.
- Only current actual mapped SKY/SPACE sources, no new registry keys for unsupported future celestial visualizations.

## CHECKLIST

- [x] Read current source, provider ownership, C1 and timeline code; confirm no colliding open Weather UI PR.
- [x] Admit 23 exact pre-existing COSMOS controls, leaving cross-domain unknowns pending.
- [x] Preserve M28-F invariant for future work.
- [x] Add focused Node regression, CI workflow and durable handoff.
- [ ] Exact-head CI success.
- [ ] Approved review/merge and separate operator desktop deployment.
- [ ] Live COSMOS source and layout acceptance.
- [ ] Review EARTH and TOOLS remaining sources, then CLASSIC retirement gate.

## NEXT

After focused CI, verify mergeability and land under the established operator GitHub workflow. Then proceed to the remaining EARTH event/dossier source controls with strict source/event/archive separation, and later TOOLS provenance and HOME quick-card semantics. Keep CLASSIC until every necessary capability is reconciled and operator approves removal.

## DECISIONS

One subject-first Station with seven top-level families, no duplicate space-weather fetchers, no second SpaceService or FileView, no local machine write, no Sway/Kitty operation, no automatic MAGICK inference, no production CLASSIC deletion, and no claim of final DONE.
