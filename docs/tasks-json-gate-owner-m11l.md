# 🏥💜 TASKS M11l // Locked-Off Live Seam + Real-Schema Owner Candidate

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / assignment:** TASKS storage continuity, Proxy 1 → Proxy 2 succession  
**Source:** M11j native observed acceptance + merged M11k gate contract  
**Staff role:** External Hospital-compatible continuation worker, no live Hospital registration verified  
**Status:** Draft source milestone, production gate **NOT ACTIVE**  
**Base HEAD (at branch creation):** `156783e3fd70c06ed53e680bc0f4e1d5d863a14d`

## IMPLEMENTATION

The one live `services/hub/ApolloHubTodoStore.qml` retains the original JSON FileView behavior. It now declares a **readonly, compile-disabled** `guardedWriterEnabled: false` and refuses `stage()` if guarded mode is ever requested without a verified gate. Because the property is locked off, existing TASKS/TODAY/PLANNER/Hub writes follow the original legacy path, including the existing synchronous `true/false` return contract, six-state public snapshot and `onSaved` behavior. **This addition does not provide OS ownership while legacy mode is active.**

A separate Python `services/projects/TaskJsonGateCandidateM11l.py` implements the host's **test-only core** on a disposable directory named `m11l-tasks-copy`, containing an explicit `todo-copy.json`. It:

- Reads stable, user-owned/private regular files with no-follow/inode checks and exact byte limits; validates the existing JSON v1/v2/v3 task and project schema.
- Holds an exclusive OS `flock` across test transactions, and records a SQLite journal with an epoch, source hash, pending stage and target hash.
- On **explicit fresh test bootstrap only**, creates a byte-for-byte backup, fsyncs it and independently reads it back before admitting a stage.
- Durably reserves exactly one stage, confirms expected bytes after an *external simulated FileView* atomic replace, and settles that stage before accepting another.
- Freezes stage admission, rejects competing owners, and changes any new process/reopen to `RECOVERY_REVIEW`, without auto rearm or replay.

The Python module contains **no CLI, no production enable switch, no Quickshell host Process connection, no source writer and no implicit startup**. Its file path is restricted to disposable test copies, deliberately not the real `apollo-hub-todo-v1.json`. This is a substantial foundation but **not** a completed production host or its live callback integration.

## HOW TO USE

There is no new control in TASKS. Existing TASKS → PLANNER → SCHEDULE continues as before. Source-only / disposable CI tests:

```sh
python3 tests/tasks/test_task_json_gate_candidate_m11l.py
python3 tests/tasks/test_task_native_acceptance_m11j.py
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
python3 tests/tasks/test_task_production_gate_review_m11k.py
```

Tests create only private temporary `m11l-tasks-copy` data and never read personal task files. Do **not** run this against your live Quickshell data, copy task contents into an issue, or modify `shell.qml`.

## VERIFY

M11l Python tests exercise v1/v2/v3 read-only validation, two simulated FileView atomic saves, durable stage readback, wrong callbacks, source drift, interrupted pending stage, fresh owner recovery review, OS flock contention, freeze behavior and backup byte equality. The full CI suite also reruns M11j/M11k/M11d no-activation boundaries.

**Limits:** Python tests simulate FileView by an external fixture-only atomic rename. They do not establish native Quickshell callback order, process JSON-lines behavior, power-loss durability, production file authority, real-time data parity or recovery usability. Passing CI does not authorize activation.

## WATCH OUT FOR

- `guardedWriterEnabled` being false is *not* a protection against existing external JSON writers. The original path is unchanged.
- The host candidate deliberately cannot be invoked as a production daemon. A future **new, explicitly reviewed** Process bridge must correlate owner epoch, stage ID, native FileView completion, deferred `Qt.callLater` reload, host-side independent verify/settle, and UI snapshot publication. No QML test fixture receipts should be trusted as production ownership.
- The task schema validator is an independently authored Python port; validate it against JS policy edge cases before real admission. Existing task content must not be leaked into logs.
- Source backup and restore, recovery review, real JSON provenance, startup/read callbacks, separate OS-owned daemon launch and full production rollback remain incomplete.
- The operator's local Quickshell worktree, untracked tests and running shell remain untouched. **Do not merge/activate** as a substitute for native acceptance and production approval.

## CHECKLIST

- [x] Recheck merged M11k / current shared writer and GitHub ownership
- [x] Preserve legacy six-state/synchronous store with compiled-off gate seam
- [x] Implement disposable real-schema OS lock + journal candidate
- [x] Add source-only + synthetic disk failure tests
- [ ] Validate tests/CI and independent review
- [ ] Design production-specific long-lived Process protocol and stage callback adapter
- [ ] Add real guarded QML state/readback correlation without changing legacy behavior
- [ ] Test native callbacks, source/backup identity, failures, actual rollback
- [ ] Separately approve local installation, guarded-mode activation and later SQLite cutover

## NEXT

Review the M11l draft and current CI. The next bounded milestone is a **separately reviewable non-activated QML ↔ OS-host handshake** compatible with real JSON payloads; it must not simply turn the compile-disabled flag on. Preserve the last confirmed TASKS snapshot on all errors, and retain the legacy writer until an operator-approved, fully tested cutover.

## DECISIONS

No production gate is active. JSON remains the sole live task writer. SQLite task migration and GitHub Project writes remain inactive. This draft does not merge itself, change local files or certify its own production readiness.
