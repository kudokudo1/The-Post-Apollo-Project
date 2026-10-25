# 🏥💜 TASKS // M11a Read-Only Shadow Snapshot Parity

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 storage continuity, Proxy 2 successor under operator-approved repo development  
**Status:** Pure comparison library and GitHub CI tests. NO live integration.  
**Authoritative writer:** `services/hub/ApolloHubTodoStore.qml`, JSON FileView only.

## IMPLEMENTATION

M10y/M10z established an **unmounted** SQLite-v2 read-only snapshot
projection and optional disposable Quickshell testing. M10n already
provides a review of byte-exact backup and schema-v2 shadow database
integrity. M11a now fills a distinct remaining hole: **semantic side-by-side
legacy UI parity** between an externally verified JSON v3 document and
the separately observed schema-v2 SQLite read projection.

Adds `services/projects/TaskSqliteShadowParityM11a.js`, a pure,
unmounted comparison policy:

- Requires the existing deployed `ApolloHubTodoPolicy.validate` and
  `view` implementations for both documents.
- Accepts only the precise M10y read-only response schema, a positive
  existing-database result and stable `READY`/`EMPTY` source state.
  `RECOVERY_REVIEW`, absent/unavailable DB, blocked operations,
  unexpected fields, false revision/hash, or any claimed write
  authority fail closed.
- Compares project/task counts AND counters, project and task array order,
  **every** deployed v3 project/task field (IDs, titles, timestamps,
  completion, description, due date, priority, project assignment).
- Rechecks the actual derived snapshot task ordering, remaining/completed
  counts and per-project counts. A successful result offers the same
  snapshot in memory but forces `writable=false`.
- Divergence reports include **field labels/indexes only**, never changed
  task titles, descriptions, project names or their private contents.
- Always returns `activate:false`, `migrate:false`, `restore:false`,
  `writeReady:false`, `sqliteWriterAuthorized:false` and
  `legacyWriterFrozen:false`. A matching pair is named
  `MATCH_FOR_REVIEW_ONLY`, NEVER ready for a writer cutover.

This comparison does **not** make claims about observing two real stores
at the *same instant*. The legacy document must still be separately
captured with exclusive writer quiescence, recorded byte-level hash,
verified backup and operator-controlled readback. M11a accepts a document
from its caller but does not inspect or freeze the user's actual files.

## HOW TO USE

CI-only tests, using synthetic v3 JSON and a separate preinitialized
private `m10y-snapshot-test/tasks.db` fixture:

```sh
node tests/tasks/test_task_sqlite_shadow_parity_m11a.cjs
python3 tests/tasks/test_task_sqlite_shadow_parity_m11a.py
```

The Python test invokes M10z's disposable sample generator and the
M10y read-only Python subprocess probe, and feeds its response to the
actual deployed JS policy in Node. No real user TASKS file or desktop
process is inspected or modified.

## VERIFY

- Identical JSON and SQLite-derived v3 UI records match for review only.
- Same-count mismatches in title, due date, priority, description,
  completion, timestamps, project links and array ordering are rejected.
- Source revision, counters and source-read metadata are checked.
- Empty but existing SQLite is distinguished from missing/error states.
- Pending recovery or unverified SQLite reads cannot pass.
- A normal synthetic SQLite edit after the initial match results in
  divergence against the unchanged legacy source.
- Every result denies activation, writes, migration and rollback.
- M10y, M10z and M10n regressions run alongside new tests.

## WATCH OUT FOR

Matching projected v3 fields proves only compatibility for the reviewed
synthetic observation. It does NOT preserve or authorize **remote
identities, custom field values, separate GIT lifecycle journal states,
unified writer authority, physical durability or on-device QML runtime**.
Those fields are deliberately outside the legacy UI projection and must
be independently verified before any production upgrade.

The returned snapshot may contain task titles and descriptions in
memory so TODAY/PLANNER can render it. Do not log or transmit such
snapshots to external tools; only diagnostic difference labels should
leave the comparison layer.

M10z's native on-device Quickshell read/cancel/reload acceptance remains
pending. M11a cannot substitute for that runtime gate. A future writer
handoff must prove a persistent, atomic JSON stage gate and one
exclusive SQLite owner before it is ever eligible for activation.

## CHECKLIST

- [x] Verify GitHub main and current M10n/M10y/M10z source boundaries
- [x] Add pure, explicit, read-only full compatibility-field comparison
- [x] Add drift/blocked-state tests with no content leakage in mismatch
- [x] Add actual disposable SQLite subprocess integration test
- [ ] CI passes and independent review
- [ ] Operator-approved PR merge
- [ ] Separately authorized isolated on-device Quickshell test
- [ ] Verified single-writer production host and cutover rollback
- [ ] Separately approved migration/activation

## NEXT

M11b should design/test an **unmounted single-writer host contract**
that refuses concurrent legacy and SQLite stages, supports explicit
drain acknowledgement and restart `RECOVERY_REVIEW`, and never grants
a write solely from self-reported readiness. Avoid altering
`ApolloHubTodoStore` until runtime acceptance and operator approval
for an exact host integration patch.

## DECISIONS

No desktop changes, production database reads, Quickshell restart, live
writer modification, GitHub Project operation or Hospital role promotion.
JSON remains authoritative. SQLite is still only the candidate replacement.
