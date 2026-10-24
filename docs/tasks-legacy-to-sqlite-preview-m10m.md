# 🏥💜 Proxy 1 // M10m Legacy TASKS → SQLite Migration Preview

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Operator:** selected Option B SQLite. Operator reported repository changes pulled into their live Quickshell on October 23, but **no database cutover was performed**.  
**Worker / assignment:** Proxy 1, unified TASKS storage and migration contract; not a registered live Hospital session.  
**Status:** CI-only migration dry run; no live migration service or UI.

## IMPLEMENTATION

**New pure adapter:** `services/projects/LegacySqliteMigrationPreview.py` accepts
**caller-supplied raw bytes**, never a file path or default TASKS directory.
It verifies UTF-8, one-megabyte limit and duplicate JSON keys, then invokes a
small Node policy oracle to reuse **the already reviewed**:

- M10d `LegacyMigrationDryRun.js`, normalizing legacy Todo versions 1, 2
  and 3 with exact field allowlists.
- M10b `OfflineOperationJournal.js`, with a verified baseline envelope.
- M10h `UnifiedProjectModelV2.js`, a strict v2 model conversion with no
  inferred remote GitHub identity.
- M10g `UnifiedStorageReadBridge.js`, validating that reverse read-only
  projection preserves the established legacy v3 shape.

The Python preview independently checks the resulting M10h v2 document
against the M10j SQLite validator and refuses nonempty journals, remote/GIT
identities, custom values or unsupported future records. It exposes:
original input byte count and SHA-256, candidate in-memory v2 document,
read-only v3 compatibility projection, and explicit
`migrationPerformed:false`, `writeReady:false` and
`remoteWriteAuthorized:false`.

**New CI test:** `tests/tasks/test_legacy_sqlite_migration_preview.py`
creates disposable, private test paths and confirms:

1. Original bytes are snapshotted without normalization or whitespace loss
   to a **new file** opened in exclusive-create mode and fsynced. An existing
   backup name cannot be overwritten.
2. The backup SHA-256 matches the exact bytes of the legacy input.
3. The converted model initializes a **different, disposable** SQLite
   schema-v2 database using M10l `ExperimentalTaskSqliteRecordsV2.py`.
4. Reloading SQLite yields the same IDs, projects, titles, completion,
   priority, description, due dates, timestamps and next-ID counters as
   the M10d/M10g v3 compatibility projection.
5. The original bytes can be copied back to a separate restored-source
   fixture with byte-for-byte equality. No original was modified.
6. Unknown/duplicate fields, unsupported versions, malformed input,
   invalid due dates, orphan project references and counter rewinds are
   rejected before any migration target is created.

## HOW TO USE

**CI only:**

```sh
python3 tests/tasks/test_legacy_sqlite_migration_preview.py
```

No operator desktop action, real path discovery, Quickshell restart or
production migration is needed. The preview function accepts bytes rather
than opening the user's live data.

## VERIFY

- Legacy v1, v2 and v3 synthetic documents, including Unicode, unusual
  whitespace, leap-day dates, historical timestamps and unassigned tasks.
- In-memory v2 model compatibility with legacy v3 consumers.
- Exact source-byte identity before and after a disposable SQLite trial.
- Safe backup-exclusive-create behavior and hash/restore round trip.
- SQLite read-back of candidate with zero active remote operations.
- Existing M10d, M10h, M10k and M10l regression suites in CI.
- No modifications to a live TASKS JSON file or active UI.

## WATCH OUT FOR

**This is NOT a production backup, migration installer, filesystem
snapshot or cutover controller.** The test's copied bytes and fsync checks
verify a disposable backup and restoration exercise, not resilience against
hardware power loss, malicious mutation or whole-disk failure. There is
no disk-space reserve, multi-writer coordination, backup retention policy,
copy-to-secure-media procedure or verified rollback of a live deployment.

The source must be *frozen* while a real backup/migration is attempted.
A live migration requires a single-writer stop protocol, exact original
backup and restore proof, cross-process locking, parity comparison, then
a separate **operator-authorized** activation with a rollback plan that
cannot overwrite edits made after cutover.

The **legacy v3 projection is deliberately read-only** and must never be
persisted over richer data. M10m marks imported v1/v2/v3 projects NORMAL
because legacy files do not supply verified GitHub identities. GitHub
Projects synchronization still needs identity verification, permissions,
remote baseline and conflict safeguards.

The M10l record-authoritative schema-v2 prototype remains unmounted.
The current live TASKS singleton still writes
`Quickshell.dataDir + "/apollo-hub-todo-v1.json"`.
Pulling and reloading Quickshell makes these source files available but
**does not turn SQLite on**.

## CHECKLIST

- [x] Verify merged M10k (#649) and M10l (#652), live writer remains JSON
- [x] Legacy migration using approved M10d/M10h/M10g policies
- [x] Reject duplicate keys and unsupported legacy extensions
- [x] Preserve original byte hash and v3 display parity
- [x] Test SQLite v2 reconstruction in independent disposable directory
- [x] Verify exclusive backup, raw restore and unchanged original source
- [ ] CI success and independent source review
- [ ] Operator-authorized PR merge
- [ ] Real database backup and WAL-safe restore procedure
- [ ] Actual Quickshell one-writer/Process integration and desktop acceptance
- [ ] Separate operator authorization for real task migration and activation

## NEXT

**M10n proposal:** migrate preview into a guarded on-device acceptance
*design*, with single-writer coordination, WAL-safe backup policy, shadow-read
parity and a fully reversible cutover workflow. Live task data remain under
the existing JSON writer until all gates pass and operator approval is
explicitly provided.

## DECISIONS

SQLite remains the approved target backend, **not yet the active writer**.
No local machine files, GitHub Project records, Hospital assignments,
Proxy 2 PLANNER, live `ApolloHubTodoStore.qml`, or Quickshell services are
modified here.
