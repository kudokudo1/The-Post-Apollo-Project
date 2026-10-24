# 🏥💜 TASKS M10v // Atomic GIT Standard-Field Intents

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** TASKS storage, continued under operator-authorized successor  
**Status:** Experimental, test-only SQLite v2 transaction adapter; not mounted  
**Live storage:** `ApolloHubTodoStore.qml` continues using the JSON FileView

## IMPLEMENTATION

M10u (PR #743) is merged. M10v introduces
`services/projects/ExperimentalTaskSqliteGitM10v.py`,
a single-purpose synthetic GIT-linked task standard-field editor.

The existing M10l `edit_task()` already supports one field per commit.
M10v supports several changed fields in **one SQLite transaction**, while
appending one PENDING offline-operation entry per changed standard field.

The v2 validator requires strictly increasing `createdRevision` values
for operation records. Accordingly, a three-field edit consumes **three
consecutive model revisions** and three stable operation IDs, even though
the SQL update to the task, three journal inserts, and metadata update
are **one COMMIT**. This is deliberate and does NOT claim a separate
commit happened for each revision.

Journal entries are allocated in the canonical `FIELDS` order:
`title`, `done`, `priority`, `description`, `dueDate`.
The input dictionary order does not change operation chronology.

The method:

- Requires an existing GIT-linked project and task, without inferring
  that their remote identities have been verified.
- Accepts only standard-field values passing the existing strict v2
  validators. Does not expose project assignment/create/delete.
- Guards both expected revision and full model hash after `BEGIN
  IMMEDIATE`, and validates the complete next model before commit.
- Preserves remote item/project metadata, task custom values, earlier
  pending operation records, operation IDs, order and counters.
- Refuses a write if ANY operation is `SENDING`, `UNCERTAIN`, or
  `CONFLICT` because unresolved remote effects demand recovery review.
- Refuses stale timestamps, no-op batches, invalid/unknown fields,
  exhausted revision or queue capacity, and non-GIT tasks.
- Returns `remoteSent:false`, `remoteWriteAuthorized:false` and
  `remoteIntentCreated:true` only after full readback verification.

**Recording an offline intent is NOT a remote ACK or permission to send.**
Nothing in M10v calls GitHub, dispatches a queued operation, retries an
uncertain request, or asserts verified remote item identity.

## HOW TO USE

No desktop action. The test module requires an explicit caller-supplied,
preinitialized disposable, private, absolute `tasks.db` path. GitHub CI:

```sh
python3 tests/tasks/test_task_sqlite_m10v_git_intents.py
```

No CLI, service, QML integration, default path, startup migration, or
production writer is added.

## VERIFY

The test suite covers:

- Three standard fields committed together with three uniquely ordered
  PENDING operations and a three-step revision advance.
- Deterministic operation order, stable IDs, before/after values and
  existing project/task remote metadata unchanged.
- A later batch coexisting with older pending operations without losing
  prior history or custom values.
- Full fail-closed rejection of NORMAL/unassigned tasks, invalid fields,
  invalid due dates, no-op batches, stale baselines or stale timestamps.
- Denial during SENDING/recovery-review states and no automatic retry.
- Failure injection before/after the task update and first/last operation
  insert, before COMMIT, and after COMMIT, with fresh-read recovery.
- SQLite integrity and foreign-key checks, database noncreation and
  absence of remote writer methods.
- The M10s, M10t, M10u, M10l, M10r and M10n regression suites remain
  required alongside the new M10v tests.

## WATCH OUT FOR

This does **not** implement GIT task/project creation, deletion, project
reassignment, remote identity verification, remote operation processing,
conflict reconciliation or full local/remote API parity. A future sync
executor must prove permissions, project item identity and remote baseline,
and reconcile any UNCERTAIN state before dispatching a PENDING operation.

The present journal schema only models field-level edits; extending it
to creation/deletion needs a separate versioned design and migration plan.
The model's multiple-revisions-per-atomic-batch rule must be understood
by downstream consumers before production use.

All test-only source checks and synthetic SQLite interruption tests do
not prove Quickshell runtime behavior or durability under physical power
loss. Any actual writer admission, data backup/migration/rollback and
production activation require separate operator authorization.

## CHECKLIST

- [x] Verify M10u merged
- [x] Preserve v2 per-operation revision invariant
- [x] Add atomic multi-field GIT edit and offline PENDING journal records
- [x] Guard stale, invalid, blocked and exhausted transaction paths
- [x] Add crash window and stable-order regression tests
- [ ] CI review and independent acceptance
- [ ] Operator-approved PR merge
- [ ] Design GIT creation/deletion/project operation schema
- [ ] Prove Quickshell writer admission, snapshot parity and restart recovery
- [ ] Verify actual backup/migration/rollback in a separate authorized phase
- [ ] Separate operator approval for real SQLite activation

## NEXT

M10w should inventory missing GitHub task/project mutation kinds and the
schema/protocol needed for a durable create/delete/reassign intent, **without
turning on transport**. Another track must complete the live snapshot/QML
single-writer protocol before cutover.

## DECISIONS

SQLite remains the future target; the active JSON file remains the only
live TASKS authority. No live machine, GitHub Project, real user task or
hospital registration was changed by this milestone.
