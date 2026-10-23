# 🏥💜 Proxy 1 // M10h Strict Model v2 and Timestamp-Aware Edits

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Owner:** Proxy 1, external development assignment, not live Hospital-registered.  
**Status:** Pure JavaScript model candidate and source-level tests only. No desktop storage writes or GitHub changes.

## IMPLEMENTATION

`services/projects/UnifiedProjectModelV2.js` provides a strict, candidate
**version 2 envelope**. This is a separately versioned *prototype schema*,
not a live TASKS version bump or a production writer.

The model stores:

- Stable local task/project IDs and original created/updated timestamps.
- Monotonic next-task, next-project, next-operation counters and revision.
- NORMAL projects without remote identity; GIT projects with a
  **shape-checked, unverified** GitHub ProjectV2 reference.
- Tasks with optional **shape-checked, unverified** GitHub item identities
  and their existing due date, priority, description and completion fields.
- Per-project typed custom field definitions with `text`, `number`,
  `boolean`, or `date` kind. These fields have `scope:"local"` only.
  Task field values are typed and bound to the definitions of their owning
  project, avoiding untyped opaque metadata.
- Offline operations in the same in-memory envelope as their GIT task edits.

Strict validation refuses unknown record keys, duplicate IDs and field
labels, invalid type/value combinations, orphan project/field references,
sequence rewinds, invalid timestamps, and remote identifiers in NORMAL
projects. `decode(raw)` additionally detects repeated object keys, including
different Unicode spellings of the same decoded key.

The model exposes:

- `upgradeBaselineV1`: pure, explicit **baseline-only** conversion from the
  M10d/M10b in-memory prototype. Refuses queued edits, already-active GIT
  data and additional fields. No silent migration.
- `editTask`: returns an immutable candidate with monotonic updatedAtMs
  (even for same-millisecond edits). GIT edits append PENDING intents in the
  same in-memory candidate. NORMAL edits do not append remote operations.
- `renameProject`: NORMAL-only, timestamp-aware local rename. A GIT project
  rename is refused until a separately designed remote action contract exists.
- `addLocalField`: adds a typed, LOCAL-ONLY field definition to either family
  and advances project timestamp and revision.
- `editCustomValue`: changes local-only typed values, advancing task timestamp
  and revision. No implicit GitHub field mapping or outbound operation.
- `legacyReadProjection`: produces a **read-only, non-persistable** M10b-shaped
  candidate for the existing M10g bridge, retaining the original v2 schema's
  rich data in its untouched source. Existing TODAY and PLANNER policy tests
  confirm the display projection.

All output contains `writeReady:false` / `remoteWriteAuthorized:false` in
applicable edit results. No method dispatches to GitHub or writes a file.

## HOW TO USE

This is a source and test milestone. GitHub CI runs:

```sh
node tests/tasks/test_unified_project_model_v2.cjs
node tests/tasks/test_unified_storage_read_bridge.cjs
node tests/tasks/test_legacy_migration_dryrun.cjs
```

No pull/restart required until an operator-approved future UI integration.
All tests use synthetic in-memory records.

## VERIFY

- Existing v3 → dry-run baseline → v2 → legacy read projection retains IDs,
  counters, dates, priorities, descriptions and historical timestamps.
- NORMAL/GIT family controls and an explicitly unverified remote reference.
- Pending Git intents have stable, monotonic operation IDs and ordered
  revisions; local-only custom fields never enter the Git queue.
- Repeated rapid edits advance timestamps; backward clock inputs fail closed.
- Per-project custom field definitions, types, valid values and duplicate
  label rejection.
- Malformed, unknown, future-version and repeated JSON keys fail closed.
- The v2 model round-trips through its own JSON encoder/decoder.
- TODAY and PLANNER continue to consume a read-only compatible snapshot.
- No QML, file IO, process, or network side effects in policy code.

## WATCH OUT FOR

**No production storage integration has occurred.** The earlier M10b journal
is still in use by its independent prototype tests; this new schema is not
automatically migrated onto disk. The M10g read bridge also still accepts
M10b, and the new v2 projection is read-only by contract.

Current v2 remote references and operation records are **shape checks only**.
They do not prove GitHub authentication, identity ownership, field mappings,
remote baselines, or read-back acknowledgement. No GIT operation is authorized
for sending solely because it was appended as PENDING. An unlinked GIT task
can have an intent preserved for later identity reconciliation, but cannot
be transmitted without a separately approved adapter.

Field definitions are currently local-only and per-project. Their scope and
the eventual multi-project task relationship design remain open decisions.
There are no field delete/rename, task reparent, GIT rename, remote mutation,
conflict resolution, or queue compaction methods.

The decoder validates duplicate keys on JSON text but is not yet the complete
production threat model: real byte-oriented UTF-8 limits, filesystem locks,
power-loss semantics, concurrent writers, and deployed QML JS behavior still
need verification. The policy uses a string-length limit, not a byte-exact
serialized file limit.

Timestamp monotonicity uses `max(nowMs, previousUpdatedAtMs+1)` after rejecting
a backward input. This is a logical timestamp rule, not a claim that every
recorded edit necessarily happened at a distinct physical millisecond.

## CHECKLIST

- [x] Review current main, M10g merge and shared ownership
- [x] Strict v2 schema and identity/reference boundary
- [x] Typed custom fields with local-only scope
- [x] Timestamp-aware task and project edits
- [x] GIT pending intent from a local edit in the same candidate
- [x] Read-only M10g / TODAY / PLANNER projection
- [x] Isolated tests and scoped CI
- [ ] CI completion and independent source review
- [ ] Operator-authorized merge
- [ ] Runtime storage-writer selection, backend, migration acceptance

## NEXT

After M10h acceptance, refine actual persistence and operation reconciliation
contracts. A later milestone must review durable commit acknowledgement,
transport mapping, remote read-back and conflict handling with verified
GitHub identifiers, before enabling sync or migrating real data.

## DECISIONS

Proxy 1 owns the project data contract. Proxy 2 retains PLANNER ownership.
No edits to `ApolloHubTodoStore.qml`, `ApolloHubTodoPolicy.js`,
`TasksW.qml`, `shell.qml`, `TaskPlannerPane.qml`,
`GitHubProjectsService.qml`, GitW, the desktop, or remote GitHub Projects.
