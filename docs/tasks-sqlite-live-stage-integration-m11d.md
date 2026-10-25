# 🏥💜 TASKS // M11d Live Writer Path Inventory & Integration Contract

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 TASKS storage continuation by Proxy 2, no presumed live Hospital registration  
**Status:** Source audit, inventory and proposed acceptance contract **only**  
**Runtime:** `services/hub/ApolloHubTodoStore.qml` retains exclusive JSON FileView authority

## IMPLEMENTATION

M11c PR #782 merged. Before any attempt to install a real SQLite handoff,
M11d records the live task mutations and read-only surfaces verified against
current GitHub `main`. Its machine-readable inventory is
`tests/tasks/fixtures/task_writer_gate_inventory_m11d.json`.
`tests/tasks/test_task_writer_gate_inventory_m11d.py` scans the actual
`widgets`, `services`, `modules` and root QML files. CI fails if
previously reviewed direct `todoStore`/`ApolloHubTodoStore` mutation
callers change or an unexpected new caller appears.

### Observed write graph

```text
TASKS mode: ApolloHubTodoMini
  addTask, renameTask, setTaskDone, removeTask, reloadFromDisk
TASKS details / Hub expanded details: TaskDetailsPane
  updateTaskDetails
PLANNER mode: TaskPlannerPane > TaskPlannerSchedulePane
  addTask (undated first), updateTaskDetails (date/details)
PROJECTS mode: TaskProjectsPane
  createProject, renameProject, deleteProject, assignTaskProject
TODAY mode: TaskTodayPane
  read-only TodayPolicy.view; OPEN navigates to TASKS details
HUB: ApolloHubW > ApolloHubTile > TodoMini/TodoExplore
  injected SAME ApolloHubTodoStore + snapshot
All mutation methods -> ApolloHubTodoStore.stage()
  -> pendingDocument -> storageState="saving"
  -> FileView.setText() [atomicWrites: true]
  -> onSaved (publish confirmed document)
     OR onSaveFailed (preserve confirmed document; error)
```

The `TodoPolicy` methods are pure transformations; they are not a
second writer. `reloadFromDisk()` does not write but can change the
active document on `onLoaded`, so it is part of freeze/callback review.
TASKS, TODAY, PLANNER and the Hub reuse the same singleton and do not
instantiate a second task `FileView`.

### Minimal prospective production gate, NOT implemented

**Invariant A: Stage admission at the authoritative seam.**
Add a *durable host-owned* admission check directly inside
`ApolloHubTodoStore.stage()` **before** assigning
`pendingDocument`, setting `storageState="saving"`, or calling
`todoFile.setText`. Checking only `snapshot.writable` in each menu
is insufficient because callers can still invoke store methods and
multiple menus share the singleton.

**Invariant B: Closed gate precedes freeze acknowledgement.**
Persist the same OS-owned authority epoch and deny fresh `stage()`
calls before the UI displays a freeze confirmation. The existing
M10p/M11b/M11c `flock` fixtures demonstrate test-only behavior;
none currently gates production `FileView`.

**Invariant C: One in-flight save and token-correlated callbacks.**
Persist stage ID/generation, snapshot or source proof, and pending
state before dispatching the asynchronous `setText()`. Only the
matching `onSaved` may publish `pendingDocument`; `onSaveFailed`
must preserve the last confirmed document and enter review. Callbacks
from prior epochs, cancelled sessions, reloads and mismatched tokens
must never be mistaken for the current save. A simulated callback
token alone is not proof that FileView wrote the correct bytes.

**Invariant D: Read/reload fencing.** `reloadFromDisk()`,
`onLoaded`, and `onLoadFailed` require an epoch-aware disposition
while the gate is frozen or recovery is unresolved. Missing files
must never be treated as safe-to-overwrite during an incomplete
migration. Read-only viewing should remain possible.

**Invariant E: Shutdown, restart and dual-writer exclusion.**
Do not grant a SQLite writer because a QML boolean, a clean-looking
checkpoint or two source reads report success. Require OS lock,
durably fenced owner epoch, settled callbacks, source and backup
readback, shadow model/hash parity, remote/journal compatibility and
separate operator-approved recovery. On new owner acquisition,
`RECOVERY_REVIEW` is the default.

**Invariant F: No implicit migration, remote operation or fallback.**
Do not connect `TaskSqliteSnapshotBridgeM10y.qml` or the experimental
SQLite writers to live TASKS automatically. No fallback from error or
unknown version to empty writable data, no automatic JSON deletion,
and no remote GitHub ACK without independently verified identity.

### Proposed testing / rollout boundaries

1. Keep this inventory in CI with the source checked out on `main`;
   on changes to any TASKS/Hub UI or the store, rerun it and review
   the changed caller map.
2. Build an isolated QML test configuration injecting a *disposable*
   gate adapter and test writer, including real `FileView` callbacks,
   save failures, process termination, and reload races.
3. After separate local operator authorization, exercise M10z's
   native Quickshell reader and the proposed write-admission adapter
   in a second test-only QS process. Record actual measured runtime
   behavior, errors and rollback.
4. Design a reversible production gate patch behind an explicit
   disabled-by-default setting, independently review exact startup
   ordering, and obtain further approval before merging a live gate.
5. Only after a fully verified backup and transactional migration
   with a single OS-owned writer may SQLite be considered for
   operator-authorized activation. No existing prototype grants it.

## HOW TO USE

CI or read-only repository checkout:

```sh
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
python3 tests/tasks/test_task_writer_recovery_m11c.py
python3 tests/tasks/test_task_sqlite_snapshot_runtime_m10z.py
```

The new M11d test performs **only source-file reads**. It does not read
the operator's task database or Quickshell data directory.

## VERIFY

The test checks:

- All nine current public mutation methods route into the sole
  `stage()` method, which is the only point that calls
  `todoFile.setText()`.
- Save publication occurs in `onSaved`; save failure retains the
  confirmed document. `onLoaded/onLoadFailed` and reload exist.
- Exact direct caller methods in mini, details, schedule and projects;
  every new direct caller must be inventoried before CI accepts it.
- TODAY stays read-only; PLANNER delegates writes only to Schedule.
- Same singleton and snapshot are injected in TASKS and Hub,
  including the expanded tile. No second task-specific FileView.
- Source audit does not constitute writer admission or activation.
- Existing M11c/M11b/M11a and M10z regressions remain unchanged.

## WATCH OUT FOR

This is a **static source inventory**. It cannot prove a dynamically
generated QML call or another noncooperating process does not write a
file. Source review and runtime evidence are essential. It also does
not guarantee the original task file has already been backed up.

The current production writer remains unmodified and **does not enforce
the proposed gate**. A green CI run authorizes neither a live freeze
nor a SQLite migration.

## CHECKLIST

- [x] Verify M11c merged, current Git state and active writer
- [x] Map write surfaces, routing and pure TODAY read path
- [x] Pin direct-call inventory in a machine-readable manifest
- [x] Test only one `setText` authority and confirmed-write callbacks
- [x] Define gate, reload, save callback and restart/fault acceptance seams
- [ ] Finish CI and independent source review
- [ ] Operator-authorized M11d PR merge
- [ ] Explicitly approved isolated native Quickshell acceptance
- [ ] Build and test an unmounted simulated FileView admission gate
- [ ] Separately authorize any production writer modification
- [ ] Separately authorize backup, migration, rollback and activation

## NEXT

M11e: build a **standalone, disposable Quickshell FileView gate harness**
that exercises the exact event order of `setText`, `onSaved`,
`onSaveFailed`, `onLoaded` and restart. It must not import or
modify the production singleton. Work on GitHub can continue without
operator desktop access; native runtime tests need separate approval.

## DECISIONS

No existing TASKS, TODAY, PLANNER, Hub, `shell.qml`, real user data,
desktop service, GitHub Project, or live Hospital assignment is changed.
JSON remains the only active task writer. SQLite remains inactive.
