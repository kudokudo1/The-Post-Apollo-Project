# 🏥💜 Proxy 1 // M10q Quickshell Writer Admission Rehearsal

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Worker scope:** Proxy 1 TASKS storage/authority boundary; no live Hospital registration assumed.  
**Operator decision:** SQLite for future TASKS storage. Live JSON TASKS storage is unchanged.  
**Status:** Unmounted QML component + persistent disposable Linux/Python host + synthetic integration tests. No live freeze or migration.

## IMPLEMENTATION

PR #667 (M10p) is merged. M10p demonstrated SQLite-backed epoch
fencing and a real OS `flock` on **disposable** files, but did not expose
a Quickshell-compatible process API. M10q connects that isolated fixture
to a **long-lived JSON-lines subprocess** and an **unmounted QML bridge**.

Files added:

1. `tests/tasks/fixtures/TaskSqliteHandoffHost.py`
   - Requires an explicit absolute private `handoff-test.db` and
     test writer ID. `--bootstrap-fixture` is a **test-only CLI argument**,
     deliberately absent from the Quickshell bridge.
   - Opens M10p `Authority` once and retains the SQLite connection and
     `flock` for the entire stdin/stdout session. A new host on an existing
     DB enters `RECOVERY_REVIEW`; neither the host nor the QML component
     automatically re-enables staged writes.
   - Emits exactly one `hello` and bounded newline-delimited replies.
     Supports `status`, `admit`, `freeze` and `settle` only, all
     operating on *synthetic stage IDs*. No real `FileView`, task data,
     GitHub API or `tasks.db` is ever accessed.
   - Rejects unexpected JSON fields, duplicate keys, replayed request IDs,
     invalid callback values, malformed JSON, oversized input and unknown
     commands. Every reply explicitly says `sqliteWriteAuthorized:false`
     and `liveChangePerformed:false`.
   - Exits and drops the OS lock after EOF, protocol error, Quickshell
     termination or process exit. The next owner reopens fail-closed.
2. `services/projects/TaskSqliteAdmissionRehearsal.qml`
   - A standalone `Scope` with a Quickshell `Process`, explicit
     `stdinEnabled:true`, `SplitParser` for newline-delimited host
     responses, and `Process.write()` for the requests.
   - Nothing starts on QML component construction. A caller would have to
     explicitly set `fixturePath`, `writerId` and call
     `beginRehearsal()`; that still only opens a disposable **test**
     database, never the user's TASKS storage.
   - Methods `simulateStage()`, `simulateFreeze()`,
     `simulateSaveCallback()`, and `inspectFixture()` send synthetic
     commands, one at a time. Stale/malformed responses fail closed.
     `stopRehearsal()` terminates the test host; abnormal exits clear
     the simulated session state.
   - It exposes `writeReady:false`, `sqliteWriteAuthorized:false`
     and `liveChangePerformed:false` as read-only constant properties.
     It has **no FileView**, no actual `ApolloHubTodoStore.stage()`
     integration, no timer/auto-start and no production import.
3. `tests/tasks/test_task_sqlite_handoff_host.py`
   - Launches the actual host in subprocesses, drives the test-only JSONL
     protocol, checks cross-process lock contention, in-flight saves,
     freeze barriers, save-success/failure callbacks and stale response IDs.
   - Verifies normal process shutdown and crash-recovery-like reopening
     always enter `RECOVERY_REVIEW` and refuse stale stage admission.
   - Attempts forged activation, unknown commands, extra keys and invalid
     inputs; verifies none can enable SQLite writes.
   - Tests missing DB and wrong `tasks.db` filename never get created.
   - Static QML/source contract checks ensure the new QML file is unmounted
     and uses no live task path or `FileView`.

## HOW TO USE

GitHub CI only:

```sh
python3 tests/tasks/test_task_sqlite_handoff_host.py
```

No desktop commands or new UI controls. The Python tests create private
`tempfile.TemporaryDirectory` fixture locations. Do not run the
`--bootstrap-fixture` host against the user's live configuration.

## VERIFY

- Existing OS lock holder blocks a different authority-owning process.
- Persistent session retains lock across multiple commands.
- JSON_ACTIVE admits at most one synthetic stage, freeze blocks new stages,
  pending save completes via a matching callback, duplicates are refused.
- Old writer state never resumes automatically after release/restart.
- Test-only process is never permitted to operate on real `tasks.db`.
- Command/reply schemas are bounded and reject spoofed write permissions.
- M10p/M10o/M10n regression suites run in dedicated CI.

## WATCH OUT FOR

**Critical: source-level Quickshell compatibility is not live runtime
acceptance.** The test exercises real Python processes on Linux but performs
only static checks on the QML component. A disposable on-device Quickshell
test is needed for parser signal timing, process lifecycle, UI event handling
and actual stderr behavior.

The QML component is **not a security/ownership authority**. User-supplied
writer IDs or QML booleans are not credentials; the genuine future bridge
needs a durable, privileged-by-owner worker with process-lifetime locks,
safely generated session tokens, callback ordering and filesystem source
verification. This work provides a transport rehearsal, **not** the
production host.

A real `ApolloHubTodoStore.stage()` guard requires a carefully reviewed
change inside the existing singleton, with every current TASKS/TODAY/
PLANNER/Hub operation preserved. Merely adding another QML component does
not freeze the old writer. Before activating SQLite, verify the complete
current writer API, startup read behavior, async `FileView` saves,
failure/recovery, source hash, backup, exclusive handoff and rollback.
M10l's experimental SQLite task writer also lacks several legacy API
operations, so migrating now would break task functionality.

**No production default path, autorun hook, migration, task mutation, or
GitHub Projects operation is included.** No local machine files were
modified by authoring this PR.

## CHECKLIST

- [x] Verify M10p PR #667 merged and active JSON TASKS owner unchanged.
- [x] Persistent Python host with an OS-held disposable lock.
- [x] Explicit QML Process + newline protocol rehearsal interface.
- [x] Strict sequential request IDs and fail-closed response handling.
- [x] Test lock contention, stage/freeze/callback sequencing and reopen.
- [ ] CI and independent source review.
- [ ] Operator-authorized M10q PR merge.
- [ ] Real on-device disposable QML runtime test, after local approval.
- [ ] Approved `ApolloHubTodoStore.stage()` admission gate and safe rearm.
- [ ] Full SQL task API and explicit operator-controlled live data cutover.

## NEXT

M10r can begin a **QML-only disposable acceptance harness** and a
compatibility inventory of every JSON TASKS writer method versus the new
SQLite adapter. Decide a practical normal-QS-restart rearm path before
touching production admission behavior.

## DECISIONS

SQLite remains the selected future backend; legacy JSON stays the sole
live writer. Proxy 2 retains PLANNER ownership; no files from the active
QML singleton, TASKS UI, TimeW, GitW or Hospital are changed. No merge,
Hospital registration, local pull/reload, real-data migration or production
activation was performed.
