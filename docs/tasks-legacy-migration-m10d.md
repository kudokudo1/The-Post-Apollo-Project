# 🏥💜 Proxy 1 // TASKS M10d Non-Destructive Legacy Migration

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Owner:** Proxy 1, external ChatGPT development assignment (not live Hospital registered).  
**Status:** Isolated dry-run contract. No live migration, no GitHub read/write, no change to the established local task writer.

## IMPLEMENTATION

`services/projects/LegacyMigrationDryRun.js` is a pure JavaScript function that accepts:

- **raw** legacy task JSON supplied by a caller
- the existing `ApolloHubTodoPolicy.js` validation/parse policy
- the experimental `OfflineOperationJournal.js` envelope policy from M10b

`plan(raw, legacyPolicy, journalPolicy)`:

1. Validates raw input with the existing legacy parser (versions 1, 2 and 3).
2. Refuses unexpected document, project, or task fields that the old normalizing clone would otherwise silently discard.
3. Converts the *validated, normalized* v3 document into a prototype envelope containing `version:1`, `revision:0`, all existing task fields, original timestamps, local IDs and monotonically advancing ID counters.
4. Classifies all previous local projects as **NORMAL** and adds no Git identity or remote operations.
5. Tests the prototype journal encoder and decoder.
6. Restores a v3-compatible projection from the candidate and compares it with the normalized original.
7. Returns a preview and counts, expressly marked `writeReady:false` and `migrationPerformed:false`.

The callable `restoreCompatibleV3` is a **read-only compatibility projection**, NOT an on-disk rollback implementation. It refuses active journals, Git projects, unknown extensions or missing counters.

## HOW TO USE

Run the isolated synthetic fixtures through GitHub CI:

```sh
node tests/tasks/test_legacy_migration_dryrun.cjs
```

This source milestone is not connected to TASKS, the Hub or GitW. It does not request access to the actual user data file.

## VERIFY

- Synthetic v3 documents with multiple projects and assignments, unused/cancelled ID gaps, completed tasks, priorities, descriptions, dates and timestamps.
- v1/v2 normalization through the existing policy without invented project links.
- Empty and sparse historical data, including early-year Gregorian dates.
- Exact preservation of the current *normalized* v3 representation through a prototype envelope roundtrip.
- Rejection of unexpected legacy fields, unsupported/malformed versions, dangling references, sequence rewinds, duplicates, and invalid dates.
- Refusal to project future Git/custom-field data back into v3 as though a lossless rollback were possible.
- Full non-mutation of supplied raw fixtures.

The existing journal contract is rerun in the scoped CI job.

## WATCH OUT FOR

This prototype **does not yet** preserve raw JSON source byte-for-byte through the new envelope. For v1/v2, it normalizes fields using the existing legacy policy. A real rollback must restore an independently backed-up copy of the original raw file.

The original v3 policy drops unknown keys when cloning. This dry run now rejects unexpected keys outright. It does **not** yet detect duplicate JSON object keys within raw source text, a limitation to address before any live migration approval.

The M10b envelope is explicitly a **prototype schema**. Its validators do not enforce all proposed v4 metadata fields and its current edit operation does not automatically advance historical task timestamps. The compatibility projection is therefore for baseline migration analysis only, not proof that future edits can be round-tripped into old v3 storage.

No disk/fsync, concurrent-write, power-loss, performance or real data migration test occurs here. No on-device or remote mutation is authorized by passing CI.

## CHECKLIST

- [x] Define strict legacy field allowlists
- [x] Preserve IDs, assignments, project metadata and timestamps in candidate
- [x] Preserve next-ID counters and prevent accidental ID reuse
- [x] Guarantee NORMAL-only classification and empty remote queue
- [x] Verify encoder/decoder and v3 compatibility projection
- [x] Test malformed and unknown fields fail closed
- [ ] CI verification
- [ ] Independent review and operator-authorized merge
- [ ] Original-file backup/restore and source hash verification
- [ ] Real migration, exclusive writer/lock protocol and on-device acceptance

## NEXT

M10e: design a versioned, genuinely durable storage adapter and backup/restore contract. Resolve whether the target uses a single atomic envelope or a transactional database; add tests for task metadata mutation, operation recording and crash consistency before the original v3 store is ever retired.

## DECISIONS

- Existing task, Hub/TODAY and Proxy 2 PLANNER readers retain the current v3 projection.
- No changes to `ApolloHubTodoPolicy.js`, `ApolloHubTodoStore.qml`, `TasksW.qml`, `shell.qml`, `GitW.qml`, `GitHubProjectsService.qml` or PLANNER files.
- Proxy 1 owns migration and journal development. Proxy 2 retains PLANNER and independent UI scope.
- User/operator authority remains required for merges, actual data migrations and live activation.
