# Weather Station // M28-P COSMOS visual-fidelity restoration

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Weather Station / CLASSIC → SUBJECTS content-fidelity recovery  
STAFF ROLE // External Hospital-compatible Doctor (no confirmed live Hospital registration)  
ASSIGNMENT // Restore complete original SKY and SPACE data, charts, images and interactions in native SUBJECTS views  
BASELINE // `main` `40e1354fe50c73771c0eca71985406a7ab425e71`  
STATUS // GitHub implementation + tests, no local deployment or CLASSIC retirement

## IMPLEMENTATION

The operator provided seven **actual classic SKY/SPACE** screenshots demonstrating missing or difficult-to-reach data in SUBJECTS. The previous **103/103 M0 control ID mapping ledger only verified route existence and per-control source links; it did not verify visual-content completeness**. The earlier M28-G report overclaimed the scope by calling this complete COSMOS parity. Source audit identified the exact mechanism:

- `StationCosmosSubjectPanelPolicy.ROUTES["cosmos/overview"]` contains only 4 SKY and 4 SPACE sections, and `StationCosmosSubjectPane` squeezes both into **two half-height** panels. It is a summary dashboard, not an original-page replacement.
- `cosmos/space-weather/overview` previously selected only SOLAR, SCALES, FIELD and AURORA. It hides the original NOAA solar-cycle prediction graph, Kp 72-hour history, Kp forecast, NOAA SUVI full solar imagery, X-ray and flare curves, watch-day and bulletin panels.
- SKY's **CURRENT/ATMOSPHERE, ISS, USNO moon, NASA eclipses, USNO celestial fix and planet rise, IAU meteor showers, twilight/photo lighting, hourly/daily forecast** are split over narrow route pages, never accessible together in SUBJECTS.
- These original instruments still exist as `StationSky.qml` (**14 unique `sectionVisible` groups**) and `StationSpace.qml` (**17 groups**). They are not physically deleted.

**M28-P adds two explicit native full-page COSMOS routes** without cloning a collector or duplicating persistent state:

1. `cosmos/sky/full`: one original `StationSky`, all **14 original section families** plus existing COSMOS sun/moon visual instruments, its own `Flickable` and all original SKY source admission (six provider-specific services). The COSMOS bottom main mode previously labeled **PLANETS + SKY** now reads **SKY // ALL** and opens this route. Planet clock/celestial-fix remain available in the deep INDEX.
2. `cosmos/space-weather/full`: one original `StationSpace`, all **17 original section families**, including the image-source-bound NOAA SUVI solar image and all solar-history/model graphs. COSMOS bottom main mode previously labeled **SPACE WX** now reads **SPACE // ALL** and opens this route. Detailed SOLAR, AURORA, FORECAST, and other COSMOS paths remain reachable in INDEX.

The other four COSMOS main bottom modes remain OVERVIEW, SUN, MOON and EVENTS, maintaining **six** equal-width bottom buttons rather than shrinking the labels into an unreadable eight-button rail. The main COSMOS overview remains a selective live dashboard with two half-height contexts, and is no longer presented as the sole full-parity destination.

Source lifetime remains route-scoped: the original `StationCosmosSubjectPane` has one active `Loader`, selecting SKY or SPACE. `visibleFor` grants all sections only for the exact full route in the matching page, and `needsSource` enables only the known page-specific original source contracts, refusing forged or cross-subject paths. No request fetch, cache, archive write, timer, file, new image downloader or terminal process is added.

M0 historical `StationSubjectNavigationPolicy.PANELS` **103 original control hints are unchanged**; the full routes are additional visual-affordance destinations. Existing six M0 subject roots, HOME's separate workspace family, original services, persistent caches, station header, NEWS/VIDEO safety and CLASSIC remain unchanged.

## HOW TO USE

After the PR lands and a **separately authorized local Fedora/Quickshell update**:

1. Open Weather Station → SUBJECTS → **COSMOS** (left rail).
2. COSMOS bottom swap → **SKY // ALL**: inspect original SKY from current weather and visual sun/moon through astronomy, NASA eclipses, IAU meteor showers, planetary times, twilight, hourly and daily forecast. Scroll inside the original panel.
3. COSMOS bottom swap → **SPACE // ALL**: inspect NOAA Kp, solar wind/Bz, scales, solar cycle model, Kp history/forecast, SUVI solar image, aurora, X-ray, flares, watches, warnings and bulletins. Scroll inside the original panel.
4. The other four bottom tabs and **INDEX** still provide topic-filtered views; the bottom swap does not open CLASSIC or an external web browser. CLASSIC remains available from the root fallback button for side-by-side acceptance.

## VERIFY

- New `tests/weather/test_cosmos_full_visual_parity_m28p.js` discovers all the original SKY/SPACE section IDs directly from source and verifies **14/14** and **17/17** visible in the new exact native full routes, off-domain blocks, six SKY/seven SPACE source gates, source label/solar `Image` presence, original full-height `Flickable`, real bottom mode clicks and fixed six COSMOS family slots, and unchanged 103-ID historical map.
- `tests/weather/test_cosmos_subject_panels_c1.js` preserves exactly the old 20 route definitions while explicitly allowing only the two new full routes (22 total).
- New `.github/workflows/weather-cosmos-full-visual-parity-m28p.yml` runs full-visual, original COSMOS and M28-G, W1 and M0 route and Weather separation regressions; all existing relevant GitHub workflows also run on changed path.
- CI and **native visual acceptance are separate**. Green source/CI can verify QML visibility bindings and source gate contracts, but cannot establish that the operator's exact Fedora render has acceptable alignment, image load, scrolling performance, provider freshness or pointer behavior.

## WATCH OUT FOR

- **103/103 is route accounting, not visual parity.** Do not delete CLASSIC on that basis. Full SKY/SPACE source rendering should be compared with the operator's screenshots at the same effective location and provider time.
- Full pages intentionally activate **all known original page-specific source services while visible**, matching CLASSIC. Because they present long content, verify responsiveness and no duplicate requests when changing bottom tabs.
- `cosmos/overview` is still a compact two-half-height dashboard, not a full reconstruction. Users must open SKY // ALL or SPACE // ALL for all original content; the bottom mode labels make this discoverable.
- Original SKY combines weather and astronomy; the SKY // ALL page includes forecasts even when located in COSMOS. This preserves real source parity, not a new scientific classification.
- NEWS/VIDEO WebEngine safe mode and Stage Director isolated viewer remain separate. Do not infer playback success from preserved catalogues.
- The other original CLASSIC pages (HOME, GROUND, MAP, NEWS, RADIO, TERMINAL) have **not received the same exhaustive rendered-content parity audit** in this milestone. Visual parity must be audited individually before CLASSIC deletion.
- No local workstation files, user records, running Quickshell process or compositor settings are modified by this GitHub PR.

## CHECKLIST

- [x] Read original operator SKY/SPACE screenshots and current GitHub main.
- [x] Identify 14 SKY and 17 SPACE original QML section groups and partial-routing cause.
- [x] Add exactly two native full-page routes, preserve original 20 detailed routes and six bottom mode slots.
- [x] Preserve original visual sources, solar image, charts and flickable height and identity.
- [x] Add source-based no-clone tests and new CI workflow.
- [ ] Final-head CI and bounded repairs, if needed.
- [ ] Merge only when exact-head CI is green and ownership verified.
- [ ] Operator desktop comparison and acceptance of image visibility, scrolling, source freshness and controls.
- [ ] Extend exhaustive visual parity audit to HOME, GROUND, MAP, NEWS, RADIO and TERMINAL.
- [ ] Seek explicit operator authorization only later for final CLASSIC retirement.

## NEXT

After COSMOS full-page acceptance, M28-Q should inventory each original CLASSIC **visible section, graph/image and command/action** against its native SUBJECTS renderer, with a public traceable coverage matrix and 0 hidden-visual regressions for all original modes. Do not substitute index-link counts for rendered-content completeness. Keep the original CLASSIC fallback until accepted.

## DECISIONS

Preserve original visual architecture and per-route source owner; no new data collectors; six compact bottom buttons with two full modes; narrow details remain in INDEX; old provenance unchanged; no merge/deployment/retirement acceptance conflation; operator final authority.
