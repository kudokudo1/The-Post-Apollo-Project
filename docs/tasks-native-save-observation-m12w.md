# TASKS M12w // Bounded native save observation

## IMPLEMENTATION
Patient: `kudokudo1/The-Post-Apollo-Project`. Room: TASKS JSON writer continuity. Worker: external Hospital-compatible ChatGPT; not verified live Hospital-registered. Source preflight: `main` at `845fe3d0f4661eed184d492be8b08f48a6b84d32` on November 2, 2026.

The operator's second M12u native test definitively reported `INITIAL_EMPTY` and `TICKET_DISABLED`, then `NATIVE_CALLBACK_TIMEOUT` with `NATIVE_SAVE` absent. The screenshot showed isolated `WAIT_SAVE`. **This establishes an incomplete save-confirmation observation, not whether the disposable file was written.**

The existing `TaskNativeSelfReportM12u.qml` uses `Connections.onStorageStateChanged` to drive advancement. M12w adds a **read-only, bounded 100 ms observation Timer** while its existing 20-second deadline remains in force. The Timer rereads only `ApolloHubTodoStore.storageState` and calls the existing `advance()` method, so a missed notification cannot leave an already-ready snapshot stranded. It **never** stages a second write or triggers a retry. The deadline now distinguishes `STORE_STUCK_SAVING`, `SAVE_STATE_NOT_READY`, and `RELOAD_STUCK` instead of treating every timeout as the same callback error. Native state and disk inspection both remain required for a PASS.

## HOW TO USE
No local changes or test execution performed by this PR. After operator review/merge and safe source update, run the existing isolated command:
```sh
python3 tests/tasks/fixtures/TaskNativeSelfReportRunnerM12u.py
```
The test launches its own disposable Quickshell process, not the live shell.

## VERIFY
Source test now asserts polling, timeout distinctions, unchanged single synthetic `addTask`, single `reloadFromDisk`, and unmounted test root. Existing CI remains scoped to fixture-safe behavior. **No native outcome is claimed until the operator re-runs.**

## WATCH OUT FOR
If `STORE_STUCK_SAVING` is reported, the actual native `FileView.onSaved` callback or path may be failing; this patch does not modify that production writer. A passing poll-reconciled run could indicate a missed QML notification, but it does not establish authenticated callback provenance or OS-level durability. The runner deletes its temporary fixture on completion. Do not modify live tasks, reset the user's dirty worktree, or enable the future ticket producer to make a test pass.

## CHECKLIST
- [x] Confirm current GitHub baseline and no open TASKS PR
- [x] Preserve operator's exact observed native output
- [x] Add bounded read-only polling and more precise timeout codes
- [x] Preserve one mutation, one reload and disabled ticket guards
- [ ] GitHub CI, operator merge
- [ ] Repeat independent disposable native test and establish real failure cause
- [ ] Production ticket activation remains unauthorized

## NEXT
Observe which state the native singleton actually reaches and the independent source-readback outcome. Fix only the proven failure. Avoid further infrastructure or privileged writer proposals.

## DECISIONS
No production storage code, no new FileView, no service, no local machine mutation. No claims of native acceptance or final DONE.
