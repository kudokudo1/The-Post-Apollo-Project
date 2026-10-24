# 🏥💜 TASKS M10w // GIT Lifecycle Intent Contract (Review Only)

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 TASKS storage continuation, current browser doctor Proxy 2  
**State:** Proposed lifecycle intent format, NOT persisted, NOT executable  
**Sources:** merged M10v field journal, v2 model validator, GitHub mapping policy  
**Live authority:** JSON-backed `ApolloHubTodoStore.qml` remains unchanged

## IMPLEMENTATION

The existing SQLite v2 `operations` table and `UnifiedProjectModelV2.js`
validator recognize **only standard-field edits** (title, done, priority,
description, dueDate), with `before`/`after` values, live task/project
foreign keys and increasing `createdRevision`.

Those invariants make create/delete/reassignment unsafe to encode as fake
field edits. A create intent can precede remote item identity; a delete may
need to outlive a locally deleted task; a reassignment can change project
identity and invalidate pending operation foreign keys or local custom values.
Do not weaken the current v2 validator just to squeeze those into it.

M10w adds `services/projects/ExperimentalTaskGitLifecycleM10w.py` as a
**pure review-only proposal contract**. It accepts a strictly validated v2
document plus one narrow lifecycle request, producing a copy of relevant
records and the unresolved prerequisites. No filesystem or database writes,
SQL, network, GitHub connector calls, background tasks, QML imports or
production service changes occur.

| Proposed intent kind | Review preconditions | Essential future retention |
|---|---|---|
| `CREATE_GIT_TASK` | Existing locally saved GIT task with no remote item reference; no unresolved same-task field intents | Stable local task ID and entire source task, not a guessed remote ID; idempotency and dependent edits |
| `DELETE_GIT_TASK` | Existing remote-shaped GIT task; explicit `confirmed=True`; no unresolved same-task field intents | Tombstone/snapshot and remote identity; **archive vs permanent delete** policy still undecided |
| `MOVE_GIT_TASK` | Existing remote-shaped GIT task, different target GIT project; no custom values or unresolved same-task intents | Source and target identity, data mapping, move/rollback semantics; no cross-family auto-relink |

The proposal has `previewVersion:1` and
`proposedJournalVersion:3`. These are **design labels**, not the active
SQLite schema/version. It captures the exact baseline revision and model
hash, immutable-in-practice task snapshot, source and target remote-reference
SHAPES, ordered existing operation IDs, and a suggested `opN` candidate.

**The suggested op ID is NOT allocated or reserved.** Multiple proposals
against the same unchanged v2 state can show the same suggested ID.
A future transactional writer must do allocation itself.

The preview also includes explicit `requiredGates`:
versioned journal migration, explicit operator approval, fresh verified remote
identity and baseline, verified permissions and remote readback, and
kind-specific idempotency/restart/rollback policy.

Every preview is marked:

- `status: REVIEW_ONLY`
- `localWriteAuthorized: false`
- `journalWriteAuthorized: false`
- `remoteWriteAuthorized: false`
- `remoteSent: false`
- `remoteAcknowledged: false`

`fingerprint` is a plain SHA-256 integrity hint over the canonical preview,
**NOT a signature, identity proof, permission or persistence receipt**.
`review_current` regenerates the preview against a fresh validated source
model and refuses stale/tampered inputs. Even a positive result never
authorizes execution.

## Future journal schema questions, still undecided

A future M10x+ durable schema must separately define:

1. An operation kind discriminant and versioned, strictly validated
   kind-specific payload shape, not v2's standard `field` placeholder.
2. A stable op ID, local task ID, optional remote item identity, source and
   target project identities, caller-supplied remote baseline, and declared
   intent policy. No title-based identity inference.
3. Explicit dependencies to enforce **create before edit**, **edit before
   delete**, and safe project moves; deletion tombstones must survive removal
   of the task's live row without breaking foreign keys.
4. A strict total-order global dispatcher, durable one-time idempotency keys
   for remote creates, and blocked stages for incompatible or missing identity.
5. Persisted `PENDING` / `SENDING` / `UNCERTAIN` / `CONFLICT` /
   `ACKNOWLEDGED` with recovery evidence and verified remote readback.
   Restart must never transform ambiguous create/delete into a blind retry.
6. Decisions on GitHub Projects' supported archive/delete/move APIs, remote
   item types, missing permissions, conflict UI, cross-family unlink, local
   custom field mapping, and whether task deletion keeps an audit record.
7. Schema migration, snapshot compatibility, backups, rollback, retained
   history, exact write locks, and physical-failure acceptance testing before
   replacement of the live JSON writer.

The existing GitHub mapping policy marks all remote identity and field
readiness as **unverified**. M10w does not elevate its previews into authority.

## HOW TO USE

No desktop actions required. Review the synthetic tests in GitHub:

```sh
python3 tests/tasks/test_task_git_lifecycle_m10w.py
```

The tests are pure: no fixture DB or real task data is created or opened.
The standalone proposed contract is not used by `shell.qml`,
`TasksW.qml`, `ApolloHubTodoStore.qml` or the experimental SQLite writers.

## VERIFY

Tests cover all three proposed kinds, exact request shapes, strict v2 model
validation, task/project identity boundaries, confirmation, custom value
transfer rejection, pending/sending/recovery dependencies, revision/counter
bounds, schema upgrades, stale/tampered review data, fingerprint consistency
and **unchanged source data**.

Existing M10v/M10u/M10t/M10s/M10l/M10r/M10n storage regression suites must
continue to pass. Passing source tests is not QML runtime or remote
authorization evidence.

## WATCH OUT FOR

This is a proposal and **not** a durable lifecycle journal. It does not
actually create, delete, reassign, archive, send, queue or acknowledge tasks.
It cannot safely be inserted in the existing SQLite v2 operations table.
The future transport is owned by the Git service only after verified
identity, permissions, and operator acceptance.

No real task data, SQLite database, app panel, desktop service, local
machine, GitHub Project or live Hospital state is modified by this milestone.

## CHECKLIST

- [x] Verify M10v merged, inspect v2 journal and mapping boundaries
- [x] Define strict separated lifecycle operation shapes, review only
- [x] Record recovery, ordering, tombstone and remote-policy dependencies
- [x] Add fail-closed synthetic tests for identity and stale proposals
- [ ] CI and independent source review
- [ ] Operator-approved PR merge
- [ ] Operator decisions on archive vs delete and cross-project moves
- [ ] Future versioned durable lifecycle journal/migration proposal
- [ ] Verified QML writer admission, snapshot parity and restart behavior
- [ ] Separate authorized live backup/migration/rollback and activation

## NEXT

M10x should implement an **isolated versioned lifecycle journal fixture**
with strict kind-specific validation, durable tombstones, cross-operation
dependency ordering and crash-window tests, without connecting it to
GitHub transport or the live JSON store. A separate track should advance
the read-only Quickshell snapshot bridge and writer handoff verification
before any SQLite activation.

## DECISIONS

SQLite remains the candidate future store, JSON remains the sole live writer.
Lifecycle intent policy is NOT accepted as a production schema merely
because this review contract is merged or CI passes.
