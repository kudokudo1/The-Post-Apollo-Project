# Weather Station // M28-K native HOME semantic routing parity

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Weather Station / CLASSIC → SUBJECTS full capability migration  
STAFF // External Hospital-compatible ChatGPT, no confirmed live Hospital registration  
ASSIGNMENT // Correct four historical HOME control destinations so deep INDEX opens the *original persistent HOME* QUICK/HISTORY workspaces instead of misleading WEATHER/COSMOS panels  
BASE // `main` `93b50fae18347fb4dd117bccdf9093b6a07830b9`  
PHASE // GitHub bounded source/route implementation and CI

## IMPLEMENTATION

Four original HOME source-control IDs still pointed, through M0's legacy `PANELS` metadata, at superficially similar but semantically incorrect WEATHER/COSMOS routes:

- `home-quick-conditions` pointed at SKY CURRENT (`weather/conditions/current`), which does not reproduce HOME QUICK's combined **humidity, wind, UV and Kp** cards.
- `home-space-weather` pointed at COSMOS SWPC overview, not HOME QUICK's compact original Kp card.
- `home-aqi-humidity` and `home-aqi-wind` pointed to general WEATHER history relations, not the original HOME AQI/HUMIDITY and AQI/WIND relationship cards, both present under HOME HISTORY.

W1 already owns a single original `StationHome` instance inside `StationWorkspaceSurface` with live `weatherService`, `spaceService`, `liveHistoryStore`, the original ranker and auto-watch timers. W1's real `home/quick` and `home/history` tab routes show exactly those original controls using `workspaceSection`.

M28-K retains **all original M0 `PANELS` historical hints unchanged**, maintaining the six-subject M0 navigation contract and source provenance. In `StationSubjectNavigationPreviewPolicy` it adds an exact, fail-closed `HOME_SOURCE_HINTS` → `HOME_NATIVE_ROUTES` audited override for these four source IDs only, and marks them `M28-K` in the `WIRED_IN_SUBJECTS` registry.

To make those native links actually clickable from header INDEX, `StationSubjectNavigator` now recognizes a **synthetic HOME index root** (not a fabricated seventh M0 SubjectRoutes node), lists W1's real HOME modes and provides functional `chooseRoute`, `selectSubject`, `openIndex` and keyboard cycling to those pages. `StationSubjectRail` includes HOME alongside the original six M0 deep-subject family buttons while preserving a single mode-button delegate and all existing original source owners. Clicking HOME/QUICK or HOME/HISTORY exits INDEX into the original HOME workspace, not CLASSIC or a cloned panel.

After M28-K, 100/103 exact historic source controls have recorded native SUBJECTS source wiring; only GROUND SOURCE, MAP SOURCE RACK and station-level SOURCE BADGE remain unreviewed. This does **not** certify final desktop parity or allow CLASSIC deletion yet.

## HOW TO USE

After merge and **separate** authorized local deployment: Weather Station → SUBJECTS → HOME. The usual left HOME rail and bottom QUICK/HISTORY controls already show the original cards. Alternatively from HOME use header **INDEX**, select HOME on the INDEX left rail, and open **HOME/QUICK** or **HOME/HISTORY** using the native routes. `WORKSPACE` restores the pre-INDEX workspace selection without opening CLASSIC.

Under HOME QUICK, verify live humidity, wind, UV and the compact Kp card; under HOME HISTORY verify AQI/humidity and AQI/wind trends as distinct relationship cards. No extra weather, NOAA, AQI or persistence collector is created.

## VERIFY

- New `tests/weather/test_index_home_cutover_m28k.js` verifies exact four M0 original ID hints and real W1 HOME routes, de-duplicated INDEX links, synthetic HOME root (M0 still six deep subjects), original `StationHome` actor and cards/history source, malformed source hint fail-closed, and exactly three still-unreviewed source controls.
- `.github/workflows/weather-subjects-home-parity-m28k.yml` runs M0/M1, W1/W1r, and all M28-D through M28-J regression contracts. Broad QML grammar and Weather navigation workflows also run based on changed file paths.
- Initial final-head CI: **pending at PR creation**. Native Quickshell pointer clicking, real Fedora/Wayland viewport correctness, realtime providers and operator acceptance have not been proven.

## WATCH OUT FOR

- HOME is one of seven *workspace* families but remains **outside the canonical M0 six-subject deep taxonomy**. Do not add a fake M0 subject or copy its source controls into WEATHER. The synthetic HOME INDEX root bridges both navigation layers cleanly.
- Original `StationHome` is shared, not cloned. The existing W1 workspace `Loader` may be inactive while INDEX is open; final workstation acceptance must test returning home without losing persistent data/time state unexpectedly.
- `HOME/QUICK` and `HOME/HISTORY` have real on-screen sections; their data presence depends on upstream weather/space/history providers and must not be silently invented.
- GROUND source health, MAP's source rack and station header source badge are broader than TOOLS' six core source-health rows. They remain pending and must not be marked migrated through name similarity.
- Embedded NEWS/VIDEO hosting is still blocked, despite catalog parity, and Stage Director/viewer work is independent.
- No local files, Quickshell process, Wayland compositor or production activation were modified.

## CHECKLIST

- [x] Inspect active GitHub main, source navigation and W1 HOME controls.
- [x] Correct four native HOME destinations while preserving M0 historical route hints.
- [x] Add real HOME INDEX navigation, breadcrumb, left-rail and keyboard selection support.
- [x] Avoid new watcher, FileView, process, terminal, weather collector or data writer.
- [x] Preserve exact earlier milestone evidence in tests, add focused CI and durable handoff.
- [ ] Verify final-head CI and narrow failures.
- [ ] Review/merge under operator's established GitHub workflow.
- [ ] Operator desktop tests HOME INDEX and original card continuity.
- [ ] Review remaining GROUND/MAP/STATION source rack and header badge parity.
- [ ] Full original CLASSIC loader/dependency teardown and explicit final acceptance.

## NEXT

After CI and merge, M28-L should verify original GROUND source summary, MAP source rack and station header badge against TOOLS source-health/provenance and the actual provider-state badges. If missing, transfer their real functional breadth rather than masking missing sources. Only after accepted coverage, audit and delete the original CLASSIC loader, related views, toggle, legacy bridge and dead source fallback, preserving shared services, caches, history, terminal actor and pending Stage Director integration.

## DECISIONS

Keep seven workspace families and six M0 deep subjects distinct; no duplicate rendering or network owner, no unapproved auto-refresh/autosave, no local machine modifications, no claims of working video or live Hospital attachment, no early CLASSIC deletion and no final acceptance claim without operator verification.
