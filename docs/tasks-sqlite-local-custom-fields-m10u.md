# 🏥💜 TASKS M10u // LOCAL Custom-Field SQLite Parity

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 TASKS storage continuation under operator-approved successor  
**Status:** Test-only, unmounted Python adapter using private disposable SQLite v2 fixtures  
**Authority:** SQLite selected as future target. The live JSON-backed TASKS writer is unchanged.

## IMPLEMENTATION

PR #735 (M10t NORMAL project lifecycle) has merged. M10u adds
`services/projects/ExperimentalTaskSqliteCustomM10u.py`, a test-only
composition of the existing M10s guarded SQLite transaction primitive.

Two new entrypoints match the existing M10h `UnifiedProjectModelV2.js`
**local-only** semantics, without extending remote authority:

- `add_local_field` adds a typed field definition to a NORMAL or GIT project.
  It enforces unique local labels, the existing per-project field count, safe
  generated field IDs, kind (`text`, `number`, `boolean`, `date`), and
  `scope:"local"`. Fields do **not** become GitHub ProjectV2 field mappings.
- `edit_local_value` updates a task's typed local value in the same
  project. The task may belong to NORMAL or GIT, with remote identity metadata
  left untouched. It verifies the declared local field type, rejects invalid
  values and no-op edits, and preserves all other values and task details.

Every operation checks the caller's **revision and full model hash inside
`BEGIN IMMEDIATE`**, validates the entire new model, writes only the
relevant SQLite project or task record plus metadata, commits, and verifies
readback. A post-COMMIT failure has an **uncertain** result requiring a new
read, not automatic retry. Changes to fields/values do not append
`operations`, change `nextOperationId`, dispatch GitHub requests, grant a
remote ACK, or convert local-only fields to remote fields.

M10u also declines local mutation when existing operations are
`SENDING`, `UNCERTAIN`, or `CONFLICT`. Those states require separate
recovery review. Legitimate `PENDING` operations are retained in their
original order and content when an independent custom value changes.

This does **not** remove M10t's restrictions on deleting NORMAL projects
with custom field definitions. Removing that project could discard definitions
needed to interpret its tasks; no safe archive/transfer policy has been
approved.

## HOW TO USE

No live desktop action is needed. GitHub CI uses only private temporary
fixtures:

```sh
python3 tests/tasks/test_task_sqlite_m10u_custom_fields.py
```

The experimental adapter has no CLI, background service, default tasks.db
path, migration, network transport, Quickshell import or live activation.

## VERIFY

- A GIT project accepts `scope:"local"` definitions without remote intent.
- Typed text/number/boolean/date and null values persist correctly.
- Existing remote identity shapes and pending intent records are unchanged.
- Invalid types, duplicate labels, no-op edits, unknown IDs, and stale
  revisions/timestamps refuse mutation.
- Before-COMMIT interruption leaves an unchanged model and counters.
- After-COMMIT interruption is resolved by a fresh SQLite read, not a retry.
- Existing `PENDING` intents survive local edits; `SENDING` blocks writes.
- SQLite integrity and foreign-key checks pass.
- M10s/M10t and relevant older regression suites rerun on the PR.

## WATCH OUT FOR

A project holding local field definitions cannot currently be deleted without
a separate schema/value retention policy. GIT project rename/delete, task
create/delete, and managed standard-field edits also require reviewed
identity and operation-journal rules. **Local-only does not imply remote sync
permission.**

Test-only SQLite functionality is not equivalent to a production write bridge:
Quickshell writer admission, snapshot parity, real OS/process behavior,
power-loss durability, backup/restore and operator-approved migration remain
outstanding.

## CHECKLIST

- [x] Verify merged M10t and canonical local-only field policy
- [x] Implement isolated typed field definition and task value writes
- [x] Preserve pending GIT journal and remote metadata without dispatch
- [x] Refuse ambiguous remote states and stale/invalid writes
- [x] Exercise fault injection and new-read reconciliation
- [ ] CI completion and independent source review
- [ ] Explicit approval for experimental PR merge
- [ ] Resolve custom-field project-delete retention design
- [ ] Review GIT standard-field mutation and offline intent policy
- [ ] Real Quickshell writer/snapshot parity and recovery gate
- [ ] Separate operator-approved live backup, migration and activation

## NEXT

M10v should address GIT-linked **standard field** edits and the transactional
offline-intent contract without enabling any network dispatch, then map the
remaining production host and snapshot-compatibility gaps. A future
custom-field deletion/archive design must not discard project field schemas
or task-local values without an explicit, verified preservation path.

## DECISIONS

The current `ApolloHubTodoStore.qml` is still the sole live TASKS writer.
No active TASKS data, Qt/QML UI, GitHub Projects, local machine, or Hospital
registration is modified by this milestone.
