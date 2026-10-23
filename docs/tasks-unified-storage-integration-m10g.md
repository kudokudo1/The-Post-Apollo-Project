# 🏥💜 Proxy 1 // TASKS M10g Read Bridge and Production Cutover Contract

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Owner:** Proxy 1, external development assignment, not live Hospital-registered.  
**Status:** Read-only integration prototype and operator review gates. No deployed writer.

## IMPLEMENTATION

M10a–M10f established the architecture, in-memory offline operation journal,
interrupted-write tests, strict legacy conversion preview, raw-byte backup and
restore fixtures, and a cooperative exclusive writer test fixture.

**M10g now adds `services/projects/UnifiedStorageReadBridge.js`.** The pure
`preview(envelope, journalPolicy, legacyPolicy)` function:

1. Validates the candidate using M10b journal policy and checks required
   counters and legacy timestamps.
2. Constructs a **new in-memory legacy v3-compatible projection**, preserving
   task IDs, descriptions, priorities, dates, completion state, project IDs,
   timestamps and monotonic ID counters.
3. Reuses the established `ApolloHubTodoPolicy.view` output layout, including
   `items`, project task counts, `total`, `remaining`, and `completed`.
4. Forces `snapshot.writable = false`, even if the original v3 view says
   the state would normally be writable.
5. Reports pending non-acknowledged journal operations as an auxiliary count,
   but does not treat them as confirmed GitHub synchronization.
6. Deliberately **does not serialize the projection back** over the full new
   envelope. New-model GIT identities and custom extensions remain untouched
   in the source model. This projection is for display compatibility only.

The test exercises the read-only snapshots through existing TODAY and PLANNER
policies. Apollo Hub and TASKS still use the real current legacy singleton;
the bridge is **not mounted** into their QML views.

`cutoverReview(facts)` is a planning checklist, not an activation authority.
Its review gates include original-byte backup, frozen source, quiesced legacy
writer, candidate validation, exclusive replacement writer proof, crash recovery,
snapshot parity, rollback, and operator authorization. **Even when all fields
are self-reported true, it returns `activate:false` and `writeReady:false`**.
A later authorized integration must verify evidence externally.

## DESIGN CHOICE UNDER REVIEW

**Preferred candidate:** one versioned envelope with model, project links,
and offline intent journal in the same atomic commit unit; one exclusive writer.

This reduces the risk of a saved task missing its queued Git operation.
However the M10b model, M10e backup fixture and M10f Node lock are **not**
production-ready. An actual Quickshell-compatible writer still requires:

- An explicit single-writer owner, with all old writers stopped or routed into
  the same service. Merely hiding `TasksW` does not stop the Hub singleton.
- Verified disk durability and post-rename uncertainty handling, not a
  `FileView.atomicWrites` property assumed to cover multiple files.
- An operator-supervised exclusive migration from original v3 data, with a
  raw-byte backup that has been restored successfully to a disposable target.
- Strict source parser including handling duplicate JSON keys, unknown fields,
  version validation, and preservation of timestamps on every future edit.
- A verified external Git-owned remote adapter for read-back, field mapping,
  conflict and permission checks. No remote write merely because an operation
  appears `PENDING` or an acknowledgement token contains text.
- Retained compatibility for Apollo Hub, TASKS, TODAY, PLANNER and current
  local PROJECTS UI, including explicit handling of GIT-specific metadata.
- A migration rollback policy that cannot erase offline edits made after
  a new store becomes active; restore to old v3 is **not** inherently safe
  after new fields or remote writes exist.
- Platform and runtime acceptance by the operator, then separately
  authorized production activation.

SQLite remains an alternative should the single-envelope approach fail
durability, concurrency, scaling, or Quickshell integration acceptance. No
SQLite installation, benchmark or backend selection has been made yet.

## HOW TO USE

CI-only: `node tests/tasks/test_unified_storage_read_bridge.cjs`.

No local pull, restart, migration, new storage path, or account permission
is required. The new policy is not instantiated in the desktop.

## VERIFY

- Synthetic v3 normalization -> prototype envelope -> v3 snapshot parity.
- TODAY and PLANNER read policies accept the same immutable preview.
- Local GIT metadata/custom extensions survive because only a projection is
  computed; no mutation or reverse persistence occurs.
- Pending/uncertain remote operations cannot make the projection writable.
- Malformed versions, missing counters/timestamps, invalid dates and duplicate
  names fail closed.
- A positive self-reported readiness checklist never activates a writer.
- Existing M10b journal and M10d migration suites rerun in scoped CI.

## WATCH OUT FOR

`OfflineOperationJournal.verify` still allows additional schema keys and does
not yet verify GitHub link identities or enforce timestamp updates on edits.
This bridge therefore relies on legacy projection validation to reject
invalid compatibility data. It does not claim the M10b journal is a complete
production model, nor does it perform a complete migration.

The projection is `writable:false` but that does not prevent an unrelated
consumer from calling the **existing** live store's edit methods. This
prototype must not be substituted as the live data source until host and
store ownership are redesigned and explicitly authorized.

Quickshell file IO, exclusive writer behavior, power-loss durability and
actual GUI interactions are still unverified for a replacement service.

## CHECKLIST

- [x] Verify current main and M10f merge
- [x] Define read-only compatibility projection
- [x] Preserve current downstream task shape
- [x] Never discard GIT-specific extensions by writing a v3 projection
- [x] Establish fail-closed cutover review gates
- [x] Independent tests and CI
- [ ] CI evidence and independent source review
- [ ] Operator-authorized merge
- [ ] Repair prototype model and choose production storage writer
- [ ] Validate original-file backup, locking and on-device runtime behavior
- [ ] Explicit separate authorization for any real data migration

## NEXT

M10h proposal: isolate the future full schema validator and timestamp-aware
edit policy, including stricter unknown/duplicate-key handling and handling
of future GIT item relationships, without deploying it or changing the
existing Quickshell writer. Plan a controlled shadow-read acceptance test
against synthetic fixtures before any production cutover.

## DECISIONS

No changes to `ApolloHubTodoStore.qml`, `ApolloHubTodoPolicy.js`,
`TasksW.qml`, `shell.qml`, `TaskPlannerPane.qml`, GitW, remote GitHub,
or on-device files. Proxy 2 continues independently owning PLANNER.
