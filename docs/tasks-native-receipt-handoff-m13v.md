# 🏥💜 TASKS // M13v Native-Callback to Source-Receipt Handoff

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS opt-in encrypted recovery / durable source coordination  
**STAFF ROLE //** DOC, external Hospital-compatible worker, provider OPEN AI // CHATGPT; live Hospital connection unverified  
**BASE //** main `1c1d05db5654720cd11431005fe49f550f9c66de` (November 6, 2026)  
**PERMISSIONS //** Bounded GitHub tests, CI, documentation only. No local Fedora modifications, production QML changes, merge, stage activation, real-task data, keyring or Connections shared authentication edits.

## IMPLEMENTATION

Merged M13u #1351 verifies revision-chain continuity in the existing disposable SQLite M12h journal with independent M11g saved-file readback. Connections C2u is concurrent but owns only its own OS package/SELinux side. M12l accepted ADR prefers a **single local TASKS storage coordinator**; do not add a privileged broker simply because one can be built.

**This milestone reuses the existing owner, not a second writer.** New `TaskNativeReceiptHandoffM13v.py` is an unmounted disposable integration facade around exactly the existing M12h `DisposableStageReceipt` and M13u `inspect()`. It accepts an existing synthetic stage ID only when the source has a verified current fixture baseline, the journal has no in-flight stage, and M10p ownership is active. The first synthetic stage requires an existing valid M11g revision-zero seed; absence never grants first-create or repairs the source.

The handoff models the native FileView sequence: reserve stage → simulate FileView source write **in test harness only** → advisory `FILE_SAVED` hint → request independent M12h source readback → settle in the **existing** SQLite journal transaction → M13u inspect revision chain → return `SYNTHETIC_RECEIPT_OBSERVED_UI_UNACKNOWLEDGED`. The facade itself neither writes the JSON file nor opens/creates a journal.

`FILE_SAVED` merely marks a native hint and **does not** advance the journal or acknowledge the task as saved. A missing hint, wrong stage ID/epoch, duplicate callback, failed file load/save, interrupted stage, missing or rolled-back source, unexpected revision chain or post-settlement discrepancy leads to conservative pending/review. An ambiguous outcome is never retried or automatically cleared. A fresh OS process inherits M10p's deliberate `RECOVERY_REVIEW`, so it cannot acquire an active synthetic write receipt.

All returned authority flags remain **false**, including `independentNativeCallbackAuthenticated`, `durableUserSaveAcknowledged`, `keyReleaseAuthorized`, `taskWriteAuthorized`, `captureAuthorized`, `previewAuthorized`, `restoreAuthorized` and `automaticRecoveryAuthorized`. Neither task body nor draft text is present in any returned response.

## HOW TO USE

There is no new desktop control. GitHub Actions runs:

```bash
python3 -B -m unittest discover -s tests/tasks -p 'test_task_native_receipt_handoff_m13v.py' -v
```

The original TASKS → SYNC → RECOVERY and CPU++ → SETTINGS → CONNECTIONS → TASKS remain read-only for draft recovery. The fixture is **not** imported by either widget, the singleton, or the shared Connections broker.

## VERIFY

- Initial source: existing valid synthetic seed required, never treat missing/corrupt saved JSON as clean first install.
- Reserved stage: journal reports pending and source remains untouched until a **test-owned** simulated FileView write.
- `FILE_SAVED` before write: no ACK; independently reread source rejects and requires review.
- Correct simulated write + subsequent native hint: M12h settles and M13u gives sequential revision 1 then 2, both UI-unacknowledged.
- No hint, stale/wrong stage ID or owner epoch, duplicate hint, failure hint: no automatic settlement or replay.
- Source rollback: refused against last settled journal revision.
- Fresh independent interpreter: journal history observable but no new stage permitted until operator review.
- **Explicit known weakness test:** a test process that writes exactly the expected bytes and supplies a fake native hint can still produce a byte-consistent synthetic receipt. This is a deliberate regression demonstration of M12k's hostile same-UID limitation, **not a successful proof of native FileView provenance**.
- CI reruns M13u, M12h, M12k, M13t, M11d and C2a checks.

## WATCH OUT FOR

The native hint and source bytes are **not independently authenticated**. Any same-UID writer that can tamper with the source may forge expected bytes; the final readback can be raced after inspection; and a SQLite receipt and file replacement are not one atomic transaction. Real production requires a source owner with appropriately scoped file custody and an enforceable compare-and-commit fence, along with native callback attribution, recovery for lost acknowledgment and signed/verified release trust. Do not turn an M13v status into `userSaved:true` or assume this proves physical crash/power-loss durability.

Real Connections operator/caller authentication remains another owner's scope. None of M13t, M13u or M13v creates genuine permission to capture/preview/delete drafts or restore TASKS after restart.

## CHECKLIST

- [x] Recheck merged M13u, canonical Syntagma, current main and no competing TASKS PR
- [x] Reuse M12h source/journal, M13u revision evidence, M10p lock and one actual JSON writer
- [x] Implement bounded unmounted native-hint/readback handoff
- [x] Test success and fail-closed callback/restart/race scenarios, preserve known hostile writer gap
- [x] Add targeted CI and docs
- [ ] PR-head GitHub CI and independent review
- [ ] Operator review/merge
- [ ] Production source-owner receipt and real Quickshell native callback tests
- [ ] Independently authenticated Connections host, explicit three-scope consent, key lifecycle
- [ ] Real opt-in encrypted draft storage, restart/reboot and operator UI acceptance

## NEXT

The next actual integration must establish **a source-owner / native-FileView fence that cannot be supplied by a simulated QML callback**. Design a carefully authorized, disabled-by-default production adapter on the sole `ApolloHubTodoStore.qml` admission path; decide how to distinguish ambiguous `onSaved`, independently read back authoritative source, and display last-confirmed versus pending draft across all four consumers. Treat first-create authorization, file custody and real signed host as separate gates. Do not modify the shared C2u Connections host until that owner coordinates an authenticated API.

## DECISIONS

No new JSON writer, SQLite production migration, privileged daemon, local task-file manipulation, keyring activation, automatic replay, automatic merge or operator acceptance. The M13v fixture demonstrates mechanics and refusals only; it does **not** establish real production task durability.
