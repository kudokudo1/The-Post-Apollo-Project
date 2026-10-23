# TASKS // PROXY 1 M10b: Offline Journal Prototype

**Status:** Isolated contract prototype, NOT an active storage implementation.
**Patient:** `kudokudo1/The-Post-Apollo-Project`
**Owner:** Proxy 1, not registered in live Hospital.
**Parallel assignment:** Proxy 2 owns PLANNER and other isolated TASKS UI features.

## Scope and mechanism

New pure policy: `services/projects/OfflineOperationJournal.js`

The prototype defines a versioned single-envelope shape:
- `version: 1`: **prototype envelope version**, NOT a live Todo v4.
- `revision`: monotonic local operation / state-change revision.
- `projects`: simplified `{id,name,family}` records with `normal` or `git`.
- `tasks`: simplified compatibility fields (local `tN` IDs, project assignment,
  title, done, priority, description, due date).
- `operations`: durable-intent *candidates* for GIT edits, with stable `opN`
  IDs, local task/project ID, changed field, before/after, creation revision,
  status, and a receipt token only for acknowledged operations.

`localEdit(envelope, request)` yields a new envelope in memory. NORMAL project
edits alter local task data but append no outbound operation. GIT edits change
the local task and append a `PENDING` intent within the same proposed commit
unit. The original input is not mutated.

The policy never persists anything. An eventual writer MUST atomically commit
the **entire** returned envelope before claiming "SAVED LOCAL" or starting a
remote operation. A FileView's `atomicWrites` property on one file is NOT an
atomic transaction spanning unrelated model + queue files.

## State contract

```text
PENDING --begin--> SENDING
SENDING --uncertain--> UNCERTAIN
SENDING --conflict--> CONFLICT
SENDING --acknowledge(verified receipt)--> ACKNOWLEDGED
UNCERTAIN --conflict--> CONFLICT
UNCERTAIN --acknowledge(after read-back)--> ACKNOWLEDGED
```

- Restart recovery converts persisted `SENDING` to `UNCERTAIN`; save the
  recovery envelope before further activity. No blind retries.
- `nextIntent()` is globally ordered for this conservative prototype.
  `UNCERTAIN`, `CONFLICT` or `SENDING` block later dispatch until resolved.
- `begin` is a **local journal transition only**. It does not provide
  authorization for sending. A future Git-owned adapter must independently
  authenticate/authorize, resolve verified ProjectV2/item IDs, read fresh
  remote baselines, ensure no conflict, and durably record SENDING before
  any outbound operation.
- `acknowledge` accepts a nonempty receipt-shaped string, not raw remote
  verification. ONLY a future verified adapter may legitimately supply it.
  There is no actual evidence check in the pure prototype.
- The design intentionally has no conflict resolution, queue compaction,
  repair/retry button, migration, daemon, polling, remote write, or deletion
  propagation. Those require separate design and operator acceptance.

## Crash-window requirements for the eventual storage adapter

| Boundary | Required behavior |
|---|---|
| Before local commit | Old local task and queue remain; do not call edit saved |
| After atomic local edit+intent commit | New local task and PENDING operation both survive restart |
| Before remote send | Persist SENDING intent; verify remote identity and latest baseline |
| During remote send or response loss | Mark UNCERTAIN on reload, never assume failure or success |
| After remote confirmation | Persist ACKNOWLEDGED and read-back token, advance baseline |
| During reconciliation | Re-read remote before choosing ACKNOWLEDGED, CONFLICT, or a separately approved retry |
| Invalid/unknown version | Fail closed and preserve original bytes; no reset to empty |

## Storage-engine choice remains open

The journal tests simulate `JSON.stringify/parse` roundtrips. They do NOT
simulate actual fsync, power failure, file rename durability, concurrent
processes or on-device crashes.

A later benchmark and failure-injection suite will compare a single atomic
versioned JSON envelope and an actual transactional engine (such as SQLite,
if its deployment and Quickshell interop are acceptable). Select only after
crash semantics, backup/restore, performance, and migration are verified.

The existing `ApolloHubTodoStore.qml` remains the ONLY live task writer.
The current v3 parser/clone still drops unknown keys; **never add the journal
to the live v3 JSON** without a validated migration and explicit operator
approval. Maintain old TODAY, PLANNER and Apollo Hub projections throughout.

## Tests

Run:
```sh
node tests/tasks/test_offline_operation_journal.cjs
```

Tests cover NORMAL edits without a remote intent, GIT edit + pending in a
single envelope, immutable revision change, serialize/reload behavior,
ordered dispatch, interrupted-send recovery, blocked uncertain retries,
syntactic receipt acceptance, malformed/unsupported version refusal,
invalid references and bounded queue capacity.

## Coordination

- Proxy 1 owns this pure service prototype, future store/migration design,
  GitHub read bridge and synchronization engine.
- Proxy 2 owns PLANNER/QML. PLANNER only needs current read-only task snapshot;
  no changes to its existing files or API.
- No changes to GitW, GithubProjectsService, ApolloHubTodoStore, TodoPolicy,
  TasksW, shell, shared UI, on-disk storage or accounts in M10b.
- Repository changes require operator-reviewed merge; live local-machine
  migration/activation requires separate explicit approval.

## Next verification milestones

1. GitHub CI contract validation and independent review.
2. Recovery semantics review: ambiguous write outcomes and non-idempotent
   operations especially creation/deletion.
3. Evaluate persistence strategies using isolated throwaway fixtures.
4. Design v3-to-new-model dry-run migration and rollback, preserving all
   existing records and projection compatibility.
