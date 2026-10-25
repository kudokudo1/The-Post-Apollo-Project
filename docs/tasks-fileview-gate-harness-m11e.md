# 🏥💜 TASKS // M11e Disposable Quickshell FileView Gate Harness

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** TASKS storage recovery, Proxy 1 successor / Proxy 2  
**State:** Test-only, standalone QML configuration and synthetic JSON fixture  
**Live authority:** `ApolloHubTodoStore.qml` remains the only JSON TASKS writer.

## IMPLEMENTATION

M11d PR #783 is merged. Its source inventory identified the exact
`ApolloHubTodoStore.stage()` and `FileView.onSaved/onSaveFailed/onLoaded`
seams that a future production authority must fence. M11e provides an
**independent disposable test harness**, not a patch to that singleton.

Files:

- `services/projects/TaskFileViewGatePolicyM11e.js`: pure state
  machine: `UNARMED → LOADING → READY → SAVING → VERIFYING → READY`.
  `FREEZE` in READY immediately closes the gate; during a save or
  verification it defers FROZEN until the pending write is verified.
  Failed/unexpected callbacks, malformed fixture content, mismatched
  readback, source drift on explicit reload or unexpected file errors
  enter permanent `RECOVERY_REVIEW` for this test process.
- `services/projects/TaskFileViewGateM11e.qml`: standalone Scope,
  containing exactly one **real Quickshell 0.2.x `FileView`** with
  `atomicWrites: true`, `blockWrites: false`,
  `watchChanges: false`, and no automatic path or timer. No task
  policy, Python stage host or SQLite owner is imported.
  Manual `attachTestFile()` requires an absolute path ending in
  `m11e-fileview-test/fixture-only.json`; the file must already exist.
  One `stageSyntheticIncrement()` changes only a synthetic counter.
  `onSaved` moves to VERIFYING and calls `reload()`. Only an
  **identical onLoaded readback** publishes the new confirmed counter.
  `onSaveFailed` keeps the previous confirmed state and locks review.
- `TaskFileViewGateHarnessM11e.qml`: separately launchable test panel
  exposing **ATTACH / INCREMENT / FREEZE / RELOAD** and synthetic counts,
  status and reason only. It is never imported into the production
  `shell.qml`, TASKS, TODAY, PLANNER, Hub, GitW or their services.
- `tests/tasks/fixtures/m11e_fileview_fixture.py`: explicit, one-time
  synthetic fixture creator. It rejects existing targets, nonprivate or
  missing test directories, unsafe symlinks and the live TASKS filename.

Every test component declares **live writer, SQLite, remote GitHub and
production activation authorization false**. There is no SQLite write,
remote transport, migration, QML autorun, save retry or live task data.

**This is not an OS-owned production writer gate.** The QML event policy
fences only this one standalone FileView. Quickshell's FileView callbacks
carry no durable process epoch/stage ID. M11e can detect invalid ordering
and verify a readback, but it cannot prove attribution against a
noncooperating writer or a concurrent external filesystem mutation.
A real writer handoff still requires M10p/M11b/M11c owner fencing.

## HOW TO USE

GitHub CI (no native QML launch):

```sh
node tests/tasks/test_task_fileview_gate_policy_m11e.cjs
python3 tests/tasks/test_task_fileview_runtime_m11e.py
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

**Later on-device manual acceptance, only after separate permission for
creating a private test fixture and launching a separate QS process:**

1. Resolve the exact repository checkout path and inspect the M11e
   sources. Do not add this harness to the existing `shell.qml`.
2. Create a new private directory outside Quickshell's live data path:
   `mkdir -m 700 -p "$HOME/m11e-isolated/m11e-fileview-test"`.
3. Create the disposable fixture once:
   `python3 -B tests/tasks/fixtures/m11e_fileview_fixture.py --file "$HOME/m11e-isolated/m11e-fileview-test/fixture-only.json"`.
   It refuses overwrite. Manually confirm this is an ordinary private file,
   not a symlink or an alias to any real TASKS file.
4. In a separately invoked Quickshell instance, launch:
   `qs -p "/absolute/path/to/repo/TaskFileViewGateHarnessM11e.qml"`.
   Do not kill the normal instance. Enter the full **test-only** fixture
   path and press ATTACH. Initial phase should become READY, counter 0.
5. Press INCREMENT and observe SAVING → VERIFYING → READY. The counter
   should increment *only after* matching `onLoaded` post-save readback.
   Repeat to confirm there are no overlapping saves. RELOAD should
   preserve the same counter. Press FREEZE; further increments/reloads
   must be refused. A freeze while SAVING must defer until readback.
6. In a **fresh, isolated test only**, intentionally change the private
   fixture from outside the harness and press RELOAD; it should enter
   RECOVERY_REVIEW rather than accept a newly writable document.
   For save failure tests, only use the disposable fixture's permissions
   and restore them afterwards. Do not modify live task file permissions.
7. Terminate **only** the extra test QS instance and record real logs
   (exclude file content and absolute home paths). Do not use
   `pkill -x quickshell`.

These are operator actions for a later test, **not work performed here**.
No implicit local modifications or background actions are authorized.

## VERIFY

New CI covers:

- Pure JS transition logic for both save phases, deferred freeze,
  single in-flight write, readback mismatch, save/load failure,
  explicit reload drift, malformed JSON and unexpected callbacks.
- Strict private disposable file generation, no overwrite, wrong
  path, insecure directory and symlink rejection.
- Static inspection of the real QML FileView wiring, callback
  handlers, disabled-by-default path and complete absence of the
  harness from production shell/widgets/services.
- Regression checks for the M11d live writer inventory, M11c restart
  gate and M10z subprocess lifecycle.

GitHub CI can verify source and simulated event logic. **It cannot
prove actual Quickshell signal order, native QML parsing, Wayland
rendering, write failure handling, file rename timing, freeze-at-save
behavior or Sway process shutdown.** Those remain on-device tests.

## WATCH OUT FOR

QML cannot reliably verify symlink/inode ownership before a FileView
write. The fixture generator checks the requested test path, but a
file could be replaced afterward by an external actor. Do not use this
standalone harness on an untrusted directory or point it at any file
holding real tasks. A production handoff must use native OS process
ownership, safe open, durable epoch/token correlation and backup/restore.

M11e's `FROZEN` and `RECOVERY_REVIEW` are terminal within a single
test process: no self-rearm button. A new isolated test run must be
explicitly started with reviewed fixture data. A readback result
is evidence only, not a green light for SQLite.

## CHECKLIST

- [x] Verify M11d merged and inspect production FileView callbacks
- [x] Add standalone FileView test scope, pure policy and explicit test panel
- [x] Verify post-save readback before confirming synthetic counter
- [x] Add single-stage, deferred freeze, failure and reload protections
- [x] Add private test-only fixture creation with no overwrite
- [ ] CI passes and independent review
- [ ] Operator-authorized PR merge
- [ ] Separately authorized native on-device FileView and M10z runtime tests
- [ ] Verified persistent OS-owned epoch/stage tokens on production writer
- [ ] Separate approval for live TASKS modification, migration and rollback

## NEXT

M11f should analyze the actual native FileView acceptance evidence
from the isolated on-device harness. If permission for that test is
still pending, build a **production gate change design and mock
acceptance suite only**, with no `ApolloHubTodoStore` patch, or fix
any issues found in the standalone test harness.

## DECISIONS

No local machine changes, actual TASKS data, production singleton
modifications, active desktop services, GitHub Projects writes,
SQLite activation or live Hospital registration occur in M11e.
