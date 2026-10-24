# 🏥💜 TASKS // M10s Guarded NORMAL SQLite Operations

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 TASKS storage continuation under operator-authorized successor  
**Status:** Experimental, isolated Python module with disposable SQLite test data only  
**Operator choice:** SQLite target; JSON remains the only live task writer

## IMPLEMENTATION

Adds `services/projects/ExperimentalTaskSqliteCrudM10s.py` as a test-only
extension to the M10l record-authoritative SQLite schema v2. It uses the
same `ExperimentalTaskSqliteRecordsV2.py` connection, strict schema
validator, model hash, transaction mechanism and existing database tables.

The following operations are now available *in the disposable test module*:

| Operation | Behavior |
|---|---|
| `create_task` | Creates a NORMAL/unassigned task **with an optional due date atomically**, preserving all defaults and stable IDs |
| `create_normal_project` | Creates a local NORMAL project with stable ID/timestamps; never infers GitHub identity |
| `assign_normal_project` | Changes an ordinary NORMAL/unassigned task's project association or clears it in one transaction |
| `edit_normal_task_details` | Edits priority, description and due date together as one record-level SQLite transaction |
| `remove_normal_task` | Explicit confirmed deletion, with no ID reuse and no deletion of journaled/GIT tasks |

Every write checks **both** the expected revision and full model hash inside
`BEGIN IMMEDIATE`, advances exactly one revision, validates the entire
candidate, updates a record and meta in the *same SQLite transaction*, commits
and verifies readback before reporting `LOCAL_COMMITTED`.

Faults before COMMIT roll back; injected faults after COMMIT remain ambiguous
and must be reconciled by a fresh `read()`. No automatic replay occurs.

All new operations refuse GIT project/task changes, pending-journal task
mutation, unsupported remote references or local custom values requiring
separate mapping semantics. The current M10l single-field GIT edit/journal
test remains unchanged and separate. The prototype never sends a remote
operation and never implies a pending intent was remotely acknowledged.

**This is NOT a production SQLite task writer.** The module has no CLI,
default database path, background loop, scheduler, QML import or local file
migration. It requires an explicitly initialized, privately owned disposable
`tasks.db`. The currently deployed `ApolloHubTodoStore.qml` still writes
`apollo-hub-todo-v1.json`.

## HOW TO USE

GitHub CI tests only:

```sh
python3 tests/tasks/test_task_sqlite_m10s_normal_crud.py
```

The tests create a private temporary database and do not access the real
TASKS JSON file or any production SQLite DB.

## VERIFY

The M10s tests cover:

- One-step creation with a valid due date, one revision and one stable ID.
- Rejection of invalid dates, empty titles, unknown or GIT project linkage.
- NORMAL project creation, unique names and monotonic counters.
- Task assignment, unassignment constraints and GIT isolation.
- Atomic multi-field details; original task/project metadata preserved.
- Stale baseline refusal.
- Fault injection before and after COMMIT and fresh-read reconciliation.
- Explicit confirmed deletion, nonreuse of IDs and positional uniqueness.
- No fabricated remote sync/ACK, SQLite integrity and foreign key checks.

Original M10l, M10r and M10n regressions run alongside the new test suite.

## WATCH OUT FOR

This module is deliberately restrictive. GIT-linked **creation, deletion,
assignment and multi-field edits** need verified remote identity/queue
policy, and arbitrary custom-value/project schema changes are not addressed.
Other legacy APIs still missing include NORMAL project rename/delete and
the deployed QML async writer contract.

The new multi-field edit is atomic for NORMAL tasks only; it does **not**
change PLANNER's live JSON behavior. The user interface still performs
separate ADD and SAVE DATE operations until a fully accepted cutover or a
separately reviewed update to the existing JSON store.

Do not import this module into production Quickshell, start a second writer,
change `ApolloHubTodoStore.stage()` or begin live migration on the
strength of synthetic tests alone.

## CHECKLIST

- [x] Confirm M10r merged and read M10l schema and policy
- [x] Add isolated NORMAL CRUD transaction module
- [x] Add atomic create-with-date and multi-field details
- [x] Preserve monotonic IDs and existing GIT task/journal records
- [x] Add interruption and rejection tests
- [ ] CI completion and independent review
- [ ] Operator-authorized PR merge
- [ ] Remaining project API and GIT intent semantics
- [ ] Production host + QML snapshot/single-writer parity
- [ ] Actual disposable on-device runtime acceptance
- [ ] Separate backup, migration, rollback and activation approval

## NEXT

M10t should extend NORMAL project rename/delete, handling task detachment
and custom-field preservation fail-closed, then address the GIT mutation
policy and complete unified snapshot parity. Only afterward should a
separate production writer handoff be considered.

## DECISIONS

SQLite remains the future target, **legacy JSON the live authority**.
No real task data, personal desktop, Hospital live assignment, remote
GitHub Project, or storage path is modified.
