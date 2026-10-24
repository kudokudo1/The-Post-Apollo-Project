# 🏥💜 PROXY 1 // M10n Controlled TASKS SQLite Cutover Review

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Status:** Review-only prototype and test harness. Does not activate production storage.  
**Owner:** Proxy 1 TASKS storage/migration; not live Hospital-registered.  
**Operator decision:** SQLite selected as target; existing Quickshell JSON writer remains authoritative.

## IMPLEMENTATION

M10m merged after its synthetic legacy-to-SQLite migration and exact-byte
backup verification. M10n introduces a **read-only gate**:
`services/projects/TaskSqliteCutoverReview.py`.

`review()` accepts explicit *caller-provided* legacy bytes, a fresh legacy
byte snapshot, a byte-exact original backup, a separately restored byte copy,
the expected SHA-256 and two explicit, independently located schema-v2
`tasks.db` paths. It compares:

- Original source SHA-256 with the recorded pre-migration fingerprint.
- Original source versus the fresh read, backup and restored copies, **byte
  for byte**. Whitespace, Unicode and unknown structures are not repaired.
- Candidate M10m strict legacy→M10h v2 in-memory normalization, refusing
  invalid source keys, remote identity guesses or active journal records.
- Both the shadow SQLite database and the independently backed-up SQLite
  database through the M10l read-only record validator.
- Exact model, hash and revision-zero parity between imported candidate,
  shadow database and SQLite backup; all operations must be clean.
- Recorded *review notes* for writer quiescence, exclusive owner, Quickshell
  runtime acceptance, online SQLite backup, startup recovery and rollback.

The review flags are self-attested **notes, not cryptographic evidence or
authorization tokens**. If all pass, the result is `READY_FOR_OPERATOR_REVIEW`,
**never** `activate:true`, `writeReady:true`, or permission to mutate
Quickshell, task files or GitHub.

`rollback_review()` is a separate **read-only** decision aid. It compares a
fresh SQLite state against its original version-zero hash, rejects unknown,
blocked or edited states, and marks any post-migration revision/operation
as an **unsafe old-snapshot rollback**. Even a pristine original remains
`restore:false` until an independently authorized manual process.
It never overwrites a source file, stops a writer or recovers a database.

A new synthetic test uses disposable private directories and SQLite's
`Connection.backup()` online backup API to prove a restorable, independent
SQLite copy. A subsequent SQLite edit intentionally makes the old JSON
backup *unsafe for blind restoration*. The test also checks wrong source
hash, modified legacy bytes, mismatched backup/restored bytes, corrupt
database and missing or non-independent SQLite backups.

## HOW TO USE

CI only:

```sh
python3 tests/tasks/test_task_sqlite_cutover_review.py
```

The suite writes only to OS-created disposable test roots. No access to
the user's Quickshell data directory or real TASKS SQLite path occurs.
The new review module has no CLI, no filesystem mutation methods, no
`FileView` or `Process` connection, no activation or network methods.

## VERIFY

- Original source bytes = fresh source = exclusive backup = restored bytes.
- Independent SQLite online backup remains model-identical to a separate
  synthetic schema-v2 shadow database.
- Legacy task IDs, project assignment, due dates, timestamps and original
  counters survive conversion and readback.
- Missing external writer/runtime review notes cannot pass the review gate.
- Pretending to pass all evidence still never activates a writer.
- Any SQLite edit after the original imported revision blocks rollback to
  old JSON even if an independently copied SQLite DB matches the newer state.
- Invalid source, missing backup, reused backup DB path and corrupted state
  fail closed without exposing task descriptions or local file paths.
- M10m, M10l and M10k regressions included in the scoped workflow.

## WATCH OUT FOR

**M10n is NOT production cutover.** It cannot prove that the live
`ApolloHubTodoStore.qml` has been quiesced, that a real system's backup is
power-loss durable, or that a future Quickshell SQLite write bridge is safe.
Those conditions require runtime inspection and explicit operator approval.

A shared or concurrently changing original JSON file must not be taken as
frozen based only on equal test buffers. Before actual deployment, a
coordinated stop-the-writer barrier and on-device byte/hash check are required.

For real WAL backups, copying the main `tasks.db` file alone is insufficient
when active WAL transactions exist. Use the SQLite online backup API, verify
the restored copy and ensure secure permissions and rollback retention. The
test exercises this only on disposable storage.

An *old* JSON rollback after new SQLite edits would lose accepted edits.
The safe rollback procedure must therefore include an explicit edit
freeze and forward reconciliation of all post-cutover mutations (including
uncertain GitHub effects). M10n refuses to offer automatic restore.

A real migration still requires running UI integration tests for TODAY,
PLANNER, TASKS and Apollo Hub and preserving the local-first/GIT journal
semantics. The M10l Python adapter remains test-only. Imported old projects
remain NORMAL until independently verified remote identities are attached.

## CHECKLIST

- [x] Confirm M10m PR #654 merged and JSON store still live
- [x] Guard source, backup, restore and independent SQLite shadow hashes
- [x] Refuse automatic activation regardless of evidence flags
- [x] Identify post-cutover edits as rollback blockers
- [x] Test actual SQLite online backup against disposable files
- [ ] GitHub CI success and independent source review
- [ ] Operator-authorized M10n merge
- [ ] Actual Quickshell writer quiescence mechanism and runtime acceptance
- [ ] Production-grade WAL backup, restore, crash and rollback tests
- [ ] Separate authorization for live user data migration and activation

## NEXT

**M10o candidate:** controlled single-writer handoff protocol for the
existing Quickshell singleton and a testable SQLite host facade, with
explicit read/write ownership tokens and a stop-the-old-writer handshake.
Do not change the active `ApolloHubTodoStore.qml` or install a new writer
until a separately approved, verifiable cutover plan passes acceptance.

## DECISIONS

SQLite remains selected, but **the current live JSON store is still the sole
authoritative TASKS writer**. Proxy 2 retains PLANNER ownership. No changes
to task data, local machine configuration, Quickshell runtime, GitW,
Hospital-owned records or GitHub Projects.
