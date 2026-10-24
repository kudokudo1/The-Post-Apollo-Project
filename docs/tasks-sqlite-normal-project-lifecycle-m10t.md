# 🏥💜 TASKS M10t // NORMAL Project Lifecycle

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 storage continuation under operator-approved successor  
**Status:** Explicitly isolated, synthetic SQLite v2 operations. **Not the live TASKS writer.**  
**Decision:** SQLite is the future target; JSON remains authoritative until separately approved cutover.

## IMPLEMENTATION

M10s merged as PR #732. M10t adds `services/projects/ExperimentalTaskSqliteProjectsM10t.py`,
an additional test-only adapter composing the existing M10s `_transaction`
with the M10l record-authoritative SQLite v2 schema.

- `rename_normal_project` updates a NORMAL project's name and monotonically
  increasing timestamp, refusing invalid/conflicting names and GIT projects.
- `delete_normal_project` requires `confirmed is True`, verifies the
  current project and all assigned tasks, changes their `projectId` to
  `null` and their `updatedAtMs` monotonically, then deletes the project
  record, **all in one `BEGIN IMMEDIATE` transaction**. The task records
  remain present and keep the same IDs, title, completion, priority,
  description, due date, created timestamp, and other unrelated content.
- Deletion is deliberately refused if the project has local custom field
  definitions, tasks contain custom values or remote references, project/task
  journal operations exist, or a GIT project is involved. Data that cannot
  yet be safely detached is **not silently discarded**.
- Both operations verify expected revision **and full model hash** before any
  write, advance revision by one, verify complete readback, and never
  authorize remote operations.
- A small fix in M10s `create_normal_project` allocates SQLite row
  `position` using SQL's maximum surviving position after deletion;
  project IDs remain monotonic through `nextProjectId`.

None of these files are imported by `shell.qml`,
`ApolloHubTodoStore.qml`, TASKS, PLANNER, GitW, or the M10q QML test bridge.
The module takes explicit caller-supplied private disposable `tasks.db` only,
with **no default data path, CLI, background service, migration or remote API**.

## HOW TO USE

GitHub CI, without touching any real user data:

```sh
python3 tests/tasks/test_task_sqlite_m10t_project_lifecycle.py
python3 tests/tasks/test_task_sqlite_m10s_normal_crud.py
```

M10t uses temporary private SQLite fixture databases and the existing
isolated M10l schema validator. No manual desktop step is needed.

## VERIFY

The new tests assert:

- Rename success, timestamp and ID preservation; duplicate names refused.
- NORMAL/GIT isolation, invalid and stale inputs, unconfirmed deletion refused.
- Fault before COMMIT rolls back project removal **and task detachment**.
- Successful deletion detaches multiple assigned tasks without losing their
  content or deleting their records.
- Deleted project IDs are not reused; the next project can be appended safely
  even when SQLite `position` numbers have gaps.
- Post-COMMIT simulated interruption requires fresh-read reconciliation.
- Project custom definitions and task custom values refuse unsafe deletion.
- SQL `PRAGMA foreign_key_check` and `integrity_check` remain clean.
- M10s/M10l/M10r/M10n regressions rerun in the scoped workflow.

## WATCH OUT FOR

**Not full API parity.** NORMAL project deletion with custom field metadata,
GIT project lifecycle, remote identity and intent journaling, complete
production read snapshot, QML single-writer admission, restart rearm, real
backup/restore and safe on-device migration are unresolved.

**Do not use the experimental module on the user's TASKS database.** It has
no runtime admission authority and does not freeze the live FileView JSON
writer. CI process fault injection is not evidence of real power-loss
durability.

## CHECKLIST

- [x] Confirm M10s is merged in GitHub and M10r remains test-only
- [x] Add isolated NORMAL project rename/delete with explicit confirmation
- [x] Preserve task records, dates, IDs and counters when detaching
- [x] Reject GIT, custom data, journal and stale input
- [x] Add failure-injection, rollback, readback and integrity tests
- [ ] Finish CI and independent source review
- [ ] Operator-authorized PR merge
- [ ] Design a safe choice for custom field handling
- [ ] Complete GIT linked mutation and offline-intent semantics
- [ ] Finish production snapshot/write bridge and live runtime acceptance
- [ ] Separately approve backup, migration, rollback and activation

## NEXT

M10u should extend remaining task/project parity carefully around custom
values and GIT-owned metadata, with no remote API sending or implicit
sync. A fully audited production QML bridge must precede any SQLite cutover.

## DECISIONS

No local machine write, real task mutation, startup change, new writer
activation, remote GitHub Project write or live Hospital registration was
performed. JSON continues as sole live TASKS authority.
