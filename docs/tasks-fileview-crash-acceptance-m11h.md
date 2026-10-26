# 🏥💜 TASKS M11h // Owned FileView Crash Windows and Runtime Acceptance Boundary

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** TASKS storage recovery, Proxy 2 continuation, bounded GitHub implementation  
**Status:** Disposable abrupt-process-death fixture and CI verification, not native Quickshell runtime acceptance  
**Authority:** Live `services/hub/ApolloHubTodoStore.qml` JSON FileView writer is unchanged

## IMPLEMENTATION

M11f PR #801 and M11g PR #803 are now merged into `main`.
M11g's long-lived OS-`flock` host reserves synthetic FileView saves
in a test-only SQLite journal. Its existing tests simulate atomic FileView
rename and perform a safe readback before settling the stage.

M11h adds **deterministic real process-death fault injection** to the
existing test-only `TaskFileViewOwnerHostM11g.py`. The new optional CLI
`--m11h-test-fault` accepts *only* four named checkpoints and is never
supplied by a QML component. There is no injection on startup or in
normal host operation.

| Fault window | Previously persisted fact | Fresh-owner treatment |
|---|---|---|
| After durable admit, before admit reply | Pending stage recorded, old file unchanged | `RECOVERY_REVIEW`, pending true |
| After FileView bytes read, before settle commit | Pending stage recorded, file advanced | `RECOVERY_REVIEW`, pending true |
| After settle commit, before reply | Pending cleared, file advanced, QML may not know | `RECOVERY_REVIEW`, pending false |
| After freeze commit, before reply | Freeze persisted, no ACK delivered | `RECOVERY_REVIEW`, no admission |

The fault injector uses `os._exit(86)`, not an exception, so the
simulated host loses its live OS file lock without performing normal
cleanup, yet its committed SQLite records survive. Tests require
**no false success acknowledgment** across process death.

M11h also tests a crash before any save and an invalid repeated
request while a stage is pending. The existing owner on ordinary
start must always be reacquired and re-reviewed, never inherited from
a `JSON_ACTIVE` row.

The host still handles only private, operator-created test files under
`m11e-fileview-test`. No QML component imports the crash flag.
`TaskFileViewHostBridgeM11g.qml` continues to have no fault injection,
autorun, production file path or migration entrypoint.

## HOW TO USE

GitHub CI only by default:

```sh
python3 tests/tasks/test_task_fileview_crash_windows_m11h.py
python3 tests/tasks/test_task_fileview_owner_host_m11g.py
```

The test suite creates private disposable synthetic fixtures in temporary
directories, uses separate real OS subprocesses with M10p lock ownership,
models a FileView atomic rename on the synthetic file only, crashes the
host, inspects its **test** SQLite ledger and restarts a fresh owner.
No live TASKS files or desktop instance are involved.

**Native on-device acceptance is still a separate, explicitly
authorized action.** The existing standalone
`TaskFileViewHostHarnessM11g.qml` can be used after permission,
with an independently inspected test directory, to observe actual QML
signal order, FileView callback behavior, Wayland rendering and process
shutdown. CI success cannot establish any of those facts.

## VERIFY

The CI suite asserts:

- Four actual abrupt exit windows and zero false successful acknowledgments
- Correct durable `phase`, `epoch`, `pending_stage` and file content
- New host still obtains its own OS lock, increments epoch and enters
  `RECOVERY_REVIEW`, regardless of previous `JSON_ACTIVE` or freeze
- Stale callback IDs and all further stages are refused after restart
- A committed settle with a lost reply never causes blind repeat or
  extra synthetic increment
- An abrupt idle exit also cannot inherit old `JSON_ACTIVE` authority
- Replayed requests abort processing and preserve the outstanding stage
- Real task writer/shell never import the disposable host or fault flag
- Regression coverage from M11g, M11f, M11e, M11d and M11c

## WATCH OUT FOR

**These tests crash a disposable Python host, not Quickshell itself.**
They do not prove QML callback origin, signal ordering or real
`FileView` cancellation behavior, nor physical power-loss durability.
The system still cannot safely rearm the old JSON writer automatically
after an ambiguous restart, and this fixture does not attempt that.

The test-only SQLite authority database is NOT an actual SQLite TASKS
database. A committed synthetic FileView write is never remote GitHub
confirmation. None of the stage, settle or frozen records authorizes
production storage migration, a live task writer, a remote project
operation or deletion of source JSON.

A future live writer patch requires operator approval, a verified native
Quickshell acceptance, durable stage-token-to-callback provenance,
full snapshot/operation parity, and backup/rollback validation. The
QML-only test path suffix does not establish safe symlink ownership.

## CHECKLIST

- [x] Verify M11f and M11g merged, current source and writer boundaries
- [x] Add deterministic crash points only to disposable OS-owned host
- [x] Test real process exit before and after durable transactions
- [x] Verify cross-process recovery remains locked after every fault
- [x] Verify no live QML import and preserve no-migration boundary
- [ ] Finish current-head CI and independent source review
- [ ] Operator-authorized PR merge
- [ ] Separately authorized native M10z/M11e/M11g Quickshell acceptance
- [ ] Real production FileView admission protocol and backup/rollback
- [ ] Separately approved SQLite migration/activation

## NEXT

Once merged, the next useful acceptance step is **native runtime
verification in a separate Quickshell process** using the previously
defined synthetic UI and explicit operator permission. Until then,
further work should focus on identifying and fixing concrete
runtime/readback/protocol limitations, not expanding test-only
simulations indefinitely.

## DECISIONS

JSON remains the sole active TASKS writer, SQLite production activation
is disabled, and all work is within a new GitHub draft PR. No local
machine change, real task data access, desktop process restart,
GitHub Project write or live Hospital registration occurred.
