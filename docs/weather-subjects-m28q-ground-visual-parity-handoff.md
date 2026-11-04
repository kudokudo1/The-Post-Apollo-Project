# Weather Station // M28-Q GROUND 1:1 visual-content migration

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Weather Station CLASSIC → SUBJECTS GROUND content preservation  
ASSIGNMENT // Copy *presentation access*, not providers: mount complete original GROUND in SUBJECTS without remodeling or feed changes  
STAFF ROLE // External Hospital-compatible Doctor, provider OPEN AI // CHATGPT; no verified live Hospital assignment  
BASELINE // GitHub `main` `5dace7b188dd8bcbd4b21b647a7a8eaae7087711` at branch creation  
PERMISSIONS // Bounded GitHub source/policy/tests, CI, PR; no local Fedora edits, Quickshell restart, data-feed repairs, CLASSIC deletion or production activation

## IMPLEMENTATION

The operator supplied screenshots of original CLASSIC GROUND lightning, river/flood/stageflow and fire/weather contexts. Several original feed panels are empty while another worker repairs the feeds. **Do not repair or fake the data.** The operator wants every original block *present* in SUBJECTS now and will restyle later.

Source audit: `StationGround.qml` owns **16 unique visible section groups**:
`header`, `runtime`, `alerts`, `coastal-rel`, `marine-rel`, `rivers`, `marine`, `coast`, `lightning`, `heat-fire`, `air-pm`, `air-gases`, `pollen`, `air-forecast`, `seismic`, `source`.

The previous migration dispersed most of them across WEATHER routes, but the complete runtime source rack and original three-card recent-earthquake panel lacked a complete visual home. The EARTH quake map and TOOLS source-health rack contain related information, **not those original visual blocks**.

**M28-Q adds `weather/ground/full`, exposed by a direct `GROUND` button on the WEATHER bottom rail and as INDEX → WEATHER → GROUND → ALL ORIGINAL INSTRUMENTS.** The page loads precisely the existing `StationGround` component through the existing *single* `StationWeatherSubjectPane` Loader, whose `subjectRoute` and `visibleFor` now admit all 16 original sections for that exact native route. It inherits the original `Flickable` and `NeonScrollBar`, NWS alerts, USGS recent cards, coastal/wave relationship charts, NOAA NWPS rivers/flood/crest/stageflow, NOAA NDBC marine, NOAA CO-OPS tides, NOAA NOWCOAST lightning, heat/fire context, air/pollen and next-12-hour forecast, source fix, and the complete eight-source runtime rack. The source feeds' current blank/error states remain unchanged.

The root `WeatherStationW.qml` original shared `SeismicService` is now admitted on this exact WEATHER full route *in addition to* its previous EARTH map routes. The same existing root services handle `river` and `lightning`; the existing panel-owned services handle `marine` and `coastal`. Full-route `needsSource` permits only these five provider types, not arbitrary collectors or new timers. The route-scoped Loader remains inactive when the WEATHER full route is not visible.

This is an additive eighth WEATHER bottom submode (temporarily narrower buttons). The original seven modes, native detail routes, COSMOS astronomy separation, original CLASSIC eight-mode interface, and historical 103-control provenance are unchanged. **Do not optimize or redesign the appearance in this milestone.**

## HOW TO USE

After the merge and **separately approved** local deployment:

1. Open Weather Station → **SUBJECTS → WEATHER** using the left family rail.
2. Select **GROUND** in the bottom row. Scroll the original full GROUND page; inspect all source sections regardless of whether their data is currently available.
3. The complete USGS recent-event three-card view and `ENVIRONMENT // SOURCE` footer are at the bottom, following its original source order. The complete runtime source rack appears near the top.
4. Open **INDEX → WEATHER → GROUND → GROUND // ALL ORIGINAL INSTRUMENTS** for the same page. Existing WATER, HAZARDS, NOW + AIR, FORECAST, HISTORY and EARTH GEOLOGY pages continue to work independently.
5. Use **CLASSIC → GROUND** for manual visual comparison. This full route does not itself repair data sources or change what counts as a successful feed response.

## VERIFY

- `tests/weather/test_ground_full_visual_parity_m28q.js`: source-derived **16/16 original section groups** visible on the full route, same QML instance and flickable, 103/103 historic M0 hints unchanged, eight navigable WEATHER bottom modes, original seismic/recent-event visual contents, original runtime/source rack, existing five provider source gates and one root source instance.
- Original M28-F (weather source controls), M2a (source owners), W1/W1r navigation, M28-R (terrestrial weather versus COSMOS), M28-N (SUBJECTS-first fallback), M28-L sources and navigator contracts rerun in dedicated `.github/workflows/weather-ground-full-visual-parity-m28q.yml`. Existing relevant GitHub workflows run on source changes.
- Automated QML/source validation **does not mean** the user has verified actual monitor layout, scroll/pointer, source freshness or visual clarity. The operator is independently fixing feed availability.

## WATCH OUT FOR

- M28-Q is a **visual parity** route, not a declaration that every original source is online. Blank lightning radar, river hydrographs, recent seismic and weather status are valid original unavailable states.
- The original GROUND includes worldwide seismic events, which are geographically an EARTH subject in the new taxonomy. The preserved full GROUND view is a **temporary migration-completeness reference** under WEATHER, not a relocation of EARTH's canonical USGS map and inspectors.
- It reuses original `WeatherStationW` and `StationGround` services; no second river/lightning/seismic actor is instantiated. Full GROUND activates original page-specific sources while visible, like CLASSIC. The page can be long, so actual desktop scrolling/performance must be checked.
- The WEATHER bottom rail now displays eight fixed equal-width buttons. Accept their temporary compactness rather than redesign during the operator's ongoing feed repairs.
- Existing CLASSIC service behavior, local caches, event/dossier archive, and State Director/Kitty lifecycle must remain unaltered. No local shell restart or filesystem edits are authorized by this GitHub work.
- Do not infer global GROUND data correctness from route/section coverage. User acceptance remains separate.

## CHECKLIST

- [x] Read current Syntagma AGENTS and Hospital protocols.
- [x] Check current main / open Weather PR ownership before changes.
- [x] Identify all 16 original GROUND sections and the three nonidentical destinations.
- [x] Add one full native GROUND route without duplicating the renderer.
- [x] Expose it from the existing WEATHER bottom row and INDEX.
- [x] Restore original shared seismic activation only while the route is active.
- [x] Preserve river, lightning, marine/coastal and other existing source gates.
- [x] Add section-level / navigation / source-lifetime regression and CI.
- [ ] Final PR head CI, fix any assertions and verify shared-file collision absence.
- [ ] Merge bounded PR after passing final checks and checking authority.
- [ ] Local workstation compare, scrolling/performance and operator acceptance.
- [ ] Broader MAP/NEWS/RADIO visual migration before CLASSIC retirement.

## NEXT

On an authorized local update, compare the full WEATHER → GROUND view to CLASSIC GROUND. Treat blank feed data as a separate worker-owned problem. Continue other CLASSIC 1:1 presentation audits without redesign until all original visual elements are accessible in SUBJECTS and operator accepts their placement.

## DECISIONS

The operator explicitly requests **1:1 presentation now, redesign later**. Source and visual owners are reused. GROUND is a migration reference within WEATHER; original USGS event map remains EARTH. No local machine modification, production activation, new collector, CLASSIC removal or live Hospital registration is claimed.
