# Apollo Hub // Capability Levels and Recovery Contract (proposal)

**STATUS:** Operator direction recorded 2026-10-23; proposed architecture and recovery checklist, not completed implementation or final UI acceptance.  
**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**SCOPE:** ApolloHubW presentation, cross-widget read-only projections, and proposed bounded actions.  
**AUTHORITY:** Operator final. Syntagma `AGENTS.md` and relevant `OPERATE/` protocols govern staffing, ownership, local writes, merges and acceptance. GitHub source owns technical truth.  
**WORKER:** Replaceable external ChatGPT worker, Hospital-compatible; no live Room/Assignment/Session registration or inherited write ownership verified.  
**GIT BASE:** `41267d059da21c23b16e3ff64d3ad6474bae560a` at document creation. Recheck `main`, active PRs, ownership, and CI before any future edits.

## 1 // Operator intent, not an implemented feature claim

Apollo Hub is a customizable workspace for a useful selection of Post-Apollo modules. Each small card should ultimately offer **more than a passive snapshot** without becoming a copied full widget. Weather must be able to expose different domain information (weather, ground, sky, solar/space). TASKS' more advanced To-do and PLANNER should inform and eventually replace/supplement Hub's older task/calendar mini presentations without creating a second task store. Extend this pattern across Media, Apps, Network, CPU++, Notes, Time, etc., subject to each domain owner's contracts.

**Do not confuse two independent axes:**
- **Geometry:** W:1/W:2 columns and H:1/H:2/H:3 rows; existing layout v2 and Stage 6 packing.
- **Capability:** Level 1 information, Level 2 exploration, Level 3 bounded agency; a single H:1 tile can offer a view selector, while an H:3 Level 1 tile remains passive. These levels are an architectural proposal, **not** the already merged "Stage 7A/B/C" implementation stages, a new saved-layout version, a permission grant, or an automatic UI setting.

| Capability | Intended mechanism | Boundary |
| --- | --- | --- |
| Level 1 // DISPLAY | Owner-provided live snapshots and truthful freshness/error states | Existing Hub foundation; no duplicate service |
| Level 2 // EXPLORE | Mini-local view/domain selector over owner-provided data; height-aware content; stable mini tile | Prefer transient per-tile view selection first; no hidden fetch-on-switch, duplicate pollers, or pretend source readiness |
| Level 3 // OPERATE | Explicit user action handed to owning widget/service through typed validated action interface | No action until owner approves API/permissions; distinguish request, accepted, confirmed effect, failure and unavailable |

Level 3 is not a full copy of the parent widget. Full-size expansion within Hub vs launching another window remains an **operator-deferred** choice, separate from Level 3.

## 2 // Source evidence at recovery

- `widgets/ApolloHubW.qml`: customizable Dashboard/Console/Media modes, submodes, picker, MOVE/SWAP, W/H, in-session undo and stable saved layout; `services/hub/ApolloHubLayout.js` v2 remains canonical for packing and tile IDs.
- `services/hub/LAYOUT_EDITOR_V2_CONTRACT.md`: Stages 1–6 and 7A/B/C. Stage 7C calendar density source was handed off by commit `9764d1e9143cd843798631d75ff0224514f276f5`. Stage 7A keyboard and 7B/7C rendering still require desktop acceptance; source/CI success is not that acceptance.
- `widgets/hub/ApolloHubCalendarMini.qml` and `services/hub/ApolloHubCalendarPolicy.js`: local month grid, navigation, TODAY month-reset, Sunday/Monday toggle. **No connected appointment/event provider.**
- `widgets/tasks/TaskPlannerPane.qml` and `TaskPlannerPolicy.js`: TASKS PLANNER MONTH/WEEK/DAY/TODAY read-only calendar, dated-task agenda and OPEN-to-details. Merged PRs [#615](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/615), [#620](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/620), [#624](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/624). A new desktop verification of TODAY fix is separate.
- `widgets/TasksW.qml` and `widgets/hub/ApolloHubTodoMini.qml` consume the **single live `ApolloHubTodoStore.snapshot`**; `services/hub/ApolloHubTodoStore.qml` remains the live writer to `apollo-hub-todo-v1.json` (the filename does not mean the in-file model is necessarily schema v1). Proxy 1's M10f single-writer/journal project is **CI-only**, not activated production storage.
- `widgets/weather/WeatherStationW.qml` plus `StationGround.qml`, `StationSky.qml`, `StationSpace.qml` own GROUND / SKY / SPACE. GROUND has air/gas/pollen and a view-local seismic source; SKY has atmosphere/forecasts; SPACE has NOAA solar, geomagnetic, X-ray/aurora services. Some services are view-activated; **do not make each Hub tile instantiate those services**. See `docs/weather-station-backend-first-master-roadmap-20261023.md` for owning WeatherStation roadmap. That roadmap prioritizes backend/data correctness ahead of major visual rearrangement.
- `services/hub/ApolloHubLiveBridge.qml` currently consumes shared WeatherService weather/AQI and other existing system/network/media/app sources; **it is not already a complete GROUND/SKY/SPACE provider interface**.
- Current Hub Media mini is read-only. Do not synthesize playback commands from observation fields.

## 3 // Proposed owner-safe implementation sequence

1. **Finish existing checkpoint:** Recheck current `main` and test suites, then operator tests Stage 7A keyboard focus, 7B Time H:1/H:2/H:3, 7C Calendar H:1/H:2/H:3. Validate compact six-week month and view switching. Record outcomes, not inferred acceptance.
2. **Density-only increments:** Give one existing Hub mini at a time useful H:2/H:3 layouts with existing snapshots, without changing its service. Start with low-risk read-only tiles; Notes and To-do require careful draft/focus/save semantics. Each increment gets separate source/CI and desktop tests.
3. **Level 2 contract pilot (read-only):** Define per-tile `availableViews` / `selectedView` and projected data with truthfully unavailable states. Prototype transient per-tile view state indexed by stable tile ID; do **not** upgrade layout v2 or persist it without separate migration approval.
4. **TASKS/PLANNER seam:** Retain one TodoStore. Use the current TaskPlannerPolicy or an owner-approved compact read-only projection for Hub TODAY/MONTH/WEEK/DAY/AGENDA. Do **not** mount a second full TasksW, shadow a writer, or transplant its minute timer blindly. Route task opening to existing TASKS details only after focus/navigation contract is agreed.
5. **WeatherStation seam:** Coordinate with Weather owner to expose safe owner-published GROUND/SKY/SPACE summaries through the existing live bridge. Do not start new Seismic, Aurora, SolarFlare, Xray, or alert collectors per Hub tile; view activation and update cadence need explicit lifecycle agreement. Weather main views and shared Hi-Fi radio work remain Weather/Media-owned.
6. **Level 3 bounded actions:** Implement only individually approved commands (e.g., existing task mutation route, MPD control route, view navigation) with typed inputs, explicit user trigger, owner verification, availability/authorization and action-result feedback. Never equate "requested" with "completed".
7. **Expansion policy:** Prototype in-Hub expand/collapse only after mini controls and focus/persistence are accepted. Separate full-window launch remains open.
8. **Acceptance/handoff:** For each PR, record exact base/HEAD, changed paths, CI, desktop evidence, rollback, owner dependencies and operator decision. No merge or local Quickshell activation by this document.

## 4 // Dependency / ownership map

| Surface | Read or proposed change | Owning boundary |
| --- | --- | --- |
| Hub mini QML and layout | Hub-owned UI only | ApolloHubW worker; avoid simultaneous edits to `ApolloHubW.qml`, `ApolloHubTile.qml` |
| TASKS data and PLANNER | Shared snapshot; agenda projection | TASKS Proxy 1 storage, Proxy 2 PLANNER, TASKS host owner |
| Weather GROUND/SKY/SPACE | Owner-published projection | WeatherStation, weather services and lifecycle owner |
| Hi-Fi controls | Owner action bridge, never duplicate backend | Media/Hi-Fi owner |
| Shell and focus | Injection and window activation | Shared shell / Koinoikos focus owner; coordinated PR only |
| Layout persistence | Existing v2 schema and atomically guarded editing | Hub layout owner; a future new per-tile setting needs explicit migration design |

## 5 // Verification and recoverability checklist

- [x] Canonical Syntagma AGENTS and Hospital/working protocols inspected.
- [x] ApolloHubW, calendar, Time, layout and bridge source inspected.
- [x] TASKS current PLANNER + shared store path inspected.
- [x] WeatherStation GROUND/SKY/SPACE and owning backend-first roadmap inspected.
- [x] Last Hub calendar handoff `9764d1e` located.
- [ ] Verify latest Hub-specific workflow/test result against exact current commit and execute appropriate tests for new modifications.
- [ ] Operator desktop acceptance: Stage 7A keyboard; Stage 7B Time; Stage 7C Calendar.
- [ ] Confirm live Hospital Room/Assignment/role/owner metadata if connected; never infer registration.
- [ ] Build separately reviewed Level 2 read-only pilot.
- [ ] Decide whether/which Level 3 actions are authorized for initial proof-of-concept.
- [ ] Decide in-Hub vs separate-window expansion after hands-on testing.

## 6 // Recovery pointers and decisions

- Canonical existing Hub layout contract: [LAYOUT_EDITOR_V2_CONTRACT.md](../../services/hub/LAYOUT_EDITOR_V2_CONTRACT.md).
- Live UI: [ApolloHubW.qml](../../widgets/ApolloHubW.qml), [ApolloHubTile.qml](../../widgets/hub/ApolloHubTile.qml).
- TASKS: [TasksW.qml](../../widgets/TasksW.qml), [TaskPlannerPane.qml](../../widgets/tasks/TaskPlannerPane.qml).
- WeatherStation: [WeatherStationW.qml](../../widgets/weather/WeatherStationW.qml), [backend-first roadmap](../../docs/weather-station-backend-first-master-roadmap-20261023.md).
- Last Stage 7C code/handoff provenance: [commit `9764d1e`](https://github.com/kudokudo1/The-Post-Apollo-Project/commit/9764d1e9143cd843798631d75ff0224514f276f5).

**DECISIONS:** Adopt capability levels as a *proposed vocabulary* to organize future increments, preserve W/H geometry independently, reuse shared authoritative stores/services, keep narrow Hub surfaces instead of replicating whole apps. Operator controls acceptance and final action/expansion choices. This file grants no changes beyond its documented drafting PR.
