# 🏥💜 TASKS // M10z Isolated Quickshell Snapshot Runtime Harness

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** TASKS storage, Proxy 1 continuation with operator-authorized successor  
**Status:** Test-only read/reload/cancel harness and process-event tests. **QML runtime acceptance still pending.**  
**Live authority:** `ApolloHubTodoStore.qml` remains the exclusive JSON FileView writer.

## IMPLEMENTATION

M10y PR #758 is merged. Its unmounted read bridge verifies SQLite-v2 to
legacy v3 snapshot compatibility in Python+Node tests. M10z closes several
*source-level* subprocess lifecycle gaps and adds an explicitly launched
Quickshell acceptance surface.

- `TaskSqliteSnapshotLifecycleM10z.js`: pure, no-IO join of Quickshell
  `Process.onExited` and `StdioCollector.onStreamFinished`. Either signal
  order is valid; the response is not parsed until both signals arrive.
  Duplicate callbacks do not overwrite the first result. A cancelled
  request is **never** treated as successful, even if the child already
  generated stdout. New requests start with a clean generation.
- `TaskSqliteSnapshotBridgeM10y.qml`: an additive, still unmounted update.
  Provides `cancelSnapshot()` (asks the one probe to terminate via
  `worker.running=false`) and `clearSnapshot()` after completion.
  `requestSnapshot()` refuses another request while a child is running
  or its exit/collector events remain unresolved. Cancellation clears
  the displayed snapshot to a non-writable unavailable state. No timer,
  automatic restart, saved data or second writer is introduced.
- `TaskSqliteSnapshotHarnessM10z.qml`: explicit-use root-level Quickshell
  configuration with **READ / CANCEL / CLEAR**. The panel displays only
  readiness, error code, task counts, snapshot writability and inspection
  count. It contains no network or storage writer. Its database path input
  defaults to blank.
- `tests/tasks/fixtures/m10z_snapshot_fixture.py`: generates an
  **explicitly requested disposable** SQLite-v2 sample, requires the
  preexisting private `m10y-snapshot-test` directory and refuses to
  overwrite existing `tasks.db`.

This does NOT mount either the new panel or SQLite bridge in
`shell.qml`, `TasksW.qml`, PLANNER, Apollo Hub or GitW. It does not
change the deployed task writer, database schema, startup ownership,
remote journal, GitHub Projects or local desktop.

## HOW TO USE

**GitHub CI (automatic):**

```sh
node tests/tasks/test_task_sqlite_snapshot_lifecycle_m10z.cjs
python3 tests/tasks/test_task_sqlite_snapshot_runtime_m10z.py
python3 tests/tasks/test_task_sqlite_snapshot_m10y.py
```

**Later, only with explicit operator permission for on-device disposable
fixture creation and a separate Quickshell instance**, the acceptance
procedure is:

1. Confirm the repo checkout is current and the normal TASKS menu is
   unaffected. Create a *new private test directory*, never a real TASKS
   database directory, for example:
   `mkdir -m 700 -p "$HOME/m10z-isolated/m10y-snapshot-test"`
2. Create synthetic data once using
   `python3 -B tests/tasks/fixtures/m10z_snapshot_fixture.py --db "$HOME/m10z-isolated/m10y-snapshot-test/tasks.db"`
   (refuses existing file and unsafe directory).
3. Launch a **second explicit-path configuration**, not the production
   `shell.qml`, with
   `qs -p "/absolute/path/to/repo/TaskSqliteSnapshotHarnessM10z.qml"`.
4. Type the *test* database's absolute path and press READ. Check READY,
   two synthetic tasks, one remaining, one completed and
   `WRITABLE: false`. Press CLEAR, repeat READ, and press CANCEL
   while a read is in flight. Verify that neither rejected nor cancelled
   reads publish task content. To test ABSENT, use a new missing
   `m10y-snapshot-test/tasks.db` path.
5. Close **only** the isolated Quickshell process. Never use
   `pkill -x quickshell` or restart the production instance for this test.
   No scripts here delete any local files automatically.

The test setup steps above are documented instructions, **not actions already
performed on the operator's machine**. The operator must separately authorize
local writes and the extra Quickshell process.

## VERIFY

GitHub tests can establish:

- Callback join correctness for **both** exit/stream orders, duplicate
  events, nonzero exit, oversized/empty output, cancellation before/after
  either callback, generation reset, and no stale output publication.
- Actual Python subprocess reads against a strictly disposable
  SQLite-v2 fixture. Multiple sequential restarts/readbacks preserve the
  same source hash and task data; the generator refuses overwriting it.
- The QML bridge is not imported into production shell/TASKS; its
  `Process` handles only explicit requests; there is no auto-retry, save,
  timer, GitHub call, QML output logging or silent real-path fallback.
- The existing M10y deployed-TODAY/PLANNER snapshot parity tests remain
  satisfied and returned snapshots remain non-writable.

**Not yet verified:** The actual Quickshell 0.2.1 runtime's QML type
resolution, real Process signal ordering, Wayland window rendering,
real cancellation timing, reload under live CPU load, window/process
cleanup, or the operator's dual-monitor SwayFX environment. Those require
the independently approved disposable on-device acceptance. Tests that
simulate callbacks are not substitutes for a QML launch.

## WATCH OUT FOR

The only reasonable route to a live SQLite cutover still requires complete
exclusive-writer admission and crash recovery, a versioned unified
field/lifecycle journal, remote identity/permission/ACK policy, verified
legacy backup/restore, shadow read, snapshot and write parity, and the
operator's *separate* approval to migrate/activate.

A pending cancellation may remain BUSY until both Process-exit and stream
completion arrive. The UI must not automatically retry an ambiguous
process. If Quickshell gets stuck, stop only the isolated instance and
inspect its logs, not live TASKS. No explicit runtime timeout is added;
this is a manual test harness, not an unattended production service.

## CHECKLIST

- [x] Recheck current GitHub main, merged M10w/x/y, active JSON writer
- [x] Add deterministic exit/stream/cancellation state machine and tests
- [x] Add unmounted standalone QML acceptance window
- [x] Add explicit disposable v2 fixture generation and process-restart checks
- [ ] Finish CI and independent source review
- [ ] Operator-authorized M10z draft PR merge
- [ ] Separate operator permission for actual disposable on-device QML test
- [ ] Confirm native Quickshell runtime tests (startup, cancellation, reload)
- [ ] Production writer handoff, migration and rollback review

## NEXT

After CI and operator review, run the isolated on-device QML runtime
acceptance in a *separate* process. If it passes, use that evidence to
design M11's production-ready single-writer host, still behind independent
activation and migration permissions.

## DECISIONS

No live machine, TASKS JSON file, real task DB, GitHub Project, Quickshell
production configuration or live Hospital registration is modified.
SQLite remains the future target, while the existing JSON writer remains
authoritative.
