# Weather Station // M28-L last three source-control parity mappings

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Weather Station / CLASSIC → SUBJECTS capability migration  
STAFF // External Hospital-compatible ChatGPT (no registered live Hospital connection)  
ASSIGNMENT // Reconcile GROUND SOURCE, MAP SOURCE RACK and the global header SOURCE BADGE  
BASE // `main` `ea249bfe9954cefab564f073a2298acfbb7b6dd3`  
PHASE // Bounded GitHub source implementation; CI and operator acceptance distinct

## IMPLEMENTATION

M28-K left three historical `StationSubjectNavigationPolicy.PANELS` mappings unreviewed. They all have the original target `tools/sources/health`; M28-L keeps those M0 historical hints unchanged, while extending actual SOURCE behavior.

1. **GROUND SOURCE** (original `StationGround`): `StationToolsSubjectPanelPolicy.groundSourceRows` now reads exact `WeatherService.latitude`, `longitude`, `aqiReady` and `airQualitySourceTime`. The TOOLS → SOURCES → HEALTH panel renders **POSITION // WEATHER FIX** and **AIR QUALITY // SAMPLE**, clearly identifying the provider/weather fix as *not device GPS* and the Open-Meteo sample clock as *not the network receipt*. Coordinates fail closed on missing, non-finite or out-of-range input. No location mutation or collector.
2. **MAP SOURCE RACK** (original `StationDiscovery.plannedSources`): TOOLS → SOURCES → HEALTH adds actual in-station buttons to **EARTH → MAPS → OVERVIEW** and **WEATHER → MAPS**, preserving source ownership in the original `StationDiscovery` map instances. EARTH lists Natural Earth, USGS, NASA EONET, GDACS, keyed/manual NASA FIRMS and NOAA HMS. WEATHER now also *shows* its existing separate original SOURCE RACK with NOAA MRMS, RainViewer fallback, Natural Earth and HMS state. No attempt to present the 37 static runtime-source contracts as live provider availability, or merge independent event and radar sources into one fake poller. The existing `StationRuntimeRack` is visible for both map families and preserves the original current provider times and staleness vocabulary.
3. **GLOBAL SOURCE BADGE** (original root `WeatherStationW`): The header's existing badge remains the **only badge actor**, retains NWS official-alert priority, 30-second status clock, foreground/border/glow semantics and CLASSIC behavior. During SUBJECTS it now uses `StationSubjectSourceBadgePolicy` over the single root Weather/Space runtime states and the active original map's `runtimeRows` via `StationEarthSubjectPane` / `StationWeatherSubjectPane` → `StationWorkspaceSurface` → `StationSubjectNavigator`. WEATHER/COSMOS/HOME distinguish LIVE/AGING/STALE/CACHE/EXPIRED/OFFLINE; the actual EARTH and WEATHER map runtime summary distinguishes READY/STALE/CACHED/READING/OFFLINE. MEDIA catalogue, MAGICK reference, TOOLS source and detailed INDEX are explicitly **not** relabeled as live weather sources. The badge remains a read-only indicator, not an invisible action button.

After this patch, exactly **103 of 103 historical M0 source-control IDs** have evidence-linked SUBJECTS routes. The previous M28-D through K milestone assertions are updated to retain their exact historical milestone counts without freezing the final total. M0 historical page/source provenance is intact and no original service, timer, persistent store, radio, terminal or source controller has been removed.

**Important:** 103/103 is a source-wiring and INDEX migration ledger, *not* an overall functional parity score or final user acceptance. WATCH/NEWS embedded video remains intentionally disabled due to the earlier in-process QtWebEngine SIGABRT; Stage Director isolated viewer work remains separate. CLASSIC deletion and final live user acceptance remain separate milestones.

## HOW TO USE

After GitHub merge and a separately authorized local Fedora update:

- **SUBJECTS → TOOLS → SOURCES → HEALTH**: see original six core products, weather-fix coordinates, independent Open-Meteo sample timestamp, and two clickable source-rack destinations.
- **EARTH → MAPS → OVERVIEW**: inspect original provider-native USGS/EONET/GDACS events, FIRMS key/manual state, HMS status and source freshness rack.
- **WEATHER → MAPS**: inspect the original MRMS/RainViewer/HMS manual sources, visible SOURCE RACK and runtime freshness summaries.
- The header badge reflects the active family/loaded original map. Official NWS alert badges retain precedence. **INDEX** shows `INDEX // PREVIEW` instead of misreporting a hidden source as live.

These controls navigate within the station; they do not launch an external browser or background provider fetch by themselves.

## VERIFY

- New `tests/weather/test_index_sources_cutover_m28l.js`: exact three original M0 IDs, 103/103 ledger, unchanged source provenance, GROUND fix and AQI sample fail-closed, both source-rack ActionButtons and existing map UI, actual loaded map runtime chain, live/stale/cache/offline badge state with operator-alert precedence, no extra file/network/terminal owner, CLASSIC and safe-mode video not removed.
- Dedicated `.github/workflows/weather-subjects-source-parity-m28l.yml`: new proof + Weather runtime/health/map/TOOLS tests + all M28-D-K tests + M0/M1/W1/W1r.
- Other existing native QML/Quickshell checks are expected to trigger on the shared source files.
- **Final-head CI pending at PR creation.** This checkpoint is not proof that the operator's local Quickshell instance was updated, that all event endpoints are online, or that any map pointer interaction has been accepted on their desktop.

## WATCH OUT FOR

- Original MAP source family is intentionally split: EARTH event providers and WEATHER meteorological/radar providers are distinct. Their source racks belong to the original map controllers. Buttons must open existing loaded native map routes rather than instantiate another map.
- The header's data-driven status should not mistake stale NOAA observations for fresh network receipts, or disabled source collectors for working streams. In INDEX it reports PREVIEW, and MEDIA/WATCH still does not mean working video.
- `WeatherService` weather-fix coordinates are not device GPS, saved settings location or official NWS alert-point identity.
- EONET/GDACS/USGS event records and ephemeral GKG article location mentions remain separate. FIRMS/HMS/MRMS/RainViewer are operator-driven, not auto-archive or implicit fetches.
- The single original HOME source watcher, source caches, event/dossier stores, stage director/viewer boundary, source lifetimes, station terminal and Sway window containment still require full pre-retirement dependency audit and operator acceptance.
- **No local** Fedora config, git worktree, Quickshell restart, Sway process, Qt WebEngine, user saved records or live Hospital room has been changed.

## CHECKLIST

- [x] Read Syntagma authority and Hospital protocol; recheck `main` and active PR ownership.
- [x] Inspect original GROUND source, MAP source racks, Station header badge and TOOLS projections.
- [x] Implement provider-weather fix + AQI source timestamp with no new ownership.
- [x] Connect click-through map-source rack in both native map families.
- [x] Rebind header status to real original source snapshots, preserve official alerts.
- [x] Mark final three reviewed ledger IDs and preserve M0 historic source map.
- [x] Add focused tests, workflow and durable handoff.
- [ ] Repair bounded CI failures and verify exact final head.
- [ ] Merge only with all required GitHub checks green and no ownership collisions.
- [ ] Separately deploy and visually verify live Fedora/Quickshell pointer, banner, status and source timing.
- [ ] Perform full CLASSIC dependency/inventory/teardown rehearsal with explicit operator acceptance.

## NEXT

Complete M28-L CI, merge if clean, then perform **M28-M CLASSIC Retirement Readiness** as a read-only inventory and reversible removal proposal: locate every legacy loader, M0 index provenance consumer, source collector, cache, archive, terminal, radio and viewer ownership/lifetime dependency, and separately track live-player containment and local runtime acceptance. **Do not actually remove CLASSIC** until the operator approves that destructive next stage after verification.

## DECISIONS

User final authority; no live Hospital registration claim; repository changes remain bounded and recoverable; no local machine writes; no duplicate data owners; existing source-time and cache authenticity; no silent video-engine activation; no premature CLASSIC retirement or final DONE label.
