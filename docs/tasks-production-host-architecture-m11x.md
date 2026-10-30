# 🏥💜 TASKS M11x // Production Host Architecture Decision Record

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Room / assignment:** TASKS JSON writer continuity, Proxy 1 → Proxy 2 successor review  
**Worker:** External Hospital-compatible ChatGPT doctor, **not** a live Hospital-registered worker  
**Inspected base:** `main` `d348991eeb5895cd260d0bf06971784eae00f1ee` (2026-10-30); recheck before any later implementation  
**Classification:** **PROPOSED ARCHITECTURE ONLY**. This document does not install or authorize a production host, writer gate, backup job, local runtime change, restoration, or migration.

## IMPLEMENTATION

This design extends [M11k](./tasks-production-writer-gate-m11k.md) and [M11t](./tasks-production-trust-and-rollback-m11t.md) after M11u, M11v and M11w exercised *synthetic* script capture, Linux process observation and disposable journal owner continuity. Those tests are valuable **mechanism evidence** but are not an independently trusted production distribution channel or real-file safety proof.

### Current implementation audit

- `services/hub/ApolloHubTodoStore.qml` remains the only active TASKS writer. `guardedWriterEnabled` is a **readonly literal false**, and one `FileView` with `atomicWrites: true` writes `Quickshell.dataDir + "/apollo-hub-todo-v1.json"`. Nine mutations all invoke synchronous `stage(result)`, which returns `true` when it calls `todoFile.setText`, **not** after OS-host verification or durable settlement.
- Existing `onSaved` publishes `pendingDocument` directly. No production OS host is consulted. The existing off mode is legacy, **not OS-fenced**, and no future disabled gate may be described as live protection.
- `TodoPolicy.view(storageState, document, errorCode)` recognizes exactly six states: `loading`, `saving`, `ready`, `empty`, `error`, `unsupported`. `writable` is true only for ready/empty. Under error/unsupported (and loading), the public view uses **an empty snapshot**, even though the store may still retain `document`. Guarded recovery must not silently erase its last confirmed task list from the operator's view.
- Existing mutation callers are `ApolloHubTodoMini.qml` (add/rename/done/delete), `TaskDetailsPane.qml` (details), `TaskPlannerSchedulePane.qml` (add/details) and `TaskProjectsPane.qml` (create/rename/delete/assign project). They treat a returned `false` as rejection and wait for changed snapshots to confirm the action. TODAY and Planner's general view are read-only consumers. Schedule's task creation is **one undated save**, with due date applied only by a later explicit operation.

### Proposed component boundaries, NOT implementation approval

| Domain owner | Proposed responsibility | Explicitly excluded |
| --- | --- | --- |
| Trusted deployment manager (to be separately chosen) | Supply independently approved host/interpreter binary identifiers, owner-controlled immutable or authenticated payload and rollback mapping | Asking the untrusted child or mutable same-user directory to attest itself |
| New production-specific OS host (later patch) | Lock lifetime, actual-source preflight and backup, immutable stage IDs, one durable owner journal, verify exact file bytes, settle or freeze, durable recovery review | Widening M11l/M11m private fixture path filters, SQLite task-data migration, task mutation logic duplicated from policy |
| Existing TASKS singleton `stage(result)` (later patch) | Remain **sole FileView writer**; serialize one proposal, await host reservation before `setText`; accept settlement before publishing; maintain last confirmed task document | A second FileView, parallel legacy fallback, QML self-issuing OS authority, hidden real-data reset |
| Existing `TodoPolicy` and UI consumers (later reviewed patch) | Explicitly reflect pending/confirmed/error state and preserve user drafts and last confirmed content through review | Mapping recovery or ambiguous data to an empty **writable** task list |
| Operator-controlled recovery procedure | Quiesce both save paths, compare source with independently read back backup and journal, decide data recovery separately from code rollback | Automatically restoring older JSON over newer tasks |

#### 1. Independently trusted executable/source chain

**Architecture decision pending:** define a root/admin-controlled or signed deployment artifact for the production host + interpreter + supporting code and record the exact verified build/hash/owner/mode before activating. A runtime test that hashes its *own* interpreter or trusts a hash packaged beside a same-user-editable script cannot provide independent provenance. Future proof must cover symlink/ancestor replacement, executable and module load races, launch environment, privileges, and how immutable code revisions are identified after an update. Linux `pidfd` + `/proc/PID/exe` and sealed memfd are correlation and pathname-pinning mechanisms, **not** an all-purpose tamper-proof attestation of a hostile same-user runtime or OS. Resolve threat model and deployment owner **before** selecting the concrete launcher. No current CI result closes M11t's `TRUST_EXEC` gate.

#### 2. Source and backup contract (one actual JSON writer)

Preflight for a separately authorized **real** source must independently check canonical path, owner/permissions, no unexpected symlink or hardlink, source inode/content/size and v1/v2/v3 policy parity. An independently rereadable, byte-for-byte backup and a dedicated journal must be created before a guarded write is admitted. Define exactly when the backup is taken, immutable retention and operator rollback references; never make the backup the default new live file. Existing `FileView` with atomic rename may change inode after saving, so the host must compare **expected stage content** and explicitly allowed replace semantics, not assume a stable target inode across every valid write. Also check conflicting external modifications because advisory `flock` alone cannot fence noncooperating writers. A missing/damaged source or journal means **review required**, never empty writable state.

#### 3. Stage/callback/settlement contract

Proposed sequence for a separate **disabled-by-default** prototype:

1. One of the nine existing wrappers computes a validated candidate using current `TodoPolicy`. Preserve its ID/confirmation semantics. Do not clear drafts or publish it yet.
2. `stage(result)` maintains one in-flight admission slot; the OS host must first persist stage ID, expected candidate bytes/hash, baseline source digest, owner epoch and current session. No reservation, **no `FileView.setText`**.
3. Only an exact matching reservation permits the existing single `FileView.setText` to run, while UI remains pending/nonwritable.
4. `onSaved` is notification, **not** confirmation. Defer `FileView.reload()` with `Qt.callLater` and fence against process/session generation, epoch, stage and file identity, including `onLoaded`, `onLoadFailed`, `onSaveFailed` and `reloadFromDisk()`.
5. The host independently reads the actual source and durably settles the exact stage. Only an exact, current, verified settlement allows `pendingDocument` to replace confirmed `document` and public views to show success. Conflicting, missing, late, duplicate or ambiguous signals enter nonwritable recovery, retaining old confirmed document and any in-progress UI draft.
6. Freeze first closes admission durably, drains only known accepted work; uncertain shutdown or fresh-owner restart enters `RECOVERY_REVIEW`, including when a commit was settled but QML never received acknowledgment. Do **not** replay a previous stage automatically.

**Unresolved integration detail:** native `FileView` callbacks do not themselves carry a durable stage ID. A session-generation guard alone cannot prove which physical save emitted a late callback. The later patch must explicitly prove non-ambiguity under callback reorder/duplication or fail closed; never infer confirmation from a convenient timing window.

#### 4. UI and Boolean return contract: a required decision, not an assumption

Current `stage()` returns synchronous Boolean: **request sent to FileView** vs rejected. Its callers assume `false` is immediate rejection, and infer durable success only after observing a matching snapshot. A host reservation is asynchronous. Two viable interfaces require review:

- **Option A (least UI churn, provisional preference):** keep the Boolean method signatures; `true` means **validated request queued for reservation**, not saved. Preserve `saving` / nonwritable snapshot until host settlement; add independent internal phase and a fenced completion token. UI reconciliation must use current stage identity or a trustworthy state transition, not merely matching content. A valid later refusal must explicitly end pending state with retained draft and visible error.
- **Option B (larger API):** return a structured request ticket and emit completion/refusal events, updating the four mutation callers and any relevant shared consumers. More explicit, but wider shared UI churn and increased collision risk.

**Neither is authorized as canonical.** Option A has a particularly important failure: `true` can be returned *before durable reservation*. Therefore it must be clearly **queued**, not an admission or success receipt. A race in which a second mutation is accepted before reserved stage completion must be denied. Long pending/recovery needs an operator-visible nonwritable state.

For either option, there must be **no success** until settlement and no loss of user drafts. The existing public view's empty-on-error behavior cannot be reused unmodified for a guarded recovery view because it would hide all last-confirmed items. Define a separate read-only last-confirmed snapshot contract or an explicitly reviewed `TodoPolicy.view()` change before runtime integration. Preserve its existing six public state strings unless *all* consumers and policy tests are separately revised.

| Consumer | Existing behavior | Required future guarded check |
| --- | --- | --- |
| `ApolloHubTodoMini` | Holds text while pending; reconciles on snapshot | No premature clearing or optimistic done/delete; reject/timeout retains text and confirmation |
| `TaskDetailsPane` | Waits for saved matching priority/description/date | Match request identity, not merely identical data; preserve draft and selected task in review |
| `TaskPlannerSchedulePane` | Undated create, then explicit separate date save | No auto-second stage or claim of atomic create+schedule; preserve scheduling draft |
| `TaskProjectsPane` | One `pendingKind` and matching project snapshot | Exactly-once completion/refusal, preserve current selection and rename/assign/delete confirmation |
| TODAY / Planner / Hub summaries | Observe shared singleton snapshot | Never render empty confirmed tasks merely because guarded review is pending |

#### 5. Failure and rollback acceptance (must be proved before activation)

Required test families: wrong executable trust anchor, untrusted process, changed source while backing up, backup readback mismatch, concurrent uncooperative editor, two lock contenders, stale/duplicate stage, `onSaved` before reserve, delayed `onLoaded`, save failure, readback mismatch, crash after reserve/save/readback/settlement, freeze during save, restart with same vs new session, interrupted rollback, changed code with unchanged task data, and deliberate **data restoration** requiring separate operator approval.

A rollback must quiesce both potential writers before restoring **code/config** only, preserving live source bytes, journal and backups. If their state conflicts, stop and present the three hashes/versions to operator for reconciliation rather than silently overwriting data. Retain a canonical prechange revision and verified recovery pointer. No `git reset` of a dirty live Quickshell checkout, no automatic restart, no SQLite dual writer or hidden migration.

### Proposed deliverable division for future independent assignments

- **M11y (proposal only):** independently pinned production-launcher trust model, threat model and synthetic reproducible negative tests; **no actual tasks or guarded store patch**.
- **M11z (proposal only):** synthetic production-shaped source/backup/rollback preflight, exact UI return/snapshot compatibility tests; keep guard off.
- **Separate later implementation:** operator-approved host, singleton patch and native acceptance with independent review, followed by **a different** explicit activation decision. These proposed names are organizational placeholders, not new authorized Assignments or Hospital Rooms.

## HOW TO USE

No TASKS control or system setting changes in M11x. The document is a review artifact. In a separate repository checkout or GitHub Actions, run:

```sh
python3 tests/tasks/test_task_production_architecture_m11x.py
```

No command is required on the operator's Fedora machine and no task source/backup is read.

## VERIFY

- Current GitHub `main` source inspection confirmed one `FileView`, nine synchronous task/project mutation wrappers and hard-coded `guardedWriterEnabled: false`.
- The actual caller sources confirm each uses a synchronous Boolean return and reconciles via `todoSnapshot`; current Planner schedule creation intentionally takes two separate actions.
- M11u/M11v/M11w were synthetic trust/process/journal tests, not a production host; M11s native fault observations used private synthetic copies.
- M11x adds only a proposal doc, machine-readable decision manifest, **read-only source/contract check** and a CI workflow. A green check means source/doc consistency only, not deployment safety.
- Reference source baseline is historical. Recheck `main`, branch ownership and live-worktree differences before any subsequent patch.

## WATCH OUT FOR

- The existing UI can display an empty view on error while retaining `todo.document`; this is an actual public-snapshot hazard for protected recovery.
- `true` from current `stage(result)` is not a durable success proof. A new async host cannot simply preserve that assumption unchanged.
- Immutable/sealed script bytes and a PIN/nonce don't establish the trustworthiness of the interpreter, OS, caller or independent key supply.
- A dangerous but tempting shortcut is changing M11l/M11m fixture path validation to the real task file. **Do not do this.**
- No operator live data, local checkout, Quickshell runtime, sqlite task store, GitHub Projects task data or Hospital registration has been touched.

## CHECKLIST

- [x] Recheck M11w merged to main, current single writer and PR collisions
- [x] Inventory real UI mutation callers and their synchronous return semantics
- [x] Write production trust/backup/source/callback/recovery boundary review
- [x] Document nonwritable last-confirmed snapshot hazard and explicit UI options
- [x] Add source-only automated no-activation review and CI
- [ ] CI passes, independent review and operator acceptance
- [ ] Operator selects actual launcher trust anchor and UI return contract
- [ ] Separately authorize any real-source host, singleton code patch, merge, local test, activation or SQLite migration

## NEXT

Review the draft PR and its CI. Choose the precise **future** trust anchor and UI return policy. Only after a separate scope/authorization should a new production-shaped, disabled-only test host be implemented. Local machine modifications and production activation remain separately gated.

## DECISIONS

**Verified:** Prior M11w disposable journal mechanics merged, existing production singleton still uses a legacy unfenced JSON `FileView`, one `stage(result)` and nine Boolean-return wrappers. Current public error/recovery UI semantics are insufficient for guarded last-confirmed visibility.

**Proposed, not accepted:** Specific host trust/deployment mechanism, Option A vs Option B for UI, staged milestone division, source backup and rollback protocol.

**Not authorized:** Production host, real task-file inspection, singleton integration, local computer changes, PR merge, activation, SQLite task-data migration, data restoration or live Hospital registration.
