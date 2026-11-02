# 🏥💜 TASKS M12o // Disabled-Only Consumer Save Ticket API

> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
> **ROOM //** TASKS JSON writer continuity  
> **ASSIGNMENT //** Reconcile local completion semantics for all four existing UI consumers while preserving the current single production writer  
> **DOCTOR //** External Hospital-compatible ChatGPT worker, not registered in live Hospital  
> **PROVIDER //** OPEN AI // CHATGPT  
> **INSPECTED MAIN //** `7e535843da7dee225f55201357b00929f14aaec6` on 2026-11-02; recheck for future work  
> **CLASSIFICATION //** **DISABLED-ONLY PUBLIC API SHAPE + PURE RECONCILIATION TESTS**. No production QML mounting, FileView, host process, real-source access, sync or native runtime certification.  
> **AUTHORITIES //** [M12l accepted architecture](../MODEL/contracts/tasks-storage-ownership-adr-m12l.md); [M12m isolated coordinator](./tasks-local-ticket-coordinator-m12m.md); [M12n native ticket observer](./tasks-native-ticket-observer-m12n.md); existing M12b production gates remain OPEN.

## IMPLEMENTATION

### Why this boundary exists

The live `services/hub/ApolloHubTodoStore.qml` exposes nine mutation methods that currently return a **boolean for successful admission of a FileView write**, not independent durable completion. Its single FileView's `onSaved` updates the in-memory task snapshot; this has historically let the four UI surfaces reconcile against the new snapshot. M12m explored a ticket-based coordinator on disposable real files. M12n observed one native synthetic M12i FileView stage in an unmounted window.

M12o now **prototypes a public ticket contract without replacing the live boolean API** or claiming native persistence certification.

### New files

- `services/hub/TaskSaveTicketContractM12o.js`: pure, QML-compatible reducer. A ticket describes exactly one recognized consumer/method, the expected **full task view** derived from the actual `ApolloHubTodoPolicy.js`, and a preserved input draft. It never reads or writes files.
- `services/hub/TaskSaveTicketFacadeM12o.qml`: **unmounted**, always-disabled QML façade exposing `submit(surface, method, draft)`, which always returns `BLOCKED / M12O_DISABLED_NO_WRITER`, plus pure preview/reconcile functions. There is no `FileView`, `Process`, socket, live store import, storage path, writable enable switch, or data mutation.
- `tests/tasks/test_task_disabled_ticket_api_m12o.cjs`: node tests using the **current production task v3 policy** in a sandbox to synthesize task/project changes and exact `TodoPolicy.view` snapshots for all four real consumer surfaces. Tests cover nine unique mutations across eleven surface/method pairs, stale/foreign receipt IDs, untrusted completion events, mismatched snapshots, error/review disposition, immutable snapshots, a disabled facade, and no real source/QML changes.
- A scoped GitHub Actions test workflow.

### Ticket rules

```text
User keeps draft in UI
      |
      v
   [ticket request] --> QUEUED --> PREPARING --> WRITING --> VERIFYING
      |                                                  |
      |                            matching verified receipt AND exact
      |                              expected confirmed task snapshot?
      |                                               /           \
      v                                             YES            NO
    BLOCKED                                          |              |
      |                                              v              v
      |                                          CONFIRMED      REVIEW_REQUIRED
      |                                              |              |
      +----> KEEP DRAFT                            CLEAR          KEEP DRAFT
```

A request being accepted for processing is never equivalent to a committed save. A completion event for **another** ticket is ignored. A claimed completion **without explicit expected test receipt classification** enters review, even if the UI happens to display the requested task. A correct receipt with an unrelated/stale task snapshot also enters review. A terminal result cannot later be silently promoted by reordered events. Invalid or rejected writes preserve the input draft.

This reducer's `SYNTHETIC_READBACK_RECEIPT` label explicitly means **test evidence only**. The future production completion source must be separately authenticated/verified according to whichever M12l architecture and reconciled M12b gates the operator eventually approves. An arbitrary caller can forge this label in pure JS, therefore it is **never** a production security check.

### Four consumers and current behavior

| Consumer | Current existing calls | M12o expected ticket reconciliation |
| --- | --- | --- |
| `widgets/hub/ApolloHubTodoMini.qml` | add, rename, done, remove | Preserve typed text, rename target and delete confirmation until the **same ticket** confirms exactly the expected view |
| `widgets/tasks/TaskDetailsPane.qml` | update details | Keep priority/description/due date draft through pending, error and review |
| `widgets/tasks/TaskPlannerSchedulePane.qml` | add undated task, update scheduling fields | Keep planner date draft / new-task text until the respective ticket's confirmed snapshot; date+creation remain two deliberate transactions |
| `widgets/tasks/TaskProjectsPane.qml` | create, rename, delete project, assign task | Preserve project rename input and destructive confirmations until matching ticket+snapshot. No early delete success |

**All four live QML files remain unchanged.** M12o tests their existing mutation names against the future-facing contract; actual QML integration requires a new approved step and cannot be inferred from these simulations.

## HOW TO USE

Run only the GitHub fixture test:

```sh
node --test tests/tasks/test_task_disabled_ticket_api_m12o.cjs
```

No additional operator setup, Fedora machine changes, Quickshell restart, local task backup, production data access, or source migration. If the QML facade is later imported accidentally, `submit()` fails closed and never reaches disk.

## VERIFY

- Nine unique write methods, eleven consumer/method combinations (Hub four, Details one, Planner two, Projects four) are exercised using the current v3 task policy. Each requires both a matching synthetic receipt and matching full `view()` snapshot to clear a draft.
- Tests show queued, preparing, writing, verifying and other-UID events **cannot** clear drafts. Missing proof, stale snapshot, rejected/blocked/recovery results keep drafts.
- Production `ApolloHubTodoStore.qml` retains exactly one `FileView`, nine `stage(TodoPolicy.*)` mutation routes, `guardedWriterEnabled: false`, and its unchanged legacy boolean semantics.
- No `shell.qml` import, no native QML execution and no production file access. CI is a code/fixture contract check, **not** a Quickshell acceptance test.

## WATCH OUT FOR

- The new `TaskSaveTicketFacadeM12o.qml` is disabled and is **not** a functioning producer. The four consumers have not been changed to call it. A green CI run must not be described as production integration.
- Pure QML/JS can correlate a receipt and snapshot but cannot **authenticate** a sender or guarantee the JSON and independent SQLite journal became an atomic transaction.
- The current UI's normalized `view()` omits persistence metadata such as a durable revision. Exact task-view equality alone is insufficient for proof of durable local storage. Production needs a separately authorized evidence source, stable revision/source identity and a non-forgeable or appropriate-trust confirmation contract.
- The reducer compares the **whole expected task view**. Concurrent independent edits or view schema changes require explicit conflict or revision-aware handling rather than automatically clearing drafts.
- The existing single-writer guard, M11t and M12b production gates, backup, rollback, native acceptance, host identity and activation are still open.
- Local machine source, mounted Quickshell state, direct real task data and live Hospital registration were not inspected or modified.

## CHECKLIST

- [x] Verify M12n merged and current one-FileView production source
- [x] Read four existing TASKS consumer surfaces and inventory methods/draft behavior
- [x] Add unmounted, hard-disabled public ticket API shell
- [x] Add test-only complete-snapshot/ticket reducer
- [x] Test nine unique operations across four consumers using actual task policy
- [x] Keep live FileView, legacy methods and real data unchanged
- [ ] CI results and final scoped diff
- [ ] Operator review/merge
- [ ] Separate native QML approval and consumer-by-consumer live integration
- [ ] Explicit decision/reconciliation of M11t/M12b production evidence and local backup
- [ ] Final production activation, only after operator acceptance

## NEXT

After M12o is merged and inspected, implement **one** consumer migration at a time behind a verified, disabled-by-default ticket producer. Start with the Hub To-Do Mini (the simplest editor), then Details, Planner, and Projects; do not cut over all four at once or silently change boolean semantics. Each cutover must preserve drafts, visibly distinguish local save pending/confirmed from future GitHub sync pending, and include a native fixture test plus rollback. Independently prove source readback and the intended acknowledgment semantics before touching real TASKS.

## DECISIONS

**Chosen for this milestone:** Test ticket ID + expected full view + separately reported synthetic completion, draft preservation, and hard-disabled real QML facade. No new process, secondary writer or cloud dependency.

**Not chosen or authorized:** Turn on a production ticket adapter, replace old boolean API, file/schema migration, create an OS-isolated broker, access task data, edit local Fedora, reload Quickshell, sync GitHub tasks, waive a security gate, or merge without operator approval.

**Acceptance:** Source and CI evidence only until operator accepts. No verified live Hospital session or native M12o runtime acceptance.
