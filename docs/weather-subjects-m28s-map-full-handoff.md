# M28-S // MAP full original presentation inside SUBJECTS

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Weather Station CLASSIC → SUBJECTS 1:1 visual migration  
ASSIGNMENT // Keep the exact original CLASSIC MAP presentation accessible in SUBJECTS; postpone redesign  
STAFF // External Hospital-compatible Doctor · OPEN AI // CHATGPT · no verified live Hospital registration  
BASE // GitHub main `ef989d86d3cd43dfa6e8a8993941d7c9a4e46b14` at branch creation  
AUTHORITY // User requested continue the 1:1 original visual migration, not data-feed fixes, styling or local changes

## IMPLEMENTATION

**Existing state:** Original CLASSIC MAP is the `StationDiscovery.qml` component with `domain: "map"`, `weatherMapOnly: false`, `earthMapOnly: false`. It shows the local Natural Earth map, provider-native events (USGS, EONET, GDACS and manually requested FIRMS), MRMS/RainViewer radar, HMS smoke, zoom/pan, original source rack, news-mention context and event inspectors in one scrollable surface. The native SUBJECTS routes currently filter that original map into EARTH-only events and WEATHER radar/smoke. M0 mapped the controls individually but never offered the complete original MAP presentation.

**New additive full route:** `earth/maps/full`, accessible from **SUBJECTS → EARTH → MAP // ALL** in the bottom row, and INDEX → EARTH → MAPS → MAP // ALL ORIGINAL INSTRUMENTS. It loads the *same* `StationDiscovery.qml` via the *same* single `StationEarthSubjectPane` Loader. For the **exact** new full route alone, `earthMapOnly` is false, recovering the original CLASSIC display and manually controlled layers. Every other EARTH route retains `earthMapOnly=true` and the original native source-layer filters; focused WEATHER radar remains independent.

The 10 pre-existing EARTH routes remain, now plus one full route (11); the bottom EARTH row grows from seven to eight temporarily. The historical 103 control destination ledger is unchanged, including `map-spatial-canvas → earth/maps/overview`.

**Original source owners:** The same global `WeatherStationW` `SeismicService`, `NowcoastLightningService` and `NwpsRiverService` are reused, with root lightning and river admission extended **only** to the new `earth/maps/full` route. Original `StationDiscovery` handles EONET, GDACS, manual FIRMS, HMS smoke and radar source lifetimes. No new provider, timer, writable store, file, terminal actor, renderer, or map-event identity is created. Existing explicit save/archive/dossier actions are untouched.

## HOW TO USE

After GitHub merger and a separately authorized local update, open Weather Station → **SUBJECTS → EARTH**. Select the bottom **MAP // ALL** mode and scroll the exact CLASSIC map controls, overlays, radar panels, source rack, event evidence and action affordances. The detailed **MAPS**, **GEOLOGY**, **EVENTS**, **FIRES**, and **DOSSIERS** modes remain available. INDEX offers the same full route, and CLASSIC → MAP remains as comparison fallback.

The full map may still report missing or stale source data, exactly as the original CLASSIC panel would. Another worker owns data-feed repairs; do not replace unavailable provider records with fabricated examples.

## VERIFY

- `tests/weather/test_map_full_visual_parity_m28s.js` checks complete MAP mode, 11 native EARTH routes, exact sole source `StationDiscovery`, unfiltered full route vs ten filtered EARTH routes, original map controls and manual dossiers, same root provider ownership, route admission, Earth/Weather separation, original 103-control provenance, and eight clickable bottom routes.
- Original `tests/weather/test_earth_subject_panels_e1.js`, `tests/weather/test_index_earth_cutover_m28h.js`, `tests/weather/test_workspace_landing_w1.js` are updated only where legacy counts or assumptions require it.
- Dedicated `.github/workflows/weather-map-full-visual-parity-m28s.yml` plus all applicable GitHub PR checks; source-based verification does not prove local render/pointer behavior, actual image loading, refresh success or final operator acceptance.

## WATCH OUT FOR

- The full original MAP blends Earth events with terrestrial atmospheric overlays and news context. This is an **explicit temporary 1:1 migration reference**, not a decision that all those categories belong permanently under EARTH. Focused, correctly classified WEATHER and EARTH routes remain unchanged.
- FIRMS/HMS and archive/dossier operations remain explicit/manual, not newly scheduled. Preserve source provenance and no surprise writes.
- The new eighth EARTH button is temporarily tighter; restyling is deferred by the operator.
- No local file writes, git pull, Quickshell restart, service activation or CLASSIC deletion authorized here. Avoid merging if concurrent workers change the same files before final verification.
- WATCH video/Stage Director is a distinct blocked capability; do not infer working media playback from this migration.

## CHECKLIST

- [x] Verify latest source and Syntagma/Hospital authority.
- [x] Trace CLASSIC `StationDiscovery` and EARTH filtered route source ownership.
- [x] Add exactly one complete original MAP route with no duplicate actors.
- [x] Preserve original ten EARTH routes, old map/source provenance and CLASSIC.
- [x] Add complete-map navigation/rendering/provider tests and workflow.
- [ ] Final head CI green, recheck merge ownership and merge bounded PR.
- [ ] Operator native screenshot/scroll/zoom/pan acceptance.
- [ ] Preserve 1:1 NEWS and RADIO presentations with independent tests.
- [ ] Later separately authorize redesign and/or CLASSIC retirement.

## NEXT

Continue M28-T to expose original CLASSIC NEWS and RADIO as complete native MEDIA pages, while preserving their existing channel catalog, GDELT report UI, favorite/recents, playback transport and video safe mode without claiming streaming works. Then inspect other omitted legacy presentations before retirement.

## DECISIONS

The user prefers **1:1 now, styling later**. Preserve source owners and original presentation, even when it mixes categories. No activation, data repair, playback-engine change, user-approved final visual acceptance, or live Hospital registration is claimed.
