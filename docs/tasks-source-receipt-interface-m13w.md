# 🏥💜 TASKS // M13w Disabled Source-Receipt Interface

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS opt-in encrypted recovery / source-owner receipt handoff  
**STAFF ROLE //** DOC, external Hospital-compatible worker, provider OPEN AI // CHATGPT; no verified live Hospital registration  
**BASE //** main `4b3c5d37494d685f0fac6558dea7c0db12ba643e` (November 6, 2026; recheck on continuation)  
**SCOPE / PERMISSIONS //** GitHub-only additive unmounted QML interface, pure JS policy, test, CI and handoff. No live TASKS saved-source file, OS keyring, workstation action, production activation, Connections host change or automatic PR merge.

## IMPLEMENTATION

M13v #1358 is merged. It verifies a *synthetic* stage using the existing M12h SQLite ledger, M13u revision chain and independent readback, but explicitly returns `SYNTHETIC_RECEIPT_OBSERVED_UI_UNACKNOWLEDGED`. The accepted M12l architecture still preserves one application-owned local storage authority, not a mandatory privileged TASKS broker. Concurrent Connections work owns SELinux packaging/real operator authorization and remains separate.

**M13w introduces a disabled, production-shaped interface boundary:**

- `services/hub/TaskSourceReceiptFacadeM13w.qml`: an unmounted Quickshell `Scope` with immutable `enabled:false`, `productionWriterAuthorized:false`, `sourceOwnerAuthenticated:false`, `nativeCallbackAuthenticated:false`, `durableReceiptAuthenticated:false`, `consentAuthenticated:false`, `draftRecoveryEnabled:false`. Its `submit()` always refuses with `M13W_DISABLED_NO_WRITER`. It owns no `FileView`, `Process`, source path, network client or Secret Service interface.
- `services/hub/TaskSourceReceiptReviewPolicyM13w.js`: pure QML-compatible, **negative-only** projection of existing M12o ticket shapes and M13v synthetic source evidence. It handles all exact M12o HUB/DETAILS/PLANNER/PROJECTS routes and accepts only a strict test receipt shape with literal false authorization flags, matching expected ticket ID, stage ID, owner epoch, baseline→next revision, source SHA-256 and complete expected M12o UI snapshot. Even if all test evidence matches, the only result is **`SOURCE_MATCHED_SYNTHETIC_ONLY`, `NEEDS_TRUSTED_OWNER`, `KEEP_DRAFT`, `userSaveAcknowledged:false`**. A fake caller cannot authorize anything by setting `approvedByUser`, `hostAuthenticated`, `sourceTrusted`, `keyReleaseAuthorized`, or a synthetic receipt boolean.
- `tests/tasks/test_task_source_receipt_interface_m13w.cjs`: evaluates M12o and the new policy through isolated Node JS contexts, tests all four surfaces, untrusted native hints, missing evidence, forged approvals, stale epochs/revisions, wrong source hashes, snapshot mismatch and terminal claims. It checks no user draft content/expected items are ever returned by the review projection and that the production single TASKS writer is unchanged.
- `.github/workflows/tasks-source-receipt-interface-m13w.yml`: Node tests, syntax-only `qmlformat`, M12o/M12p/M13v/M13u/M11d and C2a security regression guards. This is a GitHub test, not an installed service.

This is deliberately a **new disabled API seam, not activation**. It prevents the next native integration from accidentally promoting a byte-consistent fixture receipt into a real save ACK that clears the user's unsaved draft. It does not add UI controls or change the accepted CPU++ Connections layout.

## HOW TO USE

No desktop action required. GitHub Actions runs:

```sh
node --test tests/tasks/test_task_source_receipt_interface_m13w.cjs
```

Existing visible routes remain TASKS → SYNC → RECOVERY (read-only unsaved editor presence) and CPU++ → SETTINGS → CONNECTIONS → TASKS (read-only keyring/host status). Neither new file is imported into the production singleton or shell.

## VERIFY

- Every M12o route across HUB/DETAILS/PLANNER/PROJECTS is supported in the pure review contract.
- A callback `FILE_SAVED` alone, fake `CONFIRMED` event, unauthenticated M13v-shaped receipt or self-asserted approval cannot clear a draft.
- A fully matching **synthetic** source observation still preserves the draft and last confirmed snapshot, with no real local-save acknowledgment.
- A stale ticket, wrong stage/epoch/revision/hash, incomplete receipt, extra unexpected field, alternate snapshot or missing approval evidence never becomes a grant.
- Tests verify literal false QML activation flags and only the existing singleton's one `FileView` and `todoFile.setText()`.
- The policy returns no task title, source hash, draft body, key, credential, synthetic receipt payload or production authority.
- Existing M12o/M12p/M13v/M13u/M11d/C2a regressions run in CI.

**Evidence limit:** Matching synthetic event fields is data comparison, **not** cryptographic or OS authentication. The expected source pin and snapshot arrive as ordinary test inputs; they could be forged by a caller. The result therefore **never acknowledges a real save**. There is no real task-data persistence, crash-durable acknowledgment, native Quickshell proof, source fencing against hostile same-UID writers, or protected Connections consent. This interface is not mounted in the running desktop and creates no new user-visible feature.

## WATCH OUT FOR

Do not connect a QML-provided `sourceTrusted` or `approvedByUser` boolean to draft deletion. A production source receipt must be issued by an independently verified source owner with a monotonic durable committed revision and compare-and-commit protection at actual consumption. Distinguish a saved-file callback, SQLite stage settlement, source revision observation, UI snapshot consistency, real user save ACK, and protected credential consent. They are **different proof levels**.

Before enabling any writer or draft recovery, coordinate source custody with TASKS and authenticated approval/key release with the Connections owner, and test ambiguous save/restart behavior on real Quickshell only in a separately authorized isolated environment.

## CHECKLIST

- [x] Verify M13v merged, canonical Syntagma rules, main HEAD and open TASKS ownership
- [x] Reuse existing M12o ticket shapes and M13v synthetic source receipt
- [x] Add never-mounted disabled QML facade and negative-only source receipt policy
- [x] Test draft retention and no-key-release/no-writer invariants across four consumers
- [x] Add targeted CI and ownership handoff
- [ ] Final PR-head GitHub CI and independent security review
- [ ] Operator merge decision and final acceptance
- [ ] Independently verified source-owner native integration and durable first-create contract
- [ ] Connections caller/operator authentication and three separate M13p scopes
- [ ] Real encrypted draft capture, independent preview/delete and reboot acceptance

## NEXT

Do not promote M13w's matching *synthetic* receipt into a success path. The next milestone should prove an actual independent authority for the existing TASKS source, then design an isolated native Quickshell admission/readback test that can distinguish authentic source owner ACK from a spoofed callback. Only after protected source custody, independently authenticated Connections consent and native acceptance can a production coordinator permit a draft to be cleared. Preserve the accepted single `ApolloHubTodoStore.qml` FileView until a separate approved migration.

## DECISIONS

No production `ApolloHubTodoStore.qml`, `shell.qml`, widget, shared Connections, local Fedora, credential, source JSON, keyring or real draft modification. No automatic replay, additional writer, privileged broker, runtime activation or PR auto-merge. All future host and source authority decisions remain subject to the operator.
