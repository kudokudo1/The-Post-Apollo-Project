# 🏥💜 Proxy 1 // M10l Record-Authoritative SQLite

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Owner:** Proxy 1; external development assignment, no live Hospital registration.  
**Operator decision:** TASKS storage Option B // SQLite.  
**Dependency:** M10k PR #649 was draft/unmerged when M10l branched.  
**Status:** Isolated schema-v2 Python prototype and synthetic CI only.

## IMPLEMENTATION

M10j used SQLite schema-v1 with an entire versioned JSON snapshot as the
authoritative data and indexed tables rebuilt for every edit. M10l creates a
**separate, unmounted** `ExperimentalTaskSqliteRecordsV2.py` to evaluate
record-authoritative SQLite writes without silently altering the older
prototype or any production user data.

New SQLite `user_version=2` (distinct from M10h **model version 2**) stores:

- A `meta` row with model schema version, revision, next-task/project/op IDs
  and SHA-256 of the canonical reconstructed versioned model.
- A `projects` row per project, with stable ID, position, name, family,
  timestamps, JSON-encoded typed field definitions and shape-only remote
  reference.
- A `tasks` row per task, with stable ID, position, project foreign key,
  editable task values, dates, timestamps, optional remote reference, and
  JSON-encoded typed **local-only** values.
- An `operations` row per GIT intent, with stable ID, task and project
  foreign keys, before/after values, created revision, state and ack token.
  Pending intents are merely local evidence, never dispatch authorization.
- Indexes for due date, project association and operation state.

A new synthetic test database can only be initialized explicitly in a
pre-existing private directory at a caller-provided absolute `tasks.db`
path; no default `XDG_DATA_HOME` or runtime path exists. Initializing an
existing file is refused rather than attempting an automatic migration.

`edit_task()` acquires SQLite's `BEGIN IMMEDIATE` lock and checks the
**current revision and canonical model hash** before any edit. It updates
the one target task row, appends one operation row for a GIT task edit,
and advances revision / operation ID / checksum in the meta row, all within
**one SQLite transaction**. For NORMAL tasks, no operation row is appended.
The commit only reports `LOCAL_COMMITTED` after checking the reconstructed
model against the expected candidate. For injected exceptions before COMMIT,
the whole SQL transaction rolls back. If COMMIT already happened, the
caller must reopen the DB and reconcile instead of retrying blindly.

`transition_local_operation()` permits bounded LOCAL journal state
transitions for synthetic tests, preserving blocking `SENDING`,
`UNCERTAIN` and `CONFLICT` states across restart. It deliberately has
**no remote ACK transition** and never calls GitHub.

`read()` reconstructs the complete M10h-shaped model from SQL records
inside a consistent WAL snapshot, validates it with M10j's strict Python
validator and checks the persisted SHA-256. It reports READY or
RECOVERY_REVIEW. It does not attempt repair or automatic operation replay.

## HOW TO USE

GitHub CI only:

```sh
python3 tests/tasks/test_task_sqlite_records_v2.py
```

CI creates disposable private temporary directories. The M10l module has no
CLI, no active QML importer, no default file path and no user-facing writer.

## VERIFY

- Versioned model import -> SQL records -> model reconstruction round-trip
  with task/project IDs, timestamps, custom values and GIT reference shape.
- Trigger guards make DELETE-and-rebuild of projects/tasks/operations fail.
- GIT task edit atomically changes its row and appends one PENDING operation.
- NORMAL task edit changes due date without making a GIT operation.
- Stale revision or source hash, no-op edit, and backward time are rejected.
- Interrupted edits before COMMIT roll back; after-COMMIT fault requires
  readback and yields complete committed task + journal records.
- Explicit local operation-state transition also commits atomically;
  reopening SENDING/UNCERTAIN yields RECOVERY_REVIEW without remote ACK.
- Corrupt records fail checksum validation rather than auto-fixing them.
- Existing M10j schema-v1 files are rejected, **not migrated implicitly**.
- Calling edit against absent storage must not create a database.
- M10k cross-language parity, M10j SQLite, M10h model and TimeW SQLite
  regression tests are rerun by scoped CI.

## WATCH OUT FOR

This does **not** implement a production migration, Quickshell Process writer
or full schema. Individual task/operation/project records are authoritative,
but some structured nested metadata still resides in JSON columns. The
format is intentionally separate from schema-v1 until an operator-authorized,
byte-verified backup/restore and migration strategy is proven.

Although SQL handles multi-row transactions, an offline task intent is not
an atomic GitHub API write. A local PENDING or SENDING row cannot prove a
GitHub item identity, network acknowledgement or conflict-free operation.

SQLite WAL transactions/rollback are tested with in-process fault injection
and reopen tests, **not physical power-loss or filesystem corruption tests**.
Actual desktop permissions, Quickshell runtime, process lifecycle, backup,
WAL checkpoint behavior, encryption and production acceptance are still
unverified.

This prototype includes task edits and local journal transitions only.
More task operations, project management, custom field changes, schema
migration and data import/export require separately reviewed APIs.

`ApolloHubTodoStore.qml` remains the **sole live TASKS writer**.
Proxy 2's scheduling pane and current TODAY, PLANNER and Apollo Hub UIs
continue using it unchanged.

## CHECKLIST

- [x] Verify current repo, PR #649 draft dependency, and owner boundaries
- [x] Add separate normalized SQLite schema version 2
- [x] Persist local task edit + GIT pending intent in one SQL transaction
- [x] Reject stale writes, auto-migration and invalid/corrupt storage
- [x] Preserve startup recovery blockers with no automatic remote retry
- [x] Synthetic interruption tests and per-record update regressions
- [ ] CI passing, independent review
- [ ] M10k dependency merge, or reviewed PR retarget
- [ ] Operator-authorized M10l merge
- [ ] Real Qt/Quickshell runtime and backup/restore acceptance
- [ ] Separate operator authorization for production task migration

## NEXT

M10m proposal: reconcile the schema-v1 and schema-v2 experiments, complete
cross-language parity and design a **read-only legacy-to-SQLite migration
preview**, with durable backup and rollback gates. Actual activation still
requires a separate, explicit operator decision.

## DECISIONS

SQLite remains selected. No shared QML, active task JSON, GitHub Projects,
TimeW, Hospital databases, local machine, or production writer changed.
This is not live Hospital registration or remote authorization.
