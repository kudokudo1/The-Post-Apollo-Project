# 🏥💜 TASKS M12x // Native FileView Callback Reentrancy and Disk Evidence

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** Explain and isolate the operator-observed `STORE_STUCK_SAVING` in the disposable M12u harness  
**WORKER //** External Hospital-compatible ChatGPT doctor, not verified registered  
**INSPECTED MAIN //** `3dbcb653b19320253e91486345ee527e1a63765e` (November 2, 2026)  
**CLASSIFICATION //** Test-only QML/runner repair. Actual root cause requires native rerun.

## IMPLEMENTATION

### Evidence before change

The operator updated their local checkout, ran the M12w test, and posted:

```text
M12u // FAIL // STORE_STUCK_SAVING
Native stages: INITIAL_EMPTY, TICKET_DISABLED // 2/4
Expected next: NATIVE_SAVE
Native terminal: FAIL/STORE_STUCK_SAVING
Quickshell: M12U_QML_OBJECT_STARTED
```

This shows the synthetic store reached `saving` and remained there at its 20-second deadline. It **does not prove that FileView failed to write bytes**, only that the expected confirmed state never occurred. The runner formerly discarded the whole temporary test directory without independently inspecting source on a native FAIL, so the last test left no source evidence.

### Specific potential mechanism

The existing M12u `Connections.onStorageStateChanged` synchronously calls `smoke.advance()`. When the shared store handles a not-found load, `FileView.onLoadFailed` sets `storageState="empty"`; the `storageStateChanged` handler can run **before that native FileView callback returns**. M12u immediately invoked `ApolloHubTodoStore.addTask()` from this nested callback, which invokes `FileView.setText()` while the prior load event may still be handling an error. This is unlike the earlier M12s operator-clicked write that persisted one task. This is a concrete source-level event-ordering risk, **not yet a verified causal explanation**.

The same reentrancy exists after a successful save: `FileView.onSaved` sets `storageState="ready"` and M12u immediately tried `reloadFromDisk()` during its native save callback.

### M12x narrow repair

- **No production code changes.** Modify only the unmounted `TaskNativeSelfReportM12u.qml` fixture. Defer its single synthetic `addTask()` using `Qt.callLater`, so it runs after the initial native load callback unwinds. Likewise defer its single `reloadFromDisk()` beyond the saved callback. `writeDispatched` and `reloadDispatched` ensure the existing 100 ms read-only poll cannot mistake an *enqueued* call for completed native work.
- All existing `safe` private XDG path/env/compile-time-disabled flags are checked again before the one deferred mutation; if they no longer match, **fail without writing**. There is no retry, second writer, new FileView, service, or production activation.
- **Independent native-FAIL disk diagnosis.** The Python runner observes only the already-created *temporary* fixture after stopping its child and **before** the temporary directory is deleted. It prints a fixed-vocabulary classification: parent directory missing, source missing, valid single synthetic v3 task, invalid JSON/schema, wrong task/count or unsafe file. This is read-only and never changes `FAIL` to `PASS`.
- Add deterministic CI-only tests for the deferred one-write/one-reload source contract and disk classifier; retain M11d inventory, M12r/M12s/M12u and M11t gates.

## HOW TO USE

After operator review/merge and a **separately controlled** safe source update, run the same existing test:

```sh
cd ~/.config/quickshell
python3 tests/tasks/fixtures/TaskNativeSelfReportRunnerM12u.py
```

No additional setup or extra user interaction. The test creates an owner-private synthetic XDG root, starts only a separate test Quickshell process, and stops **only that child**. It leaves the live desktop, real tasks, existing untracked files and Git worktree untouched.

When native test fails, the report gains one decisive diagnostic line, for example:

```text
M12u // FAIL // STORE_STUCK_SAVING
...
Fixture after test: SOURCE_PRESENT_EXPECTED_SYNTHETIC_V3
Fixture observation is diagnostic only; it cannot override FAIL
```

The sample line is **illustrative**, not an already observed outcome.

## VERIFY

Source review: exact current singleton has one `FileView` with `blockWrites:false`, `atomicWrites:true`, and `watchChanges:false`; `onSaved` transitions to `ready`, while `onSaveFailed` transitions to `error`. Quickshell documents that `FileView.setText()` emits `saved()` or `saveFailed()` on completion. It does **not** prove callbacks fire in this specific nested native event order.

**CI:** M12u self-report test expanded with private disk observations and deferred source checks; original M11d writer inventory and production-disabled tests should remain green. Actual native Qt, callback ordering and disk states still require the operator's isolated rerun.

**No accepted full native pass yet.**

## WATCH OUT FOR

- File persistence and confirmed singleton state are different. If the next result is `SOURCE_PRESENT_EXPECTED_SYNTHETIC_V3` but `STORE_STUCK_SAVING`, do not overwrite or recreate data to "fix" the panel. Investigate callback registration/completion attribution. If the file or data directory is absent, investigate the actual parent/path/atomic-write failure, not phantom UI signaling.
- `Qt.callLater` is a test-only sequencing adjustment, not an independent source authorization, durable stage receipt, or proof that no same-UID peer can race.
- The post-failure disk inspector reads only the synthetic hard-coded fixture; it never attempts to restore, repair, or expose raw contents.
- The existing 20-second timeout, no automatic retry, one mutation and one reload remain. No production ticket/guarded flag changes are authorized.
- The user's local checkout previously had untracked items; do not clean/reset them to install this fixture.

## CHECKLIST

- [x] Reconstruct M12w native failure, live source and current GitHub HEAD
- [x] Identify nested `onStorageStateChanged` → `addTask()` and `reloadFromDisk()` ordering risk
- [x] Defer only those synthetic actions, preserve strict private path/environment guards
- [x] Add read-only synthetic file outcome classification on native FAIL
- [x] Add private fixture tests
- [ ] Source CI success / independent review
- [ ] Operator PR review and merge
- [ ] Operator-controlled local checkout update
- [ ] Native rerun to confirm or reject reentrancy hypothesis and independently observe temporary source
- [ ] Final production activation authorization, only after separate gate review

## NEXT

Use actual next native PASS/FAIL and disk classification to fix only a proven issue, not broaden the storage architecture. Keep M12l one-writer design, M12t preflight and ticket-disabled mode. If source remains absent, evaluate directory creation and FileView error signaling in a **standalone test**, not the production writer.

## DECISIONS

**Proposed correction:** test-only deferral and failure-disk inspection, no live data mutation.  
**Not established:** the native failure's cause, restored callback functionality or production acceptance.  
**Unchanged:** no persistent helper, no privileged broker, no SQLite migration, no Hospital live registration, no merge authority assumed.
