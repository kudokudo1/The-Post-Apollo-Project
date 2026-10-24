# 🏥💜 TASKS M10y // Read-Only SQLite v2 Snapshot Parity

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 TASKS storage continuation, external Hospital-compatible  
**Status:** Experimental, unmounted read-only Quickshell bridge and test probe  
**Authority:** Active `ApolloHubTodoStore.qml` remains the sole JSON FileView writer.

## IMPLEMENTATION

The older M10k `TaskSqliteReadBridge.qml` exposes only metadata counts for
the **schema-v1 prototype**. It cannot supply task/project rows to existing
TODAY, PLANNER, TASKS, Apollo Hub or other UI consumers.

M10y adds two standalone components for the **record-authoritative SQLite
schema-v2 prototype**:

1. `TaskSqliteSnapshotProbeM10y.py`, an explicit-`--db` Python subprocess
   that calls only `ExperimentalTaskSqliteRecordsV2.read()`. It requires
   the exact existing private test path ending in
   `m10y-snapshot-test/tasks.db`, in an operator-owned private directory.
   Missing databases remain ABSENT; it never creates a DB, directory,
   migration, journal operation or writer epoch.
2. `TaskSqliteSnapshotBridgeM10y.qml`, an **unmounted** Quickshell
   `Scope` with one explicit `requestSnapshot()` method. It launches the
   probe with `python3 -B -I`, parses a size-limited response and passes a
   projection through the actual
   `ApolloHubTodoPolicy.js.validate()` and `view()` methods.

The Python probe projects just legacy v3-compatible records and counters:
task ID, title, completion, timestamps, priority, description, due date,
project ID; and project ID, name and timestamps. It does **not** export
remote project/item identities, local custom values, source schema
extensions, operation bodies or pending request IDs. The in-memory
compatibility document is **never** serialized back to SQLite or the
existing JSON writer. Project names and task descriptions are included
because legacy UI components actually need them; therefore a future
approved runtime caller must treat subprocess stdout as private.

The QML bridge produces exactly the current `TodoPolicy.view()` snapshot
shape for display, including remaining/completed ordering, counts and
per-project counts. Crucially, it forces **`snapshot.writable=false`**
on every successful read. It never offers any `todoStore` write methods.

A source `RECOVERY_REVIEW` snapshot remains readable, but is always
read-only and visibly retains the recovery state in the bridge's `status`.
A missing fixture is `ABSENT` rather than deceptively rendering an
editable empty list. Unsupported/corrupt data becomes `ERROR`, with no
task content published.

The bridge deliberately has no component-completion hook, timer, file
watcher, second writer, remote transport, Quickshell shell mount, or
default production path. The active `TasksW.qml` bindings remain
`ApolloHubTodoStore.snapshot`.

## HOW TO USE

No desktop actions now. Run these in the repository CI:

```sh
python3 tests/tasks/test_task_sqlite_snapshot_m10y.py
python3 tests/tasks/test_task_sqlite_records_v2.py
node tests/tasks/test_unified_storage_read_bridge.cjs
```

The M10y test allocates private disposable fixture directories, initializes
only synthetic v2 models there, and invokes the read probe as a separate
process. The Quickshell QML bridge itself is statically inspected; GitHub
CI does **not** render the QML or prove a real Wayland/Quickshell process
lifecycle.

## VERIFY

- Compare the subprocess's exact v3-compatible document and snapshot
  against the deployed JavaScript TodoPolicy, TODAY and PLANNER policies.
- Preserve incomplete-first task ordering, due-date/priority/description
  fields, project assignment, counts and stable IDs.
- Distinguish present-empty, absent, and recovery-review states.
- Confirm GIT remote metadata, custom values and queue bodies never appear
  in the probe response, while the source v2 document remains unchanged.
- Ensure no accidental task save, journal advancement or SENDING recovery.
- Refuse wrong test paths, unsupported schema, malformed projection and
  silent database creation.
- Verify the new QML bridge stays absent from `shell.qml`,
  `TasksW.qml`, all other widgets and services.

## WATCH OUT FOR

**This is read-only parity, not writer handoff.** It does not substitute
for `ApolloHubTodoStore`; its snapshot deliberately cannot enable
SAVE DATE, ADD, project edits or other mutating controls. It neither
proves the actual QML window works on the operator's Fedora/Quickshell
installation nor provides the on-device restart/freeze experiment.

A real migration/activation will still require verified backup and
rollback, one authoritative writer process, safe startup/cancellation
recovery, QML process failure handling, and operator approval. UI acceptance
also requires deciding how historical `RECOVERY_REVIEW` snapshots should
be visually distinguished before any future live mount.

This is a separate checkpoint from the merged M10w/M10x lifecycle
contract. Their experimental HELD journal is not combined with the
record-level v2 field journal and is not exposed here.

## CHECKLIST

- [x] Verify current GitHub source, PRs and current live writer
- [x] Add fail-closed schema-v2 read projection probe
- [x] Add unmounted explicit-use Quickshell display bridge
- [x] Compare emitted projection with existing TODAY/PLANNER snapshot policies
- [x] Keep SQLite storage and JSON writer unchanged
- [ ] Complete GitHub CI and independent review
- [ ] Operator-approved PR merge
- [ ] Separately approved disposable on-device QML runtime test
- [ ] Complete writer admission, read/write snapshot parity and restart recovery
- [ ] Separately authorize backup/migration/activation

## NEXT

M10z should plan and test actual **disposable Quickshell runtime readback**,
including process exit-order permutations, cancellation, reload and
state-change signals, without ever attaching a SQLite writer to TASKS.
A later production handoff requires a distinct operator decision.

## DECISIONS

SQLite is still the selected target, the legacy JSON FileView remains
authoritative. No local-machine changes, real task database reads,
GitHub Project writes, production migration, or live Hospital registration
occurred in M10y.
