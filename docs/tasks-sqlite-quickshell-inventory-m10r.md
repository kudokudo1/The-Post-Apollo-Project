# 🏥💜 TASKS // M10r Disposable Quickshell Rehearsal & API Inventory

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Owner:** Proxy 1 assignment, continuing under the operator-authorized Proxy 2 successor  
**Hospital:** external-compatible; live assignment registration not asserted  
**Status:** unmounted test-only UI and checked compatibility inventory. JSON remains the live TASKS writer.

## IMPLEMENTATION

M10q's `TaskSqliteAdmissionRehearsal.qml` provides a persistent, fail-closed
`Process` connection to an explicitly existing private `handoff-test.db`
via `TaskSqliteHandoffHost.py`. M10r adds a separate, **explicitly
launched** `tests/tasks/fixtures/TaskSqliteAdmissionHarness.qml` that exposes
START, STATUS, synthetic STAGE, FREEZE, synthetic SAVE OK/FAIL, and STOP.

All UI controls merely drive the existing M10q **disposable fixture**.
The QML bridge will not bootstrap a fixture or open a user TASKS database.
The harness cannot set `writeReady`, `sqliteWriteAuthorized`, or
`liveChangePerformed` to true. The source has no import or instantiation
in `shell.qml`, `TasksW.qml`, or `ApolloHubTodoStore.qml`.

This provides a test surface for a future authorized Quickshell runtime
acceptance. **Source CI does not claim that the QML window has been rendered.**

## Legacy writer API parity

The present live implementation in `services/hub/ApolloHubTodoStore.qml`
has ten public task/project storage operations. The proposed
`services/projects/ExperimentalTaskSqliteRecordsV2.py` is **test-only**, not
a compatible replacement.

| Live JSON operation / behavior | Current SQLite v2 prototype | Parity |
|---|---|---|
| `addTask(title)` | No task creation operation | MISSING |
| `setTaskDone(id, done)` | `edit_task(field="done")` | PARTIAL: isolated synthetic edit |
| `renameTask(id, title)` | `edit_task(field="title")` | PARTIAL: isolated synthetic edit |
| `updateTaskDetails(id, priority, description, dueDate)` | Separate single-field `edit_task` actions | MISSING: one atomic multi-field edit |
| `createProject(name)` | No project creation operation | MISSING |
| `assignTaskProject(taskId, projectId)` | No reassignment operation | MISSING |
| `renameProject(projectId, name)` | No project rename operation | MISSING |
| `deleteProject(projectId, confirmed)` | No guarded project delete or task-detach operation | MISSING |
| `removeTask(id, confirmed)` | No confirmed task deletion operation | MISSING |
| `reloadFromDisk()` and snapshot recovery | `read(path)` on explicitly supplied DB | PARTIAL: no live QML adapter or equivalent state API |

Additional acceptance gaps:

- The live JSON singleton generates a compatible `snapshot` including
  `items`, `projects`, `state`, `writable`, and save/failure signals.
  SQLite's M10k read bridge reports limited **read-only metadata**, not the
  full deployed snapshot. M10g offers a synthetic compatibility projection.
- The live JSON writer's asynchronous FileView onSaved/onSaveFailed and
  fail-closed reload semantics have not been replaced by a fully integrated
  SQLite host with acknowledged callbacks.
- M10l's `edit_task` atomically commits one field plus local pending GIT
  operation. This is useful groundwork, but is **not** complete local/remote
  GitHub synchronization or parity for all current UI operations.
- PLANNER `addTask` followed by due-date `updateTaskDetails` remains two
  explicit, separate saves. Atomic create-with-date is a missing enhancement
  in **both** current JSON and experimental SQLite interfaces.
- Project and task IDs, timestamps, due dates, custom fields, NORMAL/GIT
  metadata, pending operations, and restart/rollback behavior must remain
  intact through any future transition.
- Quickshell's normal restart must not silently rearm a stale writer epoch.
  The recovery flow needs an explicit, operator-reviewed policy before
  production integration.

## HOW TO USE

**GitHub CI only by default:**

```sh
python3 tests/tasks/test_task_sqlite_m10r_inventory.py
python3 tests/tasks/test_task_sqlite_handoff_host.py
```

The new QML fixture is not part of the normal `shell.qml`. Later,
after explicit operator approval for *disposable on-device tests*, launch
`tests/tasks/fixtures/TaskSqliteAdmissionHarness.qml` as an isolated
Quickshell config with a previously initialized disposable private
`handoff-test.db` and a test writer ID. The bridge refuses a missing fixture;
the standalone QML does not create or migrate anything. Never supply
production user paths. Do not use this as a production migration command.

## VERIFY

- Source tests assert all current live writer entrypoints are accounted for.
- Source tests assert the experimental SQLite writer has **only** the
  documented `initialize`, `read`, `edit_task`, and
  `transition_local_operation` operations.
- Tests reject marking the missing APIs as production-ready.
- Tests assert the QML harness references only the M10q rehearsal and is
  absent from production shell/store/task host.
- Existing M10q tests exercise real disposable Python subprocess fencing,
  message sequencing, freeze and restart behavior, but QML is checked
  statically. They do not prove real Wayland rendering or interactive timing.

## WATCH OUT FOR

Do **not** connect this harness to `ApolloHubTodoStore.stage()`.
Do **not** implement a second writer or migrate the operator's task file
from a test-only interface. The SQLite task API is incomplete and normal
restart/rearm is unresolved. A blind cutover could break TASKS, PLANNER,
TODAY, project operations or Apollo Hub.

No live desktop, user task file, real `tasks.db`, or GitHub Project is
modified by the M10r code.

## CHECKLIST

- [x] Recover and verify M10q on current GitHub main
- [x] Explicit-use disposable Quickshell control surface in source
- [x] Inventory the existing writer API against SQLite
- [x] Static safety and coverage checks
- [ ] CI completion and independent code review
- [ ] Operator-authorized PR merge
- [ ] Separately approved real on-device disposable QML runtime test
- [ ] Complete all missing SQLite local CRUD and multi-field transactions
- [ ] Proven single-writer Quickshell host, safe restart recovery and parity
- [ ] Verified backup, migration, shadow read, rollback and operator approval
- [ ] Separately authorized production activation

## NEXT

M10s should close the **local SQLite API parity** gaps in isolated Python
tests, beginning with atomic create-with-date, task deletion, and project
creation/assignment. Preserve per-task invariants and GIT intent semantics.
Do not begin production migration or live writer activation until full
API parity, runtime gates, recovery and rollback have been independently
accepted.

## DECISIONS

SQLite remains the selected target; JSON remains the sole live writer.
No remote GitHub mutation authority is conferred. Source verification and
disposable subprocess tests are not a substitute for an actual authorized
Quickshell runtime check.
