# Favorites++ // Runtime Liberation & Widget-Independent Ownership Roadmap

> STATUS // Proposed architecture and staged extraction plan; **not implementation authorization, merge approval, production activation, or operator acceptance**.
>
> PATIENT // The-Post-Apollo-Project
>
> SCOPE // AppControl Favorites/COMBI reusable behavior, shared Favorites services, CPU++ universal Favorites management, provider-specific action/identity ownership.
>
> OWNER / COORDINATION // Existing Favorites (historical T2) lane, with current Hospital assignment and shared host owners to be reverified before surgery.
>
> EVIDENCE BASE // GitHub main `233857518c2b213d05325421d933aff182c92d22` (2026-11-26); inspected AppControl blob `bbea088bbfb686da95d36a3b0d43d4376e07cf2a`. Exact current code must be reacquired before implementation.

## 1. Operator objective and definition

**Fully extracted** means more than placing a JSON writer outside the widget.

AppControl must cease to own reusable Favorites storage mutation, provider-neutral orchestration, reconstruction aggregation, shared watch evaluation and general favorite catalog processing. AppControl remains a consumer and retains its own Favorites/COMBI UI, input focus, presentation, and provider-specific action/navigation behavior.

**CPU++ → FAVORITES is the primary universal human interface** to saved resources across Post-Apollo. CPU++ must not become the new backend or a second writer. Long-lived shared functionality lives under the relevant services and authoritative provider owners, independent of whether AppControl or CPU++ is open.

A Quickshell singleton/service can be widget-independent while still executing in the Quickshell process. A separate daemon is **not assumed**. A daemon/process boundary is an additional design decision requiring lifecycle, permissions, resource and restart evidence.

## 2. Verified architecture at the audit checkpoint

### Already extracted / shared

- `services/favorites/FavoritesStore.qml` owns `appcontrol-favorites.json` and its four original arrays: `favoriteKeys`, `favoriteDetailActionKeys`, `favoriteMonitorBoxKeys`, `favoriteTaskMetricKeys`.
- `services/favorites/FavoritesService.qml` already has generic membership, monitor, task-watch and preferred-action toggle APIs.
- `FavoritesDefaultStore.qml` and `FavoritesCollectionsStore.qml` independently own default-provider and collection metadata; do not merge these schemas or silently migrate existing owner files.
- `FavoritesResourcePolicy.js`, read-only provider projections, `FavoritesUnifiedCatalog.qml`, management/search/selection policies and shared UI components exist.
- `widgets/cpuplus/CpuPlusFavoritesHubPane.qml` is the current universal Favorites management surface.
- Existing provider-specific owners, e.g. Clock/Time, Weather HOME, Radio, Places, Notifications and Hospital, retain their own durable facts and action permissions.

### Still embedded in `widgets/AppControlW.qml`

The audit identified these source families (line numbers refer to the pinned blob, not a future head):

| Family | Evidence lines | Current behavior / disposition |
| --- | --- | --- |
| Four direct FavoritesStore list assignments | 6173, 6357, 6612, 9464 | Replace through existing FavoritesService while retaining UI aftermath |
| Task and metric identity, watch evaluation and notifications | 6104–6265 | Separate provider-owned identity/telemetry from reusable membership and alert orchestration; HUNTER safety remains authoritative |
| Generic key construction and favorite matching | 6267–6310 | Split by actual provider; preserve legacy key bytes and migration rules |
| Favorite record wrappers and reconstruction | 6413–6529, 8280–8397 | Provider record resolution + reusable coordinator; no fabricated authority |
| RUN favorite key decoding | 4483–4536 | RUN provider-owned format and exact compatibility |
| COMBI static catalog and search data | 3427–3555, 8200–8455 | Extract reusable assembly/policy; retain AppControl presentation/focus |
| FILES favorite sort/pin | 3778–3810 | Coordinate with FILES owner and canonical FILES resolver; no independent filesystem probing |
| Exact owner navigation and preferred detail selection | 8722–8940, 9153–9476 | Split generic checks from AppControl-local navigation and action semantics |
| Favorites rail, scope selection, submodes, visual/input states | around 120–170, 3231–3418, 16470–17620 | **Remain in AppControl** as local UI, except reusable pure filtering policies |

One important negative finding: the inspected AppControl blob had no `FileFavoritesAdapter`, `FileFavoriteResolutionClient`, `fileService.resolveFavoriteIdentity` or `FavoritesUnifiedCatalog` reference. Old T2/T3-F branch work is not proof of integration into the current patient.

These are **source audit findings**, not runtime measurements. References mentioning Favorites are not all backend code; 1,061 matching lines cannot be used as a line count of extractable logic.

## 3. Target ownership and data flow

```text
                    shared Favorites contracts/services
               membership · catalog · collection references
               resolution coordination · read-only projections
                         │                 │
                provider identity     provider snapshots
                         │                 │
     FILES · APPS · RUN · WINDOWS · PROCESS · SYSTEM · THERMAL
       and Clock / Time / Weather / Radio / Places / Hospital
               (own domain truth, liveness and actions)
                         │
                  safe request/result
                         │
          ┌──────────────┴───────────────┐
          │                              │
    CPU++ → FAVORITES            AppControl → FAVORITES/COMBI
    primary universal UI         local catalog + provider UI
    management and collections   focus, gestures, presentation
          └──────────────┬───────────────┘
                         │
                 no duplicate writer
                 no implicit authority
```

*Service ownership is independent of widget lifetime.* Specifically test that closing AppControl leaves underlying shared membership available, and that any genuinely background watches continue only if their owning service's intentional lifecycle supports them.

Provider identity is never inferred from a display label, temporary PID, window title or tab index unless a provider has explicitly defined persistence compatibility. Unavailable, invalid and ambiguous resolver results remain distinct. The coordinator must not pick the first apparent match.

## 4. Phased extraction

### Phase A // Establish equivalence and guard rails

- Reverify Hospital Room/Assignment, ownership of AppControl, CPU++, PROCESS/HUNTER, FILES, RUN and shared services; obtain a serialized host slot before any AppControl rewrite.
- Record current storage fixtures and legacy keys, including four original JSON arrays, preferred-action first-match behavior, RUN modes, task identity, metric watch identity, FILES legacy labels and the HUNTER exclusion/recheck contract.
- Capture a disposable native baseline for star/unstar, rapid clicks, restart/reload, catalog ordering, selection/focus, filter changes, watch alerts and AppControl close/reopen.
- Explicitly separate source checks, native synthetic checks, operator observations and production acceptance.

**Gate A:** baseline fixtures and owner contracts are available; no source changes required to satisfy this phase.

### Phase B // Membership mutation liberation

- Replace AppControl's four direct array-mutation sites with existing `FavoritesService` APIs after verifying exact behavioral equivalence.
- Preserve prepend/removal ordering, one preferred action per context, same-star clearing, HUNTER-compatible serialized keys and callback/UI refresh timing.
- Keep `FavoritesStore` as the single existing AppControl data writer. Do not migrate the JSON or replace the newer U1/U3 writers.
- Keep AppControl-specific selection restoration and immediate feedback in the widget.

**Gate B:** saved bytes/identities and UI behavior are equivalent; no regression in HUNTER protected-target refusal; close/reopen persistence works.

### Phase C // Provider identity and reconstruction

- Define/consume provider-specific identity adapters; move shared key matching and wrapper normalization out of `AppControlW.qml`.
- APPS identity/launch stays with APPS; RUN command format and execution with RUN; FILES stat/record resolution and navigation with FILES; WINDOWS/TABS with their owners; PROCESS/HUNTER retains kill safety.
- Treat older T2/T3-F FILE resolver work as historical until current service contracts/branches are verified and safely integrated.
- Preserve exact legacy key compatibility or provide tested, non-destructive, owner-approved migrations; never guess on ambiguity.
- Use explicit resolved/missing/unavailable/invalid outcomes and a normal provider record returned by each owner.

**Gate C:** every supported saved favorite reconstructs without opening AppControl; missing/unavailable targets do not turn into guessed actions.

### Phase D // Catalog and filtering liberation

- Extract reusable FAVORITES/COMBI record aggregation, dedupe, snapshot handling, filtering, search preparation and watch selection policies into the existing service family where appropriate.
- Reuse `FavoritesUnifiedCatalog`, `FavoritesManagementPolicy`, existing projections and owner-specific policies rather than creating a second universal catalog by default.
- Retain AppControl-specific filters, view selection, scrolling, keyboard focus, hover, animations, and rail behavior in the local widget.
- Protect performance properties: avoid full catalog rebuild on telemetry-only changes, preserve list scroll position and source snapshot freshness.

**Gate D:** CPU++ and AppControl consume consistent provider identities/results without copying orchestration logic, and AppControl's local search/COMBI behavior remains equivalent.

### Phase E // Watch processing and lifetime boundaries

- Separate PROCESS/SYSTEM/THERMAL sampling and safety enforcement from favorite membership, subscription/selection and generic alert presentation.
- Preserve exact threshold behavior, one-minute notification cooldown where applicable, explicit owner permissions and HUNTER's final pre-kill favorite recheck.
- Decide intentionally which watches run while their widget is closed and where that lifecycle is owned; do not add invisible background polling by accident.
- Verify subscription teardown, restart, stale data, rapid membership changes and resource usage.

**Gate E:** documented widget-independent operation for approved watches only; no duplicate sampling, duplicate alerts, changed kill protections or unauthorized service autostart.

### Phase F // CPU++ as universal home and acceptance

- Keep `CPU++ → FAVORITES` as the primary cross-widget management/control surface using the shared coordinator and provider-owned action routing.
- Keep `AppControl → FAVORITES/COMBI` as an AppControl-local browsing experience, not an authority-bearing universal backend.
- Confirm UI remains within current Post-Apollo component/icon/focus contracts; no wholesale restyling is implied.
- Verify source tests, native Fedora synthetic tests and actual operator-run desktop flows. Require owner review for privileged operations and independent review where Hospital assigns it.

**Gate F:** AppControl can close without taking reusable Favorites behavior offline; CPU++ retains universal visibility; original provider owners, persistence and safety all behave as before. **Final DONE remains operator acceptance.**

## 5. Constraints and rollback

- No unapproved live-machine writes, Quickshell restart, host relaunch, production enablement or PR merge.
- Do not cross an active AppControl/CPU++/PROCESS/FILES host slot or concurrent worker assignment.
- Preserve existing `appcontrol-favorites.json`, `favorites-default-v1.json`, `favorites-collections-v1.json` and provider-owned stores; never merge them implicitly.
- Preserve protected HUNTER favorite semantics; Favorites does not authorize killing, launching or navigating.
- Implement one bounded phase per reviewed branch/PR, with exact-base verification, no mass rewrite and focused regression suites.
- Rollback via a phase-specific source revert. Do not erase or silently repair user favorite data.

## 6. Acceptance matrix

| Check | Expected evidence |
| --- | --- |
| Four membership operations | Exact-key, order, preferred-action and persistence parity |
| Provider reconstruction | Current record, missing, unavailable, invalid, ambiguous refusal |
| Runtime independence | AppControl closed; shared membership and approved watches still operate |
| CPU++ source aggregation | Cross-owner visibility with identity redaction and owner action separation |
| Favorites/COMBI | Search/filter/submode/selection/scroll behavior preserved |
| Safety | HUNTER protected-target exclusion and last-moment recheck unchanged |
| Performance | No duplicate telemetry sampling or unnecessary catalog rebuild |
| Recovery | Rapid edits, save failures, restart and corrupt/unsupported document refusal |
| Human acceptance | Operator-observed live UI and final decision |

## 7. Open decisions and dependencies

1. **Host slot / team ownership:** verify the current serialized AppControl integration authority before Phase B.
2. **Resolver readiness:** verify FILES and other current provider APIs against main; historical isolated branches are insufficient.
3. **Service lifetime:** choose which watches should persist outside open widgets based on explicit policy and resource measurements; do not assume a daemon.
4. **Legacy migration:** identify collision-prone label-based keys and a safe provider-backed resolution strategy.
5. **CPU++ action expansion:** each source-owned mutating action requires a separate permission/owner contract; a universal Favorites entry is not universal authorization.

## 8. Related canonical contracts and evidence

- [Favorites U0](./favorites-universal-u0.md), [U1](./favorites-universal-u1.md), [U2](./favorites-universal-u2.md), [U3a](./favorites-universal-u3a.md).
- [CPU++ Favorites U4](./cpuplus-favorites-management-u4.md).
- [Syntagma AGENTS](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/AGENTS.md), [Hospital Agent Protocol](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/OPERATE/HOSPITAL-AGENT-PROTOCOL.md), [Post-Apollo Working Guide](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/OPERATE/POST-APOLLO-WORKING-GUIDE.md).
- Current source targets: [AppControlW.qml](../../widgets/AppControlW.qml), [Favorites services](../../services/favorites/), [CPU++ Favorites UI](../../widgets/cpuplus/CpuPlusFavoritesHubPane.qml).
