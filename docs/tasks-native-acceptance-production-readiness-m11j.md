# 🏥💜 TASKS // M11j Native Evidence and Production Readiness

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / Assignment:** TASKS storage continuity, GitHub-only follow-up; no live Hospital registration assumed  
**Source-of-truth branch:** `main` reviewed on 2026-10-26  
**Current writer:** `services/hub/ApolloHubTodoStore.qml` JSON FileView only  
**Classification:** Operator-observed, isolated runtime acceptance + future design review. **Not a production activation.**

## IMPLEMENTATION

M11j records the real native acceptance carried out by the operator on
**October 26, 2026, America/New_York**, after the Quickshell
focus patch ([PR #821](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/821))
and deferred saved-callback reload patch
([PR #823](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/823))
merged. Existing M11g Python host and QML FileView harness operate
on synthetic, disposable `fixture-only.json` and `handoff-test.db`
outside the live task data directory.

**Evidence source:** screenshots and short statements supplied by the
operator in chat. They were interpreted visually at the time. No
original screenshots, private home paths, other-window contents, raw
fixture bytes, or database copies were uploaded to this repository.
Machine-readable **sanitized observations** live in
`tests/tasks/fixtures/task_native_acceptance_m11j.json`.

### Actual native observations, in chronological order

| Test | Operator-observed UI evidence | Disposition |
|---|---|---|
| Initial attach | `JSON_ACTIVE`, `FILE READY`, counter 0 | Observed pass |
| First synthetic increment | Counter 1; trace `FILE_SAVED → FILE_READBACK_OK → HOST_SETTLED`; one save chain | Observed pass |
| Second increment | Counter 2; two completed save chains | Observed pass |
| Freeze | `TEST_FROZEN`, `FREEZE_REQUESTED`, file FROZEN, counter 2, `testStageEligible=false` | Observed pass |
| Restart with EXISTING | `RECOVERY_REVIEW`, `HOST_EXITED`, recovered epoch 2, `testStageEligible=false`, counter 2 | Observed pass |

A previous attempt had stalled in VERIFYING after `FILE_SAVED`. The
deferred `Qt.callLater` reload in M11g/M11e resolved that observed
stall on the later native run. The original test authority from the
stalled attempt must remain treated as ambiguous/fenced; do not
re-bootstrap it.

The M11i label `OBSERVATION_ONLY_NOT_NATIVE_ACCEPTED` is intentionally
cautious. We can now say **the core isolated native sequence was
observed working**. We cannot say *every native failure scenario* or
the *production replacement* is accepted.

### Production writer readiness review

Current `ApolloHubTodoStore.qml` has precisely one `FileView`
writer and one `stage(result)` that owns all nine task/project
mutations (see M11d inventory). It guards the active state and
publishes a `pendingDocument` after `onSaved`.

It currently **does not** consult a durable OS-owned epoch/journal on
each real stage, tie actual FileView callbacks to durable stage IDs,
perform independently verified source readback before publishing a
task mutation, or automatically reconcile a new process after an
uncertain write. The M11g native pass does not magically install
those mechanisms. Likewise, the existing experimental SQLite-v2
store is not mounted as an active writer.

**Future production-gate patch, separately approvable:**

1. Preserve the current verified JSON reader and last confirmed
   snapshot while adding an operator-disabled, separately switchable
   gate mode. An operator-disabled mode cannot be described as
   OS-fenced. Avoid transient write enablement on startup.
2. Acquire actual OS ownership and durable epoch prior to *any*
   enabled gate admission. Inspect source identity, real schema and
   outstanding journal entries. Unknown prior owner means
   `RECOVERY_REVIEW`, not an empty writable list.
3. In the single `stage()` entry, require a durable stage reservation
   before assigning `pendingDocument` or invoking
   `todoFile.setText()`. Reject all other UI entry routes while a
   save is pending or the gate is closing.
4. On `onSaved`, defer readback beyond the native FileView callback,
   match the correct reservation and source bytes through a safe
   OS-owned host, and durably settle the operation **before**
   publishing the confirmed task document. On mismatched/failed
   callbacks, preserve last confirmed state and freeze for review.
5. Epoch-fence `onLoaded`, `onLoadFailed` and `reloadFromDisk()`
   so outdated loads cannot undo freezes or recovery reviews.
6. Persist closed admission before acknowledging freeze, drain only
   already-reserved saves and require fresh ownership review on every
   process restart.
7. Prepare and independently verify a backup and rollback path that
   restores the prior code/config without overwriting live task data
   or causing both JSON and SQLite writers to become active.
8. Separately prove model parity, durable schema/journal handling,
   recovery and source/backup readback before **any** separately
   authorized SQLite cutover.

This is a **design and acceptance gate**, not an approved or
implemented patch. The exact future source diff and runtime failure
tests need their own operator review.

## HOW TO USE

Repository-only verification:

```sh
python3 tests/tasks/test_task_native_acceptance_m11j.py
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
python3 tests/tasks/test_fileview_deferred_readback_m11.py
python3 tests/tasks/test_task_fileview_crash_windows_m11h.py
```

No action is required on the operator's computer. Their unrelated
modified and untracked Quickshell test files can remain where they are.
No local pull, stash, reset, service restart or cleanup is part of M11j.

## VERIFY

- The M11j source test checks required screenshot-observed states,
  evidence provenance, absent native fault acceptance, and unapproved
  live writer/cutover gates.
- It rechecks the real JSON writer's exclusive `stage()` and
  FileView callbacks, no live import of the disposable test host,
  and that the native harness still carries the deferred readback,
  strict synthetic writer restrictions and on-demand focus.
- Existing M11d, M11h and deferred readback regressions rerun in CI.
- CI proves the **record and code constraints**, not that GitHub CI
  reproduced the operator's Wayland native test.

## WATCH OUT FOR

**Not proven by the submitted screenshots:** independent hash of
the synthetic source after restart, power-loss durability, real
FileView native error injection, all callback crash windows on the
desktop, malicious symlink replacement prevention, production owner
exclusive lock, correct handling of all real task/project metadata,
or SQLite cutover/rollback.

The counter of 2 on restart is FileView UI evidence, not a separate
byte-for-byte external file inspection. The post-freeze panel
advertises stage eligibility false; explicit post-freeze button
attempts were not separately evidenced in a screenshot. Likewise
the host's `HOST_EXITED` after `RECOVERY_REVIEW` is expected
fail-closed behavior, not a successful writer recovery/rearm.

No system-wide Hospital assignment, local runtime state,
or future migration authority is established by this report.

## CHECKLIST

- [x] Verify M11h/M11i/focus/deferred-reload GitHub merge status
- [x] Record operator-observed native attach/save/freeze/restart sequence
- [x] Preserve sanitized provenance and precise evidence limits
- [x] Inspect actual production writer and single-stage entry
- [x] Define future writer gate, error/reload, backup and rollback order
- [ ] Complete current-head CI and independent review
- [ ] Operator-approved PR merge
- [ ] Obtain separately scoped authorization for any real writer patch
- [ ] Verify native fault/error paths or explicitly document remaining risk
- [ ] Validate backups, rollback, full data model and stage epoch fencing
- [ ] Separately approve any SQLite migration and activation

## NEXT

**M11k, only after explicit scope approval:** review the smallest
production JSON writer *gate* patch (disabled by default), together
with a rollback plan and exact local validation procedure. No
automatic production change is implied by this record.

Until then the strongest supported status is:

**CORE ISOLATED NATIVE ACCEPTANCE OBSERVED · PRODUCTION WRITER NOT GATED · SQLITE INACTIVE.**

## DECISIONS

Existing `ApolloHubTodoStore.qml` remains the only active task data
writer. No live task data, local system files, running processes,
GitHub Projects or migration settings have been changed by M11j.
This milestone does **not** merge its own PR or activate anything.
