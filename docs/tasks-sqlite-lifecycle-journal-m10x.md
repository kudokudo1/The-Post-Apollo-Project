# 🏥💜 TASKS // M10x Isolated Durable Lifecycle Review Journal

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 storage continuation by Proxy 2, external Hospital-compatible  
**Dependency:** M10w PR #754 is still under review; M10x is stacked on its head  
**Status:** Explicit, standalone SQLite **test-only fixture**, not TASKS storage activation

## IMPLEMENTATION

M10w adds strict *in-memory* previews for three future GIT-linked lifecycle
actions: `CREATE_GIT_TASK`, `DELETE_GIT_TASK`, and `MOVE_GIT_TASK`.
These cannot be represented in the existing record-authoritative v2
`operations` table, which only supports field edits with live-task foreign
keys. In particular, deleting a task would invalidate the journal's only
task reference unless a tombstone can outlive the task.

M10x introduces `ExperimentalTaskLifecycleJournalM10x.py` as a **completely
separate and manually initialized** SQLite fixture, named exactly
`lifecycle-test.db`. It neither modifies the v2 `tasks.db` schema nor
imports into any QML production code. It has no CLI, auto-initializer, user
data path, remote transport, service, daemon, or system activation.

Fixture version `3` is **not** production v3 nor a migration of existing
storage. It has three tables:

- `meta`: synthetic fixture version, journal revision, next independent
  `lxN` ID, and previous-entry head hash.
- `intents`: append-only copies of a fully reviewed M10w source v2
  document, exact review preview, dependencies, synthetic HELD state,
  previous hash and record digest.
- `tombstones`: retained complete `taskBefore` snapshots for
  `DELETE_GIT_TASK`, independent of the task's future existence.

`initialize` requires an explicit, nonexistent `lifecycle-test.db`
under a previously created private directory. `append_held` requires
the exact existing fixture revision and head hash, a fresh validated v2
model, its matching M10w preview, and any explicit dependencies. It verifies
the entire existing chain under `BEGIN IMMEDIATE`, inserts a new held
record plus a deletion tombstone if needed, updates metadata, then commits
the whole unit. Post-commit readback verifies the chain.

Stable `lxN` fixture IDs never masquerade as v2 `opN` reservations.
Every previous held operation for the same task must be named in the new
record's dependency list. A proposed deletion is terminal: later lifecycle
proposals for that task are refused. Out-of-order and unknown dependencies
fail closed. Global append order is stable.

Every persisted intent remains `HELD`, **never** `PENDING` / `SENDING`
or dispatchable. This fixture provides **no state transition to remote
sending or acknowledgement**, no GitHub API calls, no actual task deletion,
and no new authority. Cross-project moves or deletes based on another held
proposal still need fresh verified identity and source-state revalidation
in a future, separately authorized executor. A hash chain detects
accidental corruption but is **not** cryptographic authentication against
a writer that can rewrite the database.

## HOW TO USE

CI-only by default:

```sh
python3 tests/tasks/test_task_git_lifecycle_m10w.py
python3 tests/tasks/test_task_lifecycle_journal_m10x.py
```

The tests use disposable temp directories with independent private fixture
files. No real user TASKS file or `tasks.db` path is opened, created or
migrated. The module has no default path and no implicit startup work.

## VERIFY

The test suite asserts:

- Explicit initialization, strict private `lifecycle-test.db` filename,
  no implicit database creation and no second initialization overwrite.
- All three M10w intent types can be inspected without mutating the v2
  source document or touching remote service interfaces.
- Stable unique IDs and an append-only total order with explicit same-task
  dependencies. Unknown, duplicate, missing or post-deletion dependencies
  are refused.
- A `DELETE_GIT_TASK` record and its complete tombstone are saved in the
  **same transaction** and survive reopening from disk.
- Stale revision/head, edited preview, mismatching source model and
  unrelated request shapes are rejected before mutation.
- Injected failures before the new intent, after its insert, after its
  tombstone insert, before COMMIT and after COMMIT. Precommit failures
  roll back the **entire** record and tombstone; postcommit exceptions
  demand a fresh read and reject stale retry.
- Tampered tombstone content, SQLite integrity and foreign-key checks
  fail closed rather than resetting to empty.
- All saved states remain HELD with remote authorization false.
- M10w, M10v, M10u, M10l and M10r regression suites remain green.

## WATCH OUT FOR

**This is a durable *test fixture*, not a durable *production lifecycle
journal*.** Synthetic SQLite transaction and restart/reopen tests are not
proof of physical power-loss durability, hostile database tamper resistance,
real Quickshell process lifecycle correctness, GitHub identity, remote API
permissions, idempotency or conflict recovery.

Remaining critical work:

1. Define and approve a real versioned lifecycle schema and migration,
   including tombstone retention, dependent edits, create idempotency,
   remote deletion vs archive and project-move semantics.
2. Reconcile the two journal families. The existing v2 field `opN` queue
   is distinct from the experimental lifecycle `lxN` fixture. They are
   **not** safe to concatenate or send without an atomic design.
3. Verify owner-selected global ordering, restart uncertainty and remote
   baseline/identity/permission gates, followed by independent transport
   review. Never send a held record automatically.
4. Implement and prove complete Quickshell snapshot parity, single-writer
   handoff, restart recovery, backup/rollback and operator-controlled
   migration **before** moving the live JSON FileView writer.
5. Do not mount any experimental M10x code in `shell.qml`,
   `ApolloHubTodoStore.qml`, `TasksW.qml`, GitW or PLANNER.

## CHECKLIST

- [x] Inspect M10w PR state and strict v2 ownership boundaries
- [x] Add independent review-only lifecycle SQLite fixture
- [x] Record durable tombstones and explicit dependencies
- [x] Preserve v2 source and remote identity shapes
- [x] Add transactional failure/recovery and tamper tests
- [ ] Complete CI and independent source review
- [ ] Merge M10w separately with operator authorization
- [ ] Rebase/retarget M10x onto merged M10w, then operator review and merge
- [ ] Approve future lifecycle schema semantics and remote policies
- [ ] Complete production writer admission and migration acceptance

## NEXT

M10y should start with **read-only Quickshell snapshot parity and admission
rehearsal**, or an independently reviewed unified journal migration
proposal. Do not expand M10x into a live writer or remote executor
merely because its isolated tests pass.

## DECISIONS

No local desktop changes, live TASKS edits, real SQLite cutover,
GitHub Projects writes or live Hospital registration occurred.
This is a separate stacked PR until M10w is merged. JSON remains the
sole live TASKS authority.
