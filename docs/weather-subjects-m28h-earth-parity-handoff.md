# Weather Station // M28-H EARTH event and dossier source parity

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Weather Station / CLASSIC → SUBJECTS full capability migration  
DOCTOR // External Hospital-compatible ChatGPT  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL; no confirmed live Hospital attachment  
ASSIGNMENT // Reconcile all fourteen original Earth-facing GROUND/MAP event, inspector and dossier controls to existing EARTH subject routes  
BASE // `main` `06d78a23283090acf355d2ac1015f6bad9791efe`

## IMPLEMENTATION

EARTH E1, M26-F and M28-A/B already provide `StationEarthSubjectPane` with one route-filtered `StationDiscovery` map instance, using the original USGS, EONET, GDACS, manually requested FIRMS products, Natural Earth local basemap, source-specific inspector state, selected event context, and the shared manual `eventArchiveStore` / `dossierArchiveStore`. The original CLASSIC MAP loader is deactivated while SUBJECTS is active.

M28-H marks fourteen exact original GROUND/MAP source controls as **wired to EARTH**:
- USGS seismic summary/marker/inspector → `earth/geology/earthquakes`.
- Natural Earth local basemap → `earth/geography/basemap`.
- Spatial map canvas → `earth/maps/overview`.
- NASA EONET source markers and inspector → `earth/events/eonet`.
- GDACS source markers and inspector → `earth/events/gdacs`.
- NASA FIRMS manually requested hotspots/inspector → `earth/fires/hotspots`.
- Event cross-domain context, manual dossier preview and manual archive → `earth/investigations/context`, `dossiers`, `archive`.

Nine unique native EARTH leaf destinations replace redundant INDEX CLASSIC jump buttons for these exact reviewed source IDs. The original M1 historic `sourcePagesForPath` still describes their GROUND/MAP provenance. Existing M28-A NEWS → EARTH magenta mentioned locations remain separate transient **article mentions**, never promoted into USGS/GDACS/EONET/FIRMS provider events. Dossier and event archive writes remain explicit and are not activated by selecting a route or marking a source as wired.

M28-D/F/G earlier tests are adjusted to preserve their exact milestone proofs while accepting later independent EARTH migration. No other provider, timer, store, compositor actor, or original MAP logic changes.

Current ledger after M28-H: 83/103 exact historical source controls have repo-verified native SUBJECTS wiring. **20 remain unreviewed**. This is not a statement that the 83 have been accepted on the operator's live desktop.

## HOW TO USE

After GitHub merge and separate local deployment: Weather Station → SUBJECTS → EARTH. Use GEOLOGY, EVENTS, FIRES, MAPS and DOSSIERS submodes, or header INDEX to choose direct EARTH source destinations. Selecting an actual provider event opens the original source inspector/context; manual capture and archive actions are still separate user-controlled steps. EARTH → MAPS also displays the compact M28-B EONET events-in-view tray and selected MEDIA article mentioned places when supplied.

## VERIFY

- `tests/weather/test_index_earth_cutover_m28h.js`: exact fourteen source IDs, real canonical leaf route ownership, E1 map layer and source admission, one persistent EARTH renderer, existing manual event/dossier admission, no automatic provider or archive duplication, preservation of historic origin and pending unrelated controls.
- New `.github/workflows/weather-subjects-earth-parity-m28h.yml` reruns E1, M26-F, M28-A/B, M0/M1 and M28-D/E/F/G regressions.
- **CI status pending at PR creation.** Source tests do not certify user workstation map interaction, provider live availability or permission to delete CLASSIC.

## WATCH OUT FOR

- FIRMS and NOAA HMS source data remain explicitly manually requested; entering EARTH is not a request to fetch or archive all imagery.
- NASA EONET, GDACS, USGS and FIRMS have independent identities and cannot be conflated with GKG article mentioned places.
- Exact selection state and manual dossier save must remain in the one original `StationDiscovery`; do not copy UI into another source owner.
- All other HOME QUICK, TOOLS SOURCE/STORE, MEDIA WATCH/CREATOR and other remaining controls require separate parity review. MAGICK visual/ephemeris and shared Places source work are separate owners.
- No local QML deployment, Quickshell restart, Sway control or operator desktop acceptance has occurred.

## CHECKLIST

- [x] Verify latest GitHub and absence of active conflicting Weather UI PR.
- [x] Inventory exact fourteen original Earth event/dossier source IDs and existing E1 routes.
- [x] Preserve event selection, manual dossier and archive ownership with no duplicate collector.
- [x] Reconcile historical tests to allow separately verified milestones.
- [x] Add focused tests, workflow and this handoff.
- [ ] Inspect exact-head CI and repair only bounded failure.
- [ ] Review/merge and separate operator desktop update.
- [ ] Verify real map selection, manual archives and source provenance on Fedora.
- [ ] Finish remaining 20 historical controls, dependency audit and final CLASSIC retirement acceptance.

## NEXT

Check CI then merge on green under the established operator repository workflow. Begin M28-I by reviewing the 20 remaining original source mappings, especially HOME QUICK and relationship semantics, TOOLS provenance/cache, MEDIA WATCH/CREATORS and source badge. Do not treat a future-feature placeholder as an existing CLASSIC capability.

## DECISIONS

SUBJECTS-first seven-family architecture, exact source-owner preservation, one EARTH map renderer and original stores, no unapproved automatic capture, no live desktop mutation and no final CLASSIC deletion before complete parity/acceptance.
