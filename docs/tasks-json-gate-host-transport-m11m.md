# 🏥💜 TASKS M11m // Isolated OS Host ↔ Native FileView Handshake

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / Assignment:** TASKS storage continuity, Proxy 1 → Proxy 2 successor work  
**Provider:** OpenAI ChatGPT external Hospital-compatible, not registered in live Hospital  
**Base:** `main` at `b44a16826c111adb202e50c090009deff066c5dd` (Oct 26, 2026)  
**Status:** GitHub-only native-harness implementation, not production deployment/activation  
**Prior handoffs:** [M11j](./tasks-native-acceptance-production-readiness-m11j.md) / [M11k](./tasks-production-writer-gate-m11k.md) / [M11l](./tasks-json-gate-owner-m11l.md)

## IMPLEMENTATION

The M11l Python OS-lock/journal owner had a disposable real-schema file but no real Process ↔ QML contract. This milestone adds a bounded transport and independent standalone Quickshell adapter.

| File | Role |
| --- | --- |
| `tests/tasks/fixtures/TaskJsonGateTransportM11m.py` | Explicit JSON-lines Python host; imports and holds the M11l disposable OS-owner for the session |
| `services/projects/TaskJsonGateHostBridgeM11m.qml` | Standalone Quickshell Process + FileView handshake, refuses malformed/stale callbacks, defers readback |
| `TaskJsonGateHarnessM11m.qml` | Explicit native test window, never imported into production `shell.qml` |
| `tests/tasks/fixtures/TaskJsonGateSeedM11m.py` | Explicit one-time private synthetic fixture seeder; never overwrites an existing directory |
| `tests/tasks/test_task_json_gate_transport_m11m.py` | Subprocess protocol, lock conflict, mismatch, restart and QML source audit |
| `.github/workflows/tasks-json-gate-transport-m11m.yml` | Disposable test + prior owner/source compatibility regression checks |

### Runtime sequence in the disposable test

1. Operator explicitly creates a new, private `m11l-tasks-copy/todo-copy.json` synthetic v3 fixture. Existing test authorities must not be reinitialized.
2. Standalone QML window starts the Python host with **explicit** directory, writer ID, and optionally one-time `--bootstrap-test`. The OS host acquires a nonblocking lifetime `flock`, validates source identity/version, and creates its test-only journal/backup on first bootstrap.
3. Host writes bounded `hello` status to Process stdout. QML independently loads the fixture using FileView. Neither QML's `fileLoaded` bool nor a reply field can grant **production** authority.
4. INCREMENT forms a synthetic v3 task edit in memory. QML sends a uniquely named stage ID and candidate JSON to `reserve`; host validates full task schema, exact current source hash and one-in-flight rule, then commits stage reservation.
5. **Only after valid reservation**, QML invokes FileView `setText` on the disposable fixture. `onSaved` schedules `Qt.callLater` deferred `reload`; on exact readback QML submits `verify`.
6. Host independently reads actual fixture bytes and settles the exact stage/epoch in SQLite before the QML test UI increments its confirmed counter.
7. FREEZE closes QML admission, drains a pending stage first, durably freezes host admission and requires a fresh owner on restart to enter `RECOVERY_REVIEW`, not automatically resume. STOP closes the process and never rearms old authority.

The transport enforces bounded monotonic request IDs, strict JSON key sets, response identity, one outstanding request, no reflected task contents, and false production/SQLite/migration/remote authorization fields. Malformed traffic, readback mismatch and unexpected host exit are fail-closed, leaving a pending stage to be reviewed on restart.

### Important source separation

The only production writer remains `services/hub/ApolloHubTodoStore.qml`: `guardedWriterEnabled: false`, one `stage()`, one real `FileView`. This milestone neither imports M11m into it nor alters any TASKS, TODAY, PLANNER or Hub mutation path. The disposable host accepts only the literal private `m11l-tasks-copy` folder and source file `todo-copy.json`, not `apollo-hub-todo-v1.json`. No SQLite task migration.

## HOW TO USE

CI runs automatically on the PR. **Do not launch a local native test until separately authorized** because it creates a disposable folder and Quickshell test process on the operator's machine.

For a later separately approved native acceptance session, the intended procedure is:

1. Choose an *existing private, operator-owned* test parent folder, not the live Quickshell data directory.
2. Run `python3 -B tests/tasks/fixtures/TaskJsonGateSeedM11m.py --private-parent /absolute/private/test-parent` **once**. It creates `m11l-tasks-copy/todo-copy.json`, only when that directory did not already exist.
3. Launch only the standalone `qs -p /absolute/repo/TaskJsonGateHarnessM11m.qml`. Do not edit `shell.qml` or start another instance of the same test owner.
4. Enter the resulting absolute `todo-copy.json` path. Click **NEW TEST**, then **INCREMENT** twice, **FREEZE**, **STOP**. Subsequent **EXISTING** runs against that exact folder should report `RECOVERY_REVIEW` and deny new stages.
5. Keep the original test folder if an interrupted/ambiguous stage was observed. Create a **different** private parent for a genuinely new test; do not delete or rebootstrap failed authority as if it never happened.

No local commands have been executed on the operator's desktop by this GitHub-only milestone.

## VERIFY

Repository-only checks:

```sh
python3 tests/tasks/test_task_json_gate_transport_m11m.py
python3 tests/tasks/test_task_json_gate_candidate_m11l.py
python3 tests/tasks/test_task_production_gate_review_m11k.py
python3 tests/tasks/test_task_native_acceptance_m11j.py
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

M11m subprocess tests exercise *actual Python OS processes and temporary disk copies*. They intentionally simulate FileView writes using an atomic replacement instead of running a Wayland/Quickshell runtime in CI. Native FileView callback timing and on-device screenshot acceptance are **not** proven by GitHub CI.

## WATCH OUT FOR

- The QML adapter has not yet been tested in native Quickshell on the operator's PC. UI states and callback order remain **source reviewed only** until separately observed.
- Real task backup, durable production configuration, source provenance on the operator's machine, crash/power-loss windows and production host authorization remain unresolved.
- Existing M11l host's Python validator is not automatically byte-for-byte equivalent to every JS policy edge case. Do not admit live tasks until parity is demonstrated.
- The fixture-only `SQLite` journal protects the test owner; it is **not** an active SQLite TASKS data store. Legacy JSON is still live and unfenced by this test harness.
- Re-using an ambiguous native test folder is prohibited. No silent reset, rebootstrap, file deletion, local pull, process restart, or modified worktree cleanup is authorized.
- M11m does **not** grant merge, local installation, running the native harness, production activation, or data migration authority.

## CHECKLIST

- [x] Reverify M11l merge, current `main`, concurrent TASKS ownership and source
- [x] Add explicit disposable JSON-lines OS-host transport
- [x] Add standalone FileView handshake with deferred readback and stage correlation
- [x] Add explicit private test seeder and independent harness
- [x] Add subprocess fault/mismatch/lock/restart checks and CI
- [ ] Complete current PR CI and independent source review
- [ ] Separately approve/operator-observe native test on a new private test folder
- [ ] Reconcile validator parity, all crash/error cases and actual-source backup/rollback
- [ ] Separately authorize a production host patch and *later* guarded mode activation
- [ ] Separately authorize future SQLite migration, if still desired

## NEXT

Check workflow results and source diff. Only after independent review may the M11m draft be merged. The next milestone is **M11n native acceptance** of this new disposable handshake, with operator-observed evidence and explicit on-machine scope. A future production integration must be another exact, separately approved patch.

## DECISIONS

No live TASKS code paths are changed in M11m; no local user files, running shell, GitHub Project data or live Hospital assignment were modified. Production JSON remains sole live authority and the compile-disabled gate remains off. SQLite task migration remains inactive.
