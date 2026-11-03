# Weather Station // M28-I TOOLS provenance and store cutover

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Weather Station / CLASSIC → SUBJECTS full capability migration  
STAFF // External Hospital-compatible ChatGPT (no confirmed live Hospital attachment)  
ASSIGNMENT // Transfer original SPACE sample clocks into TOOLS and verify existing source-health/storage views before retiring their CLASSIC shortcuts  
BASE // `main` `b599607ed456df293e2dd17b2f453d00751c0935`  
PHASE // GitHub review and regression verification

## IMPLEMENTATION

Twenty historical source mappings remained after M28-H. The real `StationToolsSubjectPane` already displayed `SourceHealth.buildCoreSources` (the same 6 core sources as HOME's health rack), real last-known persistent cache, bounded live-observation history, event-archive and dossier-archive status, plus a frame-retention **contract catalogue**. It had a gap: `tools/sources/provenance` showed the 37 declared runtime source specifications, **not** the four original NOAA *live sample clocks* in CLASSIC SPACE.

M28-I resolves the real gap, rather than simply marking a route as migrated:

- Adds pure `StationToolsSubjectPanelPolicy.fieldTimeRows(spaceService,nowMs)` over the **same original four SpaceService fields**: Kp (`kpTime`), solar wind (`solarWindTime`), IMF (`magneticFieldTime`), F10.7 (`solarFluxTime`). No new HTTP request, timeout, SpaceService instance, or sensor store.
- Under `TOOLS → SOURCES → PROVENANCE`, renders those four sample clocks with actual provider time, sample age and status, original freshness windows, and *separate last successful network receipt time*. Missing/malformed/future dates remain `TIME UNVERIFIED` or `NO SAMPLE`; a fresh receipt must not relabel a stale sample as current. The 37 static source specifications stay clearly labeled as a separate inventory.
- Reconciles exactly six existing native TOOLS mappings in `WIRED_IN_SUBJECTS`: `home-source-health`, `space-field-times`, `station-frame-cache`, `station-persistent-cache`, `station-live-history`, `station-event-store`.
- Preserves old M1 `sourcePagesForPath` provenance, M28-D native-link logic, and CLASSIC shortcuts for all not-yet-reviewed controls.
- Original archive writes and persistent stores remain owned by the root/Weather services. This is **read-only** status and sample timing, not file reading or archive CRUD. `FRAME CACHE` means a temporary retention-policy inventory, not an existing persistent frame archive.

Current classification after this patch: 89 of 103 historical controls have verified *source wiring*; 14 still pending review or runtime acceptance. Classification is not proof of final operator desktop acceptance.

## HOW TO USE

After GitHub merge and separately approved local deployment: Weather Station → SUBJECTS → TOOLS → SOURCES → PROVENANCE. Actual NOAA Kp/WIND/IMF/FLUX provider sample times appear above the static source catalogue, with freshness status and distinct last receipt times.

TOOLS → SOURCES → HEALTH keeps the original 6 core source readouts; TOOLS → STORAGE → CACHE / HISTORY / EVENTS show original store state, revision, record/series counts (where available). TOOLS → STORAGE → FRAMES displays **frame retention contracts**, not a fabricated saved-frame archive. Header INDEX routes the six reviewed origins directly into those panels.

## VERIFY

- New `tests/weather/test_index_tools_cutover_m28i.js` verifies exact six mapped IDs, known native leaves, original 4 sample fields and clock/receipt separation, stale despite new receipt, missing/bad/future fail closed, same HOME six-core health policy, shared store metadata, no new writer or second terminal actor, preservation of pending source racks and WATCH.
- New `.github/workflows/weather-subjects-tools-parity-m28i.yml` runs original TOOLS T1, M28-D/E/F/G/H, browser M0/M1 and W1/W1r regressions.
- Earlier M28-F/G/H tests retain exact milestone counts but no longer assert that now-reviewed `space-field-times`, `home-source-health`, or `station-event-store` must remain unreviewed.
- Initial exact-head CI: **pending at PR creation**. No live Fedora/Quickshell UI, provider connectivity, hosted video or operator acceptance claimed.

## WATCH OUT FOR

- `ground-source`, `map-source-rack`, `station-source-badge` are **not** certified as migrated. They may cover broader provider selections and header display than the six core health rows; reusing the word SOURCE does not prove parity.
- `home-quick-conditions` currently points to WEATHER/CURRENT rather than the original HOME QUICK instrument; the original `home/quick` workspace exists and should be reconciled in the next bounded review.
- `home-aqi-humidity` and `home-aqi-wind` map to general WEATHER history relationships, and `home-space-weather` is cross-domain. Verify their exact original panels and data flow before removing CLASSIC.
- MEDIA WATCH has explicit disabled video-hosting controls even though the publisher catalogue exists. CREATORS has an explicit upload-check and saved creators. Do not call video playback integrated merely because a route or button exists.
- Frame products and cache state do not imply a new archive. Health source time is not an emergency alert targeting fix. No local Sway/Kitty, MPD, persistent disk or live workflow changed.

## CHECKLIST

- [x] Recheck live GitHub main, open PRs and code ownership.
- [x] Audit 20 remaining mappings against real HOME/TOOLS/MEDIA implementations.
- [x] Expose actual four NOAA sample clocks, state, age and network receipt separately.
- [x] Account for six exact existing TOOLS/health/storage controls.
- [x] Preserve unresolved CLASSIC controls and event/archive ownership.
- [x] Add regression tests/workflow and durable handoff.
- [ ] Verify final-head CI and fix bounded failures.
- [ ] Review/merge, deploy separately, and run actual Fedora/Quickshell acceptance.
- [ ] Continue remaining 14 control reviews and full CLASSIC dependency audit.
- [ ] Obtain operator final sign-off before removing CLASSIC loader and buttons.

## NEXT

Upon clean CI and merge, proceed to HOME QUICK/HISTORY and semantic mapping, and then MEDIA WATCH/CREATORS. Keep WATCH's disabled video host explicit and preserve in-station navigation first. A future final CLASSIC cutover must audit original collectors, terminal, timers, caches, persistence and shared service lifetimes before deletion.

## DECISIONS

Maintain seven-family SUBJECTS; reuse existing original services/store/controller and their data, no duplicated writer or automatic save, no local workstation writes, no silent video-hosting claim, no premature CLASSIC deletion, no live Hospital role claim. GitHub tests are technical evidence, not operator acceptance.
