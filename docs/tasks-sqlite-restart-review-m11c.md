# 🏥💜 TASKS // M11c Consumable Restart Recovery Review

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Assignment:** Proxy 1 storage continuity, Proxy 2 operator-authorized successor  
**Status:** Disposable Python test fixture, NOT production writer rearm  
**Active storage:** `services/hub/ApolloHubTodoStore.qml` JSON FileView exclusively

## IMPLEMENTATION

M11b merged. Its disposable M10p OS-flock owner and persistent SQLite
`handoff-test.db` authority always reopen in `RECOVERY_REVIEW`.
That is correct for safety, but it does not distinguish a prior cleanly
quiesced owner from an interrupted save or missing historical evidence.

M11c extends the **test-only** M11b coordinator in
`tests/tasks/fixtures/TaskWriterRecoveryM11c.py`, without altering the
M10p authority's existing API or production QML:

- A private SQLite `restart_review` table is created **only during
  explicit fresh fixture bootstrap**, never silently on reopening.
- `mark_quiescent_close()` requires the owner to have frozen simulated
  JSON save admission, settled the outstanding callback, obtained M11b's
  verified two-read JSON SHA-256 and reached durable `JSON_QUIESCED`.
  It independently rereads the *actual disposable JSON file* twice,
  verifies the saved SHA and atomically records a **single immutable
  quiescence checkpoint** referencing the owning epoch.
- `inspect_restart()` only runs on an OS-lock-holding current owner in
  `RECOVERY_REVIEW`. It rereads the private source, checks a distinct
  new owner epoch, the prior source hash, pending save token and required
  recovery reason. It **consumes the checkpoint once in SQLite**, even
  when the first review blocks. Replaying the old marker across
  subsequent restarts is prohibited.
- A valid match produces `REVIEW_CANDIDATE`, **not** JSON_ACTIVE,
  `SQLITE_ACTIVE`, a new writer token or any permission to save. All
  paths return `simulatedJsonStagePermitted:false`,
  `legacyWriterEnforced:false`, `sqliteWriteAuthorized:false`,
  `remoteWriteAuthorized:false`, `liveChangePerformed:false`,
  `rearmPerformed:false`.
- Absent, malformed, stale or consumed markers, source drift during
  either inspection, unsaved in-flight callbacks and unmatched epochs
  fail closed. The current process's OS lock is still provided by M10p,
  and its owner/epoch tests remain intact.

A crucial limitation: a process may **crash after recording a clean
quiescence checkpoint but before exiting normally**. No persisted
checkpoint alone can prove a graceful process exit. M11c intentionally
treats that case as a review candidate *only*. The source hash and epoch
are **evidence**, not an authorization token.

## HOW TO USE

GitHub CI or an independently authorized developer's fully disposable
test environment only:

```sh
python3 tests/tasks/test_task_writer_recovery_m11c.py
```

The tests create OS-private temporary files named `handoff-test.db` and
`legacy-test.json`, use synthetic task bytes, launch real competing and
crashing Python processes, and clean up test folders. They do not read
or create `~/.local/share/quickshell` paths or any live TASKS file.

## VERIFY

The tests exercise:

- Quiescence marker creation only after a simulated in-flight save drains,
  a frozen admission gate and identical real source readbacks.
- Fresh owner still begins `RECOVERY_REVIEW` even with a matching marker,
  and a candidate can be reviewed **only once**.
- Subsequent process restart does not replay the marker or resurrect
  stage admission.
- OS-level lock contender cannot acquire owner access.
- Unclean JSON_ACTIVE exit without marker, crash with pending save,
  failed save callback, mismatched source, changed source between reads,
  tampered marker, repeated mark and stale evidence are refused.
- True `os._exit()` process crashes **before and after** checkpoint.
  A post-checkpoint crash remains a *review candidate*, not a write grant.
- The legacy writer remains unmodified and production SQLite migration
  does not exist in this fixture.
- Existing M11b, M10p, M10o and M11a regressions rerun.

## WATCH OUT FOR

**M11c is still not a real Quickshell restart recovery path.** The
production `ApolloHubTodoStore.stage()` does not consult the fixture;
its `FileView.onSaved/onSaveFailed` callbacks are not yet tied to
durable stage tokens. External filesystem writers may not cooperate
with an advisory lock. Two matching byte reads alone cannot prove
source immutability after the reads.

A real production recovery method must atomically bind all active stage
entry points to an exclusive writer, establish whether any FileView
callback/atomic rename remains outstanding, verify source and backup
with actual process ownership, retain a durable recovery history, and
obtain explicit operator approval before rearming. Normal QS startup
must retain safe task viewing while recovery is blocked.

The M10z on-device Quickshell runtime acceptance has not been performed
here and still needs separate authorization. No live migration or
production writer activation is implied by merging this test fixture.

## CHECKLIST

- [x] Verify M11b merged and inspect M10p/M11b authority source
- [x] Persist review-only source/epoch checkpoint in existing private fixture
- [x] One-time review after new OS owner fences the prior session
- [x] Test clean/unclean restart, source drift, pending saves and true crashes
- [ ] Complete CI and independent source review
- [ ] Operator-authorized M11c PR merge
- [ ] Native isolated QML runtime acceptance
- [ ] Production FileView stage gate and callback/owner integration
- [ ] Safe production recovery/rearm review and rollback
- [ ] Separately approved SQLite migration and activation

## NEXT

M11d should produce a **production integration plan, not an activation**:
inventory every actual TASKS/TODAY/PLANNER/Hub write entry and FileView
callback path, define the minimal atomic stage gate, source freeze and
recovery UX, and test any proposed QML patches only in an isolated,
operator-authorized environment. The operator must approve real local
modifications separately.

## DECISIONS

The JSON store remains the only active writer. No real desktop,
Quickshell instance, TASKS data, SQLite TASKS database, GitHub Project,
or live Hospital assignment is modified.
