# 🏥💜 TASKS M12n // Isolated Native FileView Ticket Observer

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** M12n, standalone native ticket observation on the already-tested M12i FileView/receipt path and four caller boundary inventory  
**DOCTOR //** External Hospital-compatible ChatGPT worker; no verified live Hospital registration  
**PROVIDER //** OPEN AI // CHATGPT  
**INSPECTED MAIN //** `88ca0894c8c416627be77944db626c0356b84a04` (November 2, 2026); verify latest before edits  
**CLASSIFICATION //** ISOLATED UNMOUNTED NATIVE TEST WRAPPER; NOT PRODUCTION QML INTEGRATION OR NATIVE RUNTIME ACCEPTANCE.

## IMPLEMENTATION

### M12m handoff and ownership

[M12m PR #989](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/989) is merged. Its `TaskLocalTicketCoordinatorM12m.cjs` models serialized, disposable-file FIFO tickets and independent exact source readback. It is not importable into native QML as-is (CommonJS and Node APIs are deliberately test-only), and is not a new production storage service. M12n **does not** create a second writer to approximate it.

[M12i](./tasks-native-receipt-integration-m12i.md) already has an operator-observed single `FileView` + one `Process` Python host, with two native settlements and a durable synthetic SQLite stage receipt chain from [M12j](./tasks-m12j-checkpoint-and-external-writer-boundary-m12k.md). Its `onSaved` callback is only a reload hint; after a deferred reload, the independent test host compares actual source bytes to a stage it previously reserved before emitting `TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED`. These are still **synthetic OS host observations**, not authenticated callback provenance.

### New unmounted files

- `TaskNativeTicketHarnessM12n.qml`: new root-level Quickshell standalone config, **not included by `shell.qml`**. It instantiates the unmodified M12i lab exactly once and the ticket overlay once. The only native `FileView` remains the one inside the existing M12i component. No second `Process` is introduced.
- `tests/tasks/fixtures/TaskNativeTicketLogicM12n.js`: pure ticket-state reducer. A ticket is created in `QUEUED`, armed only with the native lab's actual pending synthetic stage ID, then follows `RESERVING`, `WRITING`, `VERIFYING`, `SETTLING`, `CONFIRMED` or `REVIEW_REQUIRED`. A stale status, changed stage, unexpected epoch/counters, host exit or invalid observation cannot confirm. Terminal outcomes are monotonic.
- `tests/tasks/fixtures/TaskNativeTicketAdapterM12n.qml`: small Quickshell overlay with **TICKET INCREMENT**. It calls only M12i's existing `increment()`, observes native properties/receipt count, and shows the session-local ticket ID/state. It reports if the original M12i lab's **INCREMENT** button is used out of band; it does not silently attribute that save to its ticket.
- `tests/tasks/test_task_native_ticket_bridge_m12n.cjs`: pure reducer test vectors plus static audit of one FileView, one native process, no new shell import, no real TASKS path, and every existing consumer still using its legacy boolean method.
- Scoped CI workflow.

**Meaning of `CONFIRMED` for M12n:** the unchanged M12i synthetic host has reported `TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED`; exactly one counter and one receipt increment occurred for the single armed stage, and the native lab has returned to `JSON_ACTIVE` / `READY` with no pending stage. This is **host-reported settlement and QML UI state correlation**, not independent authenticated native callback proof. Only the previously observed M12j fixture, not CI, has real native runtime observation.

### Crucial difference from M12m

M12m demonstrates **FIFO queuing and a disposable JSON coordinator** in Node. M12n demonstrates **one ticket observing one actual native M12i stage** in an unmounted QML bridge. It intentionally refuses multiple in-flight ticket requests because the M12i host supports exactly one active stage. M12n is a bridge experiment, **not** a finished QML production port of M12m's FIFO queue, durable coordinator or asynchronous public TASKS API.

### Four live caller reconciliation targets (inventory only)

| Current consumer | Existing synchronous `todoStore` calls | Future necessary adjustment |
| --- | --- | --- |
| `widgets/hub/ApolloHubTodoMini.qml` | `addTask`, `renameTask`, `setTaskDone`, `removeTask` | Differentiate admission from durable confirmation; preserve edit on failed completion |
| `widgets/tasks/TaskDetailsPane.qml` | `updateTaskDetails` | Confirm details only when save result is confirmed; retain draft on failure |
| `widgets/tasks/TaskPlannerSchedulePane.qml` | `addTask`, `updateTaskDetails` | Preserve planner drafts across ambiguous write or recovery state |
| `widgets/tasks/TaskProjectsPane.qml` | `createProject`, `renameProject`, `deleteProject`, `assignTaskProject` | Deletion/assignment feedback must reflect committed revision, not queue admission |

These callers are **not modified by M12n**. None yet has a production ticket callback or last-confirmed overlay. A subsequent approved assignment must reconcile all four and preserve their existing user interactions and save-error behavior.

## HOW TO USE

**GitHub CI** runs the pure reducer and static boundaries only:

```sh
node --test tests/tasks/test_task_native_ticket_bridge_m12n.cjs
```

**Future operator-approved native demonstration (not run in this PR):** Use a newly seeded, owner-private M11e fixture, **not** an existing TASKS source and **not** the previous frozen M12j fixture. Verify the current local branch/diff and separately launch:

```sh
qs -p "$HOME/.config/quickshell/TaskNativeTicketHarnessM12n.qml"
```

The original M12i lab appears with its path/writer inputs and NEW TEST/EXISTING/FREEZE/STOP controls. The second M12n window shows ticket status. In the original lab, enter the **exact private fixture path**, never an unexpanded `*` wildcard, and a fresh synthetic owner ID. Click **NEW TEST** only for an actually fresh, separately approved fixture. Once `JSON_ACTIVE`/ `READY`, click **TICKET INCREMENT** **in the M12n window**, rather than the original M12i INCREMENT. Expect `QUEUED` → `RESERVING` → `WRITING` → `VERIFYING` / `SETTLING` → `CONFIRMED` after the M12i host's settlement; a rapid transition can skip rendering intermediate states. Optional second ticket is allowed **only after the first is terminal**. Freeze, STOP, and stop only this standalone `qs` process, never `pkill -x quickshell`.

This is a **future manual procedure requiring explicit local approval**, not authorization to launch from this PR. Review the private journal and source read-only after native tests. No real tasks or production source permission is implied.

## VERIFY

- GitHub main inspected before branch; #989 merged, no competing open TASKS PRs at entry.
- M12n wrapper contains only **one instance of M12i**, which contains one `FileView` and one `Process`.
- The adapter never instantiates `FileView`, `Process`, a socket, a privileged helper or a TASKS production source.
- New pure reducer tests reject wrong stage, stale counter/receipt, host exit, epoch changes, and an apparent settlement without matching counter/readiness.
- Existing M12m test verifies the FIFO coordinator separately; M12h/M12i tests continue verifying synthetic host readback and durable stage receipt behavior.
- Existing production still has one `FileView`, nine `stage(TodoPolicy.*)` routes, `guardedWriterEnabled: false`. No call sites changed, and the original live boolean's meaning is unchanged.
- **Native QML launch/routing is not tested in GitHub CI**. This is a source and unit test implementation until the operator runs and reports native results.

## WATCH OUT FOR

- This is still an *advisory UI layer*. A forged same-user source write with correct bytes can produce a matching receipt, as M12k proved. An untrusted QML signal cannot certify native writer identity.
- The original M12i INCREMENT button remains available in its separate window. M12n flags any out-of-band settlement but does **not** revoke M12i or prevent it. This is a limitation of test composition, not a production design.
- `CONFIRMED` does not mean real TASKS was saved or cloud sync occurred. No durable ticket ID across restarts; the queue from M12m is not yet ported to QML.
- `RECOVERY_REVIEW` and failed native observations block new M12n ticket submission. A fresh native owner should not auto-replay an incomplete previous session.
- The old M11t and M12b production gates remain OPEN. M12l's simpler in-application coordinator direction is accepted but must be reconciled with those gates explicitly, not silently waived.
- Integration with the four live callers and any local Quickshell launch requires separate operator authorization.

## CHECKLIST

- [x] Reconstruct GitHub main and verify merged M12m
- [x] Reuse M12i native FileView/host rather than create second writer
- [x] Implement isolated ticket observer and reducer
- [x] Inventory four live consumer call surfaces without editing them
- [x] Add reducer and static safety tests
- [ ] GitHub CI and final scoped diff
- [ ] Operator review/merge
- [ ] Explicit approval for local native M12n run
- [ ] Native ticket state screenshots and independent source/receipt inspection
- [ ] Separately approved disabled-only real public API reconciliation with all four consumers
- [ ] Production activation only after new operator acceptance and reconciled security gates

## NEXT

Verify CI, review the draft M12n PR, and obtain separate operator permission for a fresh **native isolated lab test**. If native behavior matches the reducer contract, follow with a dedicated disabled-only production-facing API patch that preserves one file writer and requires explicit final activation review. Do not add an OS-privileged broker by default.

## DECISIONS

**Implemented here:** One M12i-instance native ticket observer for a single synthetic stage, pure JS stage-correlation reducer, four-caller contract inventory and test-only CI.

**Unchanged:** One production TASKS FileView, native source path, task v3 policy, existing M12h/M12i host, original consumer behavior, `guardedWriterEnabled: false`.

**Not authorized:** Local file edits, launching/restarting the user's Quickshell, read/write of actual task data, new privileged service, task migration, source/backup restore, production activation, PR merge or live Hospital registration.
