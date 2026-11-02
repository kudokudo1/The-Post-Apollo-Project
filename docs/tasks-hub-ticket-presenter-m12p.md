# 🏥💜 TASKS M12p // Hub To-Do Mini Disabled Ticket Presentation Seam

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity  
**ASSIGNMENT //** First UI consumer reconciliation, Hub To-Do Mini, behind a permanently disabled ticket mode  
**DOCTOR //** External Hospital-compatible ChatGPT worker, not live Hospital-registered  
**PROVIDER //** OPEN AI // CHATGPT  
**INSPECTED MAIN //** `cc35826e9c9df993d6f37cff224b1360485caee5`, November 2, 2026  
**CLASSIFICATION //** DISABLED-BY-DEFAULT PRODUCTION FILE *SOURCE EDIT*, **NOT** ACTIVE TICKET SAVE OR PRODUCTION ACCEPTANCE  
**PRIORITY //** No second writer, no local machine modifications, no migration, no browser/remote sync.

## IMPLEMENTATION

M12o PR [#996](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/996) was independently verified merged before M12p began. The live `services/hub/ApolloHubTodoStore.qml` still owns the only `FileView` and nine mutation routes, and `guardedWriterEnabled: false`. Its boolean mutation API still signals **admission**, not durable save; `onSaved` publishes the pending in-memory document.

This change touches the **first UI consumer only**:

- `widgets/hub/TaskHubTicketPresenterM12p.js`: pure helper for Hub To-Do Mini's four mutations. Calls M12o's existing pure reducer to reconcile an exact ticket, a synthetic test receipt and the expected full task view. If a synthetic completion receipt arrives while the store view is `saving`/`loading`, buffers it without clearing the draft, and waits for a stable matching view. Wrong ticket, wrong snapshot, error, rejected/blocked/review and late outcome do **not** clear the draft.
- `widgets/hub/ApolloHubTodoMini.qml`: imports that helper and adds a `readonly property bool ticketUiEnabled: false`, a null `ticketProducer`, and inactive methods to submit/observe ticket outcomes. When disabled (always, in this patch) **all existing add/rename/done/delete and reload paths remain the original ones**, their UI geometry remains intact, and the old onSaved-snapshot reconciliation remains unchanged. The new path is a future seam, not an actual enabled feature.
- `tests/tasks/test_task_hub_ticket_presenter_m12p.cjs`: tests all four actions against the **actual** task v3 policy, unrelated tickets, early receipt/stale snapshot, missing synthetic receipt, error/review, immutable drafts, and static checks ensuring the live guard, one FileView and all existing four methods remain intact.
- Scoped GitHub Actions CI runs M12p, M12o, M12n, M12m, M12i, M12k, M11t and M11d checks.

### What the disabled QML seam expects in a future separately approved integration

The pending API shape is:

```text
ticketProducer.submit("HUB", method, {args: {...}, draft: {...}})
       -> {admitted: true, ticketId, expected: fullView, baseline?: fullView}

ticketProducer.ticketEvent(event)
       -> {ticketId, state, evidence}

todoSnapshot change -> observe current confirmed view
       -> clear matching draft ONLY after verified ticket AND expected full view
```

The expected task view must be supplied by a future **trusted local coordinator** when the ticket is admitted. The UI does not infer it from the legacy boolean result. The API must not emit a completion synchronously before the consumer has registered the returned ticket; actual ordering/replay semantics require their own review.

The current M12o façade always refuses `submit()`, so the new M12p path must remain disabled. `SYNTHETIC_READBACK_RECEIPT` is a **test-only marker** and is trivially forgeable in QML/JavaScript. It does not authenticate native FileView, source provenance, or a malicious same-UID process. The literal false QML flag cannot be switched by a settings preference. It requires a separate, reviewed source change.

### Actual existing Hub semantics deliberately preserved

| Action | Unchanged default path | Disabled ticket path's required behavior |
| --- | --- | --- |
| Add | Save request via `addTask`; clear input on original snapshot transition | Preserve input until matching ticket + expected full view |
| Rename | `renameTask`; restore pre-rename add text only on original success | Do not erase rename or restore text prematurely |
| Complete/uncomplete | `setTaskDone`, original pending state | Do not claim a toggle saved until ticket confirmed |
| Delete | Two-click NO/YES confirmation, `removeTask(id,true)` | Keep destructive confirmation until matching committed result |

Details, Planner and Projects QML are **unchanged**. This is intentional: adapting all four at once would increase rollback and regression risk.

## HOW TO USE

No local actions. The new feature path is **hard-disabled**, so the current Hub To-Do and TASKS panes operate normally. GitHub CI can exercise its pure presenter with:

```sh
node --test tests/tasks/test_task_hub_ticket_presenter_m12p.cjs
```

This doesn't import a native FileView, start Quickshell, access real tasks, require credentials, or affect GitHub synchronization.

## VERIFY

- Four Hub actions tested against current `ApolloHubTodoPolicy.js`.
- Ticket status cannot clear a draft until an exact expected task snapshot is provided alongside the test receipt.
- A receipt delivered while the store view is `saving` remains buffered and is reconciled only when a future stable view arrives.
- A different ticket, missing evidence, stale data, error/recovery and reordered callbacks cannot accidentally promote UI success.
- `ApolloHubTodoMini.qml` maintains a compile-time readonly false ticket flag, null producer and all legacy method invocations.
- Single production `FileView`, all nine mutation paths and `guardedWriterEnabled: false` remain unchanged.
- **No native QML runtime test of M12p** is included. GitHub CI is a source/test-model boundary, not proof of a live ticket UI.

## WATCH OUT FOR

- No actual production ticket producer exists. The new branch does **not** create one and does not enable ticket mode. `ticketProducer` is an optional future injected dependency currently always null, and the connection signal is detached while disabled.
- This is a code edit of a **live UI source file** but with no expected runtime behavior change. Native QML load and rendering must still be checked separately before claiming acceptance. Production deployment is not performed.
- A synthetic receipt and full-view equality alone do not prove that the correct process wrote the authoritative JSON file or that two separate resources are atomically committed. M12k explicitly demonstrates this weakness.
- Cross-process ticket IDs, offline replays, independent OS source verification, persisted journal, native callback acceptance, background GitHub sync and multi-device identity conflict resolution all remain future work.
- Existing M11t/M12b production security gates are open; this patch neither waives nor satisfies them.
- If `ticketUiEnabled` is ever changed from false, the resulting behavior is **not approved** by this PR. The future producer, callback contract, draft persistence and rollback plan require fresh verification and operator acceptance.

## CHECKLIST

- [x] M12o merged verified and no active competing TASKS PR
- [x] Existing Hub To-Do Mini actions and reconciling UI code inspected
- [x] Add M12p pure presenter for the four Hub methods
- [x] Add disabled-only QML seam without touching storage or existing methods
- [x] Add policy-driven draft and late-receipt regression tests
- [ ] CI green and final diff audit
- [ ] Operator review and merge
- [ ] Native no-regression UI verification on the actual device, separately approved
- [ ] Future approved trusted ticket producer, then gradual activation of Hub consumer
- [ ] Other three consumer migrations, one by one

## NEXT

Review the draft M12p PR and its CI. Before any ticket-mode activation, build and test the **actual trusted local ticket producer** under M12l architecture, reconcile its completion with the native FileView and source receipt, and independently verify the data boundary. Only then authorize enabling the new UI path for Hub. No privileged broker or second writer is required by this M12p feature.

## DECISIONS

**Implemented:** First Hub-specific ticket and draft presenter, ticket API wiring behind a QML readonly literal false, real-policy unit tests and compatibility inventory.

**Unchanged:** Single live writer, legacy boolean APIs and all four production consumer behaviors, including Hub's original save-confirmation path while the feature flag stays false.

**Not authorized:** Production ticket mode activation, real TASKS source access, local Fedora edits or Quickshell restart, storage migration/restore, GitHub task sync, additional OS service, or merging this PR.
