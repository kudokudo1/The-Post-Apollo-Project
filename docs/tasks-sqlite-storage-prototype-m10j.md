# 🏥💜 PROXY 1 // M10j SQLite Storage Prototype & Startup Recovery

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Operator decision:** Option B, SQLite for the future unified TASKS database.  
**Owner:** Proxy 1, external development assignment, not registered in live Hospital.  
**Status:** Experimental adapter / test-only implementation; no live activation.

## IMPLEMENTATION

The operator selected **Option B**, a separate TASKS SQLite store using the
pattern already established by TimeW `MachineCheckpointStore.py`, PX Hospital,
and PX Operations. This milestone does not attach TASKS to those databases or
change their permissions or schema.

New `services/projects/ExperimentalTaskSqliteStore.py` has **no CLI,
configured default database path, or Quickshell connection**. A test caller
must explicitly supply a `Path` ending in `tasks.db` inside a
pre-existing private directory. No storage is created for read-only calls.

The experimental SQLite format uses `PRAGMA user_version=1`,
`journal_mode=WAL`, `synchronous=FULL`, foreign keys and bounded timeouts.
It stores the complete M10h version-2 model in a checksum-verified singleton
row alongside indexed projections for projects, tasks, and offline operations.

An explicit commit:

1. Strictly validates the caller's full v2 model, including operation order,
   project/task identity and timestamp constraints, custom field types and
   shape-only GitHub references. The database's JSON decoder refuses
   duplicate keys and non-finite values.
2. Acquires SQLite's `BEGIN IMMEDIATE` transaction. Requires exact revision
   and SHA-256 baseline for updates; the first initialization requires an
   explicit revision-zero envelope and no previous baseline.
3. Rebuilds the task, project and operation indexes and saves the complete
   envelope **within the same transaction**.
4. Commits and reopens/validates the whole model, hash, revision, and index
   parity before reporting `LOCAL_COMMITTED`. The adapter never reports a
   GitHub sync or authorizes remote writes.

Read-only startup inspection returns `ABSENT`, `EMPTY`, `READY` or
`RECOVERY_REVIEW`. A committed `SENDING`, `UNCERTAIN`, or `CONFLICT`
operation remains untouched and requires reconciliation; startup never
silently retries the remote operation or fabricates a readback ACK.

## HOW TO USE

CI only, with synthetic task records:

```sh
python3 tests/tasks/test_experimental_task_sqlite_store.py
```

Tests explicitly provision disposable `tempfile.TemporaryDirectory`
locations. No desktop commands, production database path, running Quickshell
changes, or user data migrations are part of M10j.

## VERIFY

- Read-only access to missing storage does not create a directory or DB.
- A full v2 snapshot, project/task indexes, and one GIT pending operation are
  committed together, reopened and compared across transactions.
- A subsequent stale update is refused using revision and file-content hash.
- Test-injected exceptions at SQL transaction boundaries roll back every
  table before commit. After-commit exceptions produce an uncertain caller
  result, but restart reveals the exact committed state.
- Startup observes committed SENDING and blocks future remote dispatch.
- Invalid model versions, extra fields, bogus remote-reference shapes and
  corrupt projected indexes fail closed.
- NORMAL-only updates remain local, without creating GitHub intents.
- Ownership/private directory permissions follow the TimeW precedent.

## WATCH OUT FOR

**This is still a prototype**, not production-ready or mounted. The current
`ApolloHubTodoStore.qml` remains the *only* live TASKS writer. This Python
file deliberately has no active QML call site or user-facing invocation.
The chosen future path `~/.local/share/post-apollo/tasks/tasks.db` is a
proposal, not an actively created database.

The source snapshot remains the canonical record in this first SQLite slice;
indexes are derived and integrity-checked. Consequently a commit still
rewrites the complete model and its indexes. This does **not yet** realize
record-level SQLite scalability or a finalized normalized relational schema.
A later milestone must evaluate whether to make normalized records
authoritative while preserving the M10h versioned import/export contract.

M10h's JS policy remains the canonical application contract. The Python
validation is intentionally stricter at the storage boundary but not
yet proven equivalent for every possible input. Full cross-language parity,
real Quickshell Process integration, backup restoration, database schema
upgrades, WAL checkpoint/backup procedures, worker lifetime/lock ownership,
physical power-loss simulation, and operator acceptance remain required.

SQLite transactions cover **local** state and journal atomicity. They cannot
atomically commit an external GitHub API operation; remote reconciliation
still requires independently verified identity, baselines, permissions,
conflict detection and readback. A committed `PENDING` queue item does
not automatically grant remote write authorization.

Do not mix TASKS with `hospital.db`, `operations.db`, or `machine.db`.
The latter are independently owned data domains. Reuse patterns and helper
structure only.

## CHECKLIST

- [x] Record operator selection: Option B // SQLite
- [x] Confirm TimeW/PX SQLite precedents and existing live TASKS writer
- [x] Create test-only SQLite v2 snapshot + indexes adapter
- [x] Atomic task+pending-operation transaction and stale-source gate
- [x] Explicit startup inspection with uncertain-remote operation blocking
- [x] Synthetic crash-window, read-only and corruption tests
- [ ] Scoped GitHub CI verification and independent source review
- [ ] Operator-authorized PR merge
- [ ] Full schema parity, true normalized records and single-writer lifecycle
- [ ] Disposable backup/restore plus DB migration dry-run
- [ ] Separate operator authorization for live Quickshell migration/activation

## NEXT

**M10k:** cross-language schema parity and a service boundary compatible with
Quickshell's Process helper. Compare snapshot+indexes with normalized tables
and decide a safe incremental cutover, without changing the existing shared
writer or Proxy 2's scheduling controls.

## DECISIONS

SQLite selected; a standalone TASKS database will be used rather than
sharing Hospital/MACHINE/PX Operations databases. Current approval does
**not** authorize local file mutation, Quickshell restart, task migration,
GitHub sync, or production activation.

Proxy 1 owns storage and migration; Proxy 2 retains PLANNER. No shared QML,
`services/hub/ApolloHubTodoPolicy.js`, GitW or live Task widget files edited.
