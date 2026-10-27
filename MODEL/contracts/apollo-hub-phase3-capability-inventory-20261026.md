# ApolloHubW // Phase 3 capability inventory and integration gaps

**STATUS:** Source-backed implementation inventory / proposed next work, **not a new canonical rule**, implementation authorization, Hospital assignment, or desktop certification.  
**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Source baseline:** GitHub `main` `b44a16826c111adb202e50c090009deff066c5dd` (2026-10-26). Recheck HEAD/ownership before using this to implement anything.  
**Operator observation:** 2026-10-26: "all existing controls and mini widgets seem to work". Record as broad positive **operator smoke feedback**, not individual lifecycle/data-safety acceptance for every control.  
**Scope of this inventory:** System Audio, AppControl, TimeW, TASKS; Hub capability/geometry/state invariants and next gaps.  
**Phase 3 TODAY implementation update:** 2026-10-26, `ApolloHubTodoExplore.qml` mounts canonical `TaskTodayPane` in H:2/H:3 with safe OPEN-to-details, no new writer. Source contracts and repository validation passed at `5b4c77218c8505fdd796d8c215a6724eff839434`. Live desktop acceptance remains pending.  
**Phase 3 PLANNER implementation update:** 2026-10-26, the expanded Hub To-do also reuses `TaskPlannerPane` with `schedulingAllowed: false` and no writer handle, adding read-only MONTH/WEEK/DAY/TODAY and agenda OPEN. The standalone TASKS pane retains its default scheduling actions. Integration contracts and repository validation passed at `cf76bec5aa1c6ebd4905ff0c1ae0f10182e70b10`; real H:2/H:3, scroll, selected-date and draft-continuity acceptance remain pending.  
**Canonical context:** [capability levels proposal](apollo-hub-capability-levels-v0.md), [layout v2](../../services/hub/LAYOUT_EDITOR_V2_CONTRACT.md), [B11 acceptance](../../services/hub/INTEGRATION_ACCEPTANCE.md), Syntagma `AGENTS.md`. No local device, branch, service, or persistence changes were made by this inventory.

## 1. Shared semantics

- **Geometry:** W:1/W:2, H:1/H:2/H:3 changes room available, not authorization or functional scope. The existing v2 layout stores tile identity/geometry, not durable drafts, active PID targets, process ownership, or audio-stream identity.
- **Capability (proposed vocabulary, independent of size):** L1 observe → L2 explore → L3 explicit owner-routed action. STATUS / CONTROL / DETAILS / SETTINGS are potential internal tabs, **not approved new global UI structure**.
- **Action-result phases:** `unavailable`, `observed`, `requested`, `revalidating`, `accepted`, `pending`, `applied/observed`, `failed/refused` must not be collapsed. A call returning true is not proof that the intended OS/user outcome happened.
- **Lifecycle:** Switching views, resizing tiles or moving between groups must not silently drop dirty drafts, replace an action's original target, launch an app, run an owner operation, create new polling instances, or turn a request into an assumed success.
- **Authority:** Hub presents controls and typed requests. The original widget/service owns underlying state, target semantics, validation, execution and observed effects. Source tests ≠ live Fedora acceptance. A ChatGPT session ≠ registered Hospital Room.

## 2. System Audio // parent and Hub

**Parent/owner files:** `modules/Volumebar.qml`, `services/audio/ApplicationAudioService.qml`, `services/audio/TEAM6_CROSS_TEAM_SEAMS.md`.  
**Hub/host files:** `widgets/hub/ApolloHubAudioMini.qml`, `widgets/hub/ApolloHubAudioStreams.qml`, `services/hub/ApolloHubAudioStreamGate.qml`, `services/hub/ApolloHubAudioStreamsPolicy.js`, `widgets/ApolloHubW.qml`, `shell.qml`.

| Capability | Parent/owner present | Hub at inspected HEAD | Classification / next boundary |
| --- | --- | --- | --- |
| Default output sink name, volume, mute | Existing dock uses `Pipewire.defaultAudioSink` | Shared `hubOutputSnapshot`; H:1 quick +/-5%, mute; H:2/3 master slider & APPLY | **Implemented owner-routed**. Confirm requested vs observed state and focus across resizing. |
| Per-stream discovery and details | Team 6 `ApplicationAudioService.sinkInputs`, generation, error/loading | STREAMS panel, explicit refresh, list, details | **Implemented bounded observation**; transient stream index/fingerprint is not canonical APP/WINDOW/TAB identity. |
| Per-stream mute/volume | Team 6 `setSinkInputMute`/`setSinkInputVolumes` | Gate rechecks generation + exact identity before invoking owner | **Implemented guarded request**; returned `REQUEST SENT // ACTUAL RESULT UNVERIFIED` is truthful; effect verification is outstanding. |
| Output device selection / routing | Not provided by current Hub master-output adapter | **Not wired** | Requires owner-published device list, identity, availability and explicit route-result contract. Do not interpret current default sink snapshot as a selector. |
| Persistent APP/WINDOW/TAB audio policies | Team 6 supports descriptor-matched mute/volume policies | Hub exposes raw stream controls, not full semantic scope | **Owner-dependent** on Team 7 identity and serialized host slot. Do not turn sink-input index into persistent application ID. |
| Hi-Fi playback | Separate Media/MPD/MPRIS ownership | Outside System Audio | **Keep separate** unless Media owner explicitly publishes transport actions. |

**Owner/acceptance caution:** `shell.qml` at baseline mounts one `ApplicationAudioService` and `ApolloHubAudioStreamGate`, but still contains a T3/Team 6 acceptance warning. Reconcile this ownership/host seam before changing lifetime or donor audio wiring. No new audio process or PipeWire tracker inside Hub tiles.

## 3. AppControl // parent and Hub

**Parent owner:** `widgets/AppControlW.qml` (nine modes: FAVORITES, APPS, FILES, RUN, WINDOWS, REMOTE, THERMAL, KILL, SYSTEM). Supporting owners include `widgets/appcontrol/TaskManagerView.qml`, `HunterControls.qml`, `SystemMonitorView.qml`, `ThermalMonitorView.qml`, `AppControlHubActionGate.qml`, `services/system/ProcessTelemetry.qml`, `ProcessControl.qml`, `ProcessLimits.qml`.  
**Hub:** `widgets/hub/ApolloHubAppsExplore.qml`, `ApolloHubProcessesExplore.qml`, `services/hub/ApolloHubProcessesPolicy.js`.

| Parent capability family | Source-backed parent scope | Hub capability | Next boundary |
| --- | --- | --- | --- |
| FAVORITES | Favorite entries, categories, controls | No equivalent full favorites workspace | Owner-backed identity and persistence API before Hub editing. |
| APPS | Application sources/identities and details | Native app catalog, details, explicit launch | Distinguish installed entry ID from process/window/tab identity; scope safe actions separately. |
| FILES | Dedicated file-related mode/actions | Not in Hub | File operations require owner-enforced path/permission and destructive action contracts; not part of process controls. |
| RUN / processes | Telemetry, metric cards/graphs, task detail, CPU/MEM/RSS/threads/PID/uptime | Bounded 24-row projection and RUNNING detail | Extend observed metrics/graphs only through the existing ProcessTelemetry; no duplicate sampler. |
| RUN operations | Freeze/resume/end/restart, guarded memory limit | Direct controls in `ApolloHubProcessesExplore.qml` | **Implemented guarded owner requests**: preserve PID + startTicks + name and protected-process/unlock/reconfirm gates; re-observe result before claiming applied. |
| WINDOWS | Window/source records and actions | Only partial navigation/metadata | Identity and action semantics differ from PID operations; do not assume process kill equals close window. |
| REMOTE | Remote/transport controls | Not in Hub | Explicit host capability and safety model required. |
| THERMAL | Thermal/fan metrics and guarded fan actions | Hub CPU++ has utilization only | Owner-approved thermal snapshot and supported controls; avoid extra sampling and hazardous implicit fan changes. |
| KILL / HUNTER | Target filters, protected/all views, metric scoring, bulk guarded operations | Hub running per-target controls only | Bulk scope and confirmation need an independent contract; no synthetic Kill All button. |
| SYSTEM | System component metrics, actions, contributors | Hub CPU++ and Network share some readings, not entire SYSTEM control plane | Per-operation owner approval; no generic SYSTEM action bridge. |

**Identity and safety facts:** `AppControlHubActionGate` validates the exact live row and probes process birth time; it does not expose raw ProcessControl to Hub. A saved tile selection must not silently switch to whichever PID reused a row. `ApolloHubAppsExplore` can navigate to RUNNING but does not imply every APPS action is available there.

## 4. TimeW // parent and Hub

**Owner:** `widgets/TimeW.qml`; `services/time/StopwatchPolicy.js`, `CountdownPolicy.js`, `TimeArithmetic.py`, `TimeDifference.py`, `TimeZoneConverter.py`, `WorldClockPolicy.js`, `WorldZoneSearch.js` and dedicated Time Machine contracts.  
**Hub:** `ApolloHubTimeMini.qml`, `ApolloHubStopwatchControls.qml`, `ApolloHubCountdownControls.qml`, `ApolloHubTimePolicy.js`, `shell.qml`.

| Parent function | Hub at inspected HEAD | Gap / safe next move |
| --- | --- | --- |
| Local date/time, 12/24, seconds, UTC offset | Policy-backed Time tile driven by its existing 1s tick | Observe midnight/DST/visibility; format preference currently transient. |
| Stopwatch START/PAUSE/LAP/RESET, recent laps | Hub controls bound to `timewWindow.hubStopwatchSnapshot` and routed to same TimeW instance | **Implemented shared owner**; verify equivalent elapsed/lap state in both surfaces. |
| Up to 8 named countdowns: create, edit, select, start, pause, reset, remove | Hub controls bound to `hubCountdownSnapshot`; actions forwarded by stable timer ID | **Implemented shared owner**; ensure selection/draft is not silently replaced and edits wait for owner acknowledgment. |
| Time difference and arithmetic calculator | Parent methods `runTimeDifference` and `runTimeArithmetic` exist | **Not in Hub**; ideal pure compute/preview integration, no second stateful clock. |
| Time zone conversion, 12/24 input/output, country/zone search, world clock | Parent converter/world-zone search present | **Not in Hub**; reuse policies/catalog and existing permitted lookup, no duplicate expensive process. |
| Time Machine capture/markers/restore/revive | Parent has separate capture, selection and restore workflows | **Deliberately out of first Hub functional wave**; state-moving actions require their own evidence/approval/recovery boundary. |

TimeW stopwatch/countdown functionality already flows through the owner instance; **do not duplicate monotonic clocks, countdown journals, heartbeats or timer identities**. Distinguish the pure time-format adapter from the separate Date/Planner task domain.

**TimeW CALC/WORLD owner-seam audit (2026-10-26):** [source-backed boundary and proposed owner contract](apollo-hub-timew-owner-seam-audit-20261026.md). At inspected HEAD, TimeW has private process-backed converter/arithmetic/difference/zone lookup operations and **no Hub-facing CALC/WORLD request/snapshot contract**. The existing shell bridge only forwards stopwatch/countdown. Functional CALC/WORLD integration is **BLOCKED on TimeW + serialized shell owner approval**, not authorized for Hub-only implementation. Do not create duplicate processes or fake IANA/DST results. Existing TASKS and TimeW Hub controls still require desktop acceptance.

## 5. TASKS // parent and Hub

**Owner UI:** `widgets/TasksW.qml` with modes TASKS, TODAY, PROJECTS, PLANNER, SYNC; `widgets/tasks/{TaskDetailsPane,TaskTodayPane,TaskProjectsPane,TaskPlannerPane,TaskPlannerSchedulePane,TaskSyncConnectionsPane,TaskSyncPreviewPane}.qml`.  
**Writer:** single `services/hub/ApolloHubTodoStore.qml`; Hub `ApolloHubTodoMini.qml` and `ApolloHubTodoExplore.qml`.

| Capability | Parent source | Hub at inspected HEAD | Next boundary |
| --- | --- | --- | --- |
| Local task create/done/rename/delete | Shared store/UI | **Present** in mini | Explicit confirmed writes/delete; preserve draft/error state across layout changes. |
| Task description, priority and due-date editing | `TaskDetailsPane` | **Present in H:2/H:3** via canonical TaskDetailsPane | Same editor and store; prevent task selection switch when dirty/pending. |
| TODAY/due-date projection | `TaskTodayPane` / `TaskTodayPolicy.js` | **Implemented in H:2/H:3 expanded To-do at Phase 3 commit `5b4c7721`** | Same read-only TASKS view; OPEN selects existing details with dirty/pending guard. Desktop acceptance still needed. |
| Local PROJECTS grouping/rename/delete/assignment | `TaskProjectsPane`; same local store | **Read-only PROJECTS in H:2/H:3 expanded To-do, source-complete at `8b64dcfd`** | Canonical project selection and task OPEN are present. Create/rename/delete/assignment remain in standalone TASKS; no Hub writer. Desktop acceptance pending. |
| PLANNER MONTH/WEEK/DAY/TODAY + agenda | `TaskPlannerPane` | **Implemented in H:2/H:3 expanded To-do at Phase 3 commit `cf76bec5`** | Uses the same planner view and calendar projections; SCHEDULE disabled in Hub, unchanged in standalone TASKS. Desktop acceptance still needed. |
| Deliberate scheduling and due-date changes | `TaskPlannerSchedulePane` | **Not integrated** | Reuse explicit save/clear date and shared writer; do not auto-run second write after create. |
| SYNC mapping/connections/preview | `TaskSyncConnectionsPane`, `TaskSyncPreviewPane` | **Not integrated** | Preview ≠ remote sync; GitW keeps `GitHubProjectsService` and credentials. |
| Hardened OS-owned writer and SQLite cutover | M11l disposable gate; M11m draft PR #849 may be ongoing | **NOT production active** | Preserve current single legacy JSON writer; no host/SQLite activation without independent acceptance and operator authorization. |

**Concurrent ownership:** TASKS M11m draft PR #849 was open during inventory. It concerns storage/host handshake, not permission for a Hub worker to change that seam. Coordinate before any new TASKS persistence operation.

## 6. Cross-cutting acceptance gates

For any new functional Hub view, use these checks, not simply a screenshot:

1. **Owner identity:** exact existing source and action method documented; no second collector, watchdog, disk writer or controller.
2. **Truthful state:** ready/stale/unavailable/error and `request → pending → observed result` displayed separately. Never mark a service result completed from a button handler alone.
3. **Target safety:** selected PID+start identity, app/tab/window ID, stream fingerprint/generation, task ID/revision and time timer ID revalidated before action where applicable.
4. **Continuity:** edited text, selection, scroll and confirmation state do not silently disappear or switch target on H:1/H:2/H:3, W changes, tab switches, tile MOVE/SWAP or closing the Hub. If an operation cannot preserve state, block the transition with an explicit choice rather than auto-discard.
5. **Keyboard:** controls inside an editor own arrow/typing keys; outer Hub navigation does not swallow active text edits.
6. **Recovery:** failed/rejected actions retain drafts and target; destructive actions have correct owner-backed confirmation and rollback where available.
7. **Desktop:** actual Fedora/Quickshell owner-vs-Hub parity, close/reopen, service-lifetime count, resource/performance behavior, and operator acceptance recorded distinctly from source tests.
8. **Versioned layout:** state preservation work must not silently change `ApolloHubLayout.js` schema v2 or persist unapproved private state in layout JSON.

## 7. Bounded next implementation sequence (proposed)

1. **DONE at source / awaiting desktop acceptance:** TASKS **TODAY read-only** now uses canonical `TaskTodayPane` in expanded To-do with guarded navigation. Verify TODAY → OPEN → DETAILS, draft blocking, date rollover, scroll and H:2/H:3 display; H:1 compact tile remains unchanged.
2. **DONE at source / awaiting desktop acceptance:** TASKS **PLANNER read-only** is now in expanded To-do (LIST / TODAY / PLANNER / PROJECTS / DETAILS). Uses the canonical MONTH/WEEK/DAY/TODAY and agenda projection. Hub explicitly disables SCHEDULE and uses a scrollable viewport to keep the agenda reachable in H:2. Next separate decision: whether to integrate guarded scheduling writes into Hub. Keep local task scheduling distinct from provider-connected Calendar events.
3. **DONE at source / awaiting desktop acceptance:** TASKS **PROJECTS read-only** now mounts the canonical `TaskProjectsPane` in H:2/H:3, with local project selection, assigned-task grouping, and guarded OPEN → DETAILS. The Hub passes `todoStore: null`, so create/rename/delete/assignment controls remain unavailable there; standalone TASKS retains them. A scrollable viewport exposes the lower task list at H:2. No new service, writer, or task polling.
4. **TimeW calculator / timezone tools:** pure calculations and owner-owned zone choices first. Preserve separate monotonic stopwatch/countdown state.
5. **System Audio completion:** finish output selection and re-observed effects once Team 6/T3 owner coordination is resolved. Do not conflate sink inputs with semantic app identities.
6. **AppControl deeper inventory/contract:** define exact candidates beyond RUNNING (FAVORITES, FILES, WINDOWS, THERMAL, SYSTEM, HUNTER) and their distinct safety scopes. No broad generic action gateway.

**Hi-Fi stays deferred** unless the operator/Media owner reopens it. Social, Notifications, WeatherStation, CPU++, Calendar and Notes extensions remain independent lanes for later, each subject to a full parent-widget inventory before implementation.

## 8. Verification / decisions

- **Observed:** Current repository source files and parent mode lists at the baseline HEAD above; existing operator broad functional feedback.
- **Not verified:** Each possible action-result state, zero-draft-loss across every resize/tab/mode transition, production task-writer cutover, independent T3/Team 6 host acceptance, complete live test matrix for every parent capability.
- **Initial inventory:** Documentation-only baseline; subsequent source changes are recorded below. No local-system activation or storage migration is implied.
- **Decision status:** This inventory proposes remaining ordering and traceable gaps. Operator approval for the bounded Hub UI integration does not authorize further writer, storage, or live-machine changes. Operator is final authority.

**2026-10-26 Hub integration checkpoint:** `TaskTodayPane`, `TaskPlannerPane` and `TaskProjectsPane` are mounted inside the expanded To-do workspace. The PROJECTS increment uses the same `ApolloHubTodoStore.snapshot` and canonical `TaskProjectsPane`, but deliberately passes no writer handle. Existing DETAILS draft/pending navigation guards remain in place. The H:1 compact tile is unchanged. Source contracts and repository validation passed for `8b64dcfd8e6c2f1fa20d8dc8c9c84ad7e2d47af8`. **Not yet accepted:** live Fedora/Quickshell H:2/H:3 sizing, nested scroll, project selection, OPEN → DETAILS, dirty-draft blocking, and persistence of view state across tile resize/move/close. **Active adjacent owner:** TASKS M11p draft PR #858 covers storage/host recovery and is outside this Hub integration scope.
