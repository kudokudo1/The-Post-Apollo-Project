# 🏥💜 TASKS M11g // Disposable OS-Owned FileView Integration

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** TASKS storage recovery, successor to Proxy 1, operator-approved GitHub implementation  
**Status:** Independent draft milestone using previously merged M10p/M11e. M11f remains a separate review draft.  
**Live authority:** `services/hub/ApolloHubTodoStore.qml` JSON FileView writer, unchanged.

## IMPLEMENTATION

M11f PR #801 is still open and its simulated owner evidence **cannot**
stand in for OS ownership. M11g is intentionally independent of that PR
and instead reuses the already merged M10p durable `flock` and M11e
synthetic `FileView` design.

- `tests/tasks/fixtures/TaskFileViewOwnerHostM11g.py`: a long-lived
  JSON-lines subprocess owning M10p's **actual OS-level exclusive lock**
  and transactionally persisted synthetic stage IDs. It accepts only a
  preexisting private `m11e-fileview-test/fixture-only.json` plus sibling
  disposable `handoff-test.db`. Test DB creation requires a separately
  explicit bootstrap request; reconnecting never bootstraps or re-arms.
- `services/projects/TaskFileViewHostBridgeM11g.qml`: unmounted QML
  Scope containing one real `Process` and one real `FileView`. A user
  must specify an absolute test file path and writer ID. There is no
  auto-start, production data path, default task filename, GitHub API,
  actual SQLite task writer or migration.
- `TaskFileViewHostHarnessM11g.qml`: standalone root configuration with
  NEW TEST / EXISTING / INCREMENT / FREEZE / STOP controls. It displays
  only test counters, status and errors, not private task content.

### One synthetic save

```text
Quickshell FileView loads existing synthetic fixture
  -> separate Python process takes OS flock and confirms bootstrap state
  -> QML asks host to admit named stage
  -> host validates current private fixture; M10p persists pending stage
  -> host returns only the next synthetic counter JSON bytes
  -> QML FileView.setText(payload), atomicWrites:true, blockWrites:false
  -> FileView.onSaved => QML reload() and compares returned bytes
  -> QML requests host verify(stageId)
  -> host independently reads real fixture bytes twice with no-follow,
     inode, owner, permission, size and exact expected-byte checks
  -> ONLY THEN host settles stage durably under M10p lock/authority
  -> QML displays confirmed counter, accepts the next synthetic stage
```

A FileView `onSaveFailed` or bad post-save readback signals FAIL to the
host, which enters RECOVERY_REVIEW rather than recording a successful
stage. Unknown/stale callback IDs, duplicate stages and new stages after
host freeze are refused. A host process that exits with a pending stage
will cause the next owner to enter durable RECOVERY_REVIEW.

**Important:** the OS lock is real but guards only this disposable
fixture. It is advisory: a noncooperating process can still write the
synthetic file. The host validates its own expected readback but does
not prove live TASKS quiescence. The QML callback itself carries no
native signed stage ID. Nothing here can grant authority to a real
TASKS operation.

## HOW TO USE

GitHub CI (safe, no Quickshell launch):

```sh
python3 tests/tasks/test_task_fileview_owner_host_m11g.py
node tests/tasks/test_task_fileview_gate_policy_m11e.cjs
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

Tests initialize private files in temporary directories and simulate
FileView's atomic rename using synthetic bytes. The Python host runs as
a **real separate OS process**, holds a real lock and commits durable
stage operations to the test-only DB. No actual Quickshell UI runs in CI.

### Later native acceptance, requiring separate operator permission

1. Create a private empty test directory **outside** active QS data,
   e.g. `mkdir -m 700 -p "$HOME/m11g-isolated/m11e-fileview-test"`.
2. Create the synthetic fixture once, not the database:
   `python3 -B tests/tasks/fixtures/m11e_fileview_fixture.py --file "$HOME/m11g-isolated/m11e-fileview-test/fixture-only.json"`.
   Confirm it is a regular private file, not a symlink.
3. Launch **a second explicit Quickshell configuration**
   `qs -p "/absolute/repo/TaskFileViewHostHarnessM11g.qml"`.
   Do not restart/kill the normal Quickshell instance.
4. Enter the exact synthetic file path and press **NEW TEST** only for
   a pristine test directory without an existing `handoff-test.db`.
   Confirm JSON_ACTIVE, counter 0, stage eligible.
5. Press **INCREMENT**, verify counter 1 only after host readback;
   repeat, then **FREEZE** and verify further increments are refused.
   Press STOP and terminate only the isolated process.
6. Start the standalone test harness again with **EXISTING**, not NEW
   TEST; the durable owner must now enter RECOVERY_REVIEW and never
   re-enable stage admission.
7. For failure tests use only another newly initialized disposable
   fixture. Preserve the old test directory for review until explicitly
   authorized cleanup. Never manipulate live TASKS file permissions.

These are documented future actions, **not actions executed on the
operator's PC**.

## VERIFY

The new test checks private file/path confinement, actual cross-process
`flock` competition, synthetic reservation without changing file bytes,
one stage in flight, exact host readback before successful settlement,
unknown callback/refusal, duplicate success, freeze and pending-save drain,
synthetic bad FileView readback, failed callback, terminated host with
pending durable stage, a second owner in RECOVERY_REVIEW, altered bytes
before a new admit, and no live QML mounts. M10q/M11e/M11d/M11c
regressions run alongside it.

## WATCH OUT FOR

M11g still does not prove actual Quickshell runtime signal ordering,
native QML parsing, callback latency, Wayland rendering, or safe
cancellation. Those require approved on-device runtime acceptance.

The bridge exposes a test-path suffix filter, **not secure filesystem
canonicalization in QML**. The host checks synthetic inode and symlink
conditions on reads, but the fixture remains vulnerable to external
noncooperating writers between checks. Use only a freshly reviewed
private test directory.

M10p's existing authority is not yet a production-grade durable stage
and exact FileView byte journal. The host keeps expected bytes in RAM:
after a crash it refuses admission rather than reconstructing and
replaying an ambiguous operation. That is intentional.

## CHECKLIST

- [x] Verify M11e merged, M11f draft, actual test authority source
- [x] Reuse M10p OS lock and durable stage record, not forged QML booleans
- [x] Add independent synthetic FileView-to-host subprocess bridge
- [x] Verify actual private disk bytes before host settlement
- [x] Test contention, failure, freeze and durable restart recovery
- [ ] GitHub CI and independent review
- [ ] Operator-authorized M11g PR merge
- [ ] Explicit permission for native isolated on-device Quickshell test
- [ ] Verified production callback provenance and OS-owned epoch gate
- [ ] Separate authorization for any real writer patch or SQLite migration

## NEXT

M11h should inspect real native M10z/M11e/M11g acceptance evidence if
the operator approves that disposable desktop test. Without it, continue
a separate fixture-level callback and host crash matrix, not live
activation. Reconcile M11f before merging or sharing its mock contract
with any accepted native host implementation.

## DECISIONS

M11g is independent of unmerged M11f. JSON is still the sole active
TASKS writer. No production QML mounts, real tasks, actual TASKS database,
GitHub Projects, desktop restarts, local machine changes or live Hospital
registration occurred.
