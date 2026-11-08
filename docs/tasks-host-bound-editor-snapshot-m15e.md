# 🏥 TASKS M15e // one-editor snapshot boundary, host integration blocked

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** TASKS opt-in encrypted draft recovery (external compatible continuity, no live Room verified)  
**ASSIGNMENT:** Prove the single-editor capture transaction ordering and required Connections scopes while preserving current production default-deny boundary.  
**STAFF ROLE:** DOC-compatible external worker; live Hospital staffing/lease not verified.  
**PERMISSIONS:** Operator-requested bounded GitHub TASKS-owned test/CI/docs. No Connections host edit, actual user draft read, live desktop write/reload, credential activation, production IPC, saved TASKS writer change or merge authorization for this new risk boundary.

## IMPLEMENTATION

The *actual* M15d UI picks one of `entry` (NEW TASK / RENAME) or `details` (TASK DETAILS), but only forwards status booleans. In the live editors, the unsaved text remains in `ApolloHubTodoMini.qml`'s `entryInput.text` and `TaskDetailsPane.qml`'s description/priority/due-date drafts; the one persisted TASKS source remains `ApolloHubTodoStore.qml` and its single FileView writer. M15d's ephemeral selector is **not a task identity, source revision, authenticated caller, consent record or credential**.

This M15e slice adds `tests/tasks/fixtures/TaskEditorSnapshotHostM15e.cjs`, a disposable-only transaction that **reads synthetic editor content** only after a separate test-host approval. The test owner, not UI state, holds its own ephemeral HMAC key. A request binds exactly one editor target, selected editor identity and edit epoch, independent committed-source bytes/owner epoch/generation/digest, one capture scope and a 30-second expiry. The host consumes the approved request *before* invoking the editor callback; it rechecks source and editor state on both sides of the read and refuses wrong target, stale/changed source, stale edit, pending save, revocation, replay, wrong scope, malformed packet or encryption failure. Its response never includes plaintext, source hash, editor ID, ciphertext or key. The synthetic encryption callback reuses M13m's existing source-bound AES-256-GCM checkpoint model; no new cipher, storage, or TASKS writer is added. It does not claim real authenticated authority even when synthetic encryption succeeds.

Production TASKS/Connections QML are **not imported, modified, mounted or activated** by this fixture. The fake operator and its HMAC are in-process test capabilities only, not a real host's attestation. A test fixture's ability to read fake drafts MUST NOT be treated as permission to read user drafts.

## HOW TO USE

No desktop action or new button. The existing UI still provides **TASKS → SYNC → RECOVERY → CAPTURE → CHOOSE UNSAVED EDITOR**, but **SAVE ENCRYPTED DRAFT remains disabled**. M15e's tests run only in GitHub Actions via `node --test tests/tasks/test_task_editor_snapshot_host_m15e.cjs` and are not a real capture/restore workflow.

## VERIFY

The M15e suite validates no pre-approval editor reads, no wrong-target reads, single consumption, source/file generation conflict, editor target/epoch changes, inflight saves, revocation, expiry, malformed request, during-read mutation, no plain output, and source-bound synthetic encryption through the existing M13m model. Re-run M15d, M15c, M13p, M13t, M13m, M11d and C2a regressions. Native Fedora/Wayland, actual D-Bus host authentication, real owner/source receipt and real Secret Service key-release are **not verified** by test-only code.

## WATCH OUT FOR

The shared `ConnectionsBroker` has `credentialActionsEnabled: false`; `ConnectionsRequestStatus` has no registered authenticated production host. Same-UID processes may impersonate each other's labels or directly replace a desktop-owned TASKS file. A boolean or in-process HMAC under a fake host does not solve that boundary. Do not transport real draft plaintext through QML UI status fields, stdout, environment variables, logs, unverified processes or a UI-supplied `approved` flag. Do not release a key before host authentication and independent consent. The test fixture leaves no live draft or checkpoint.

## CHECKLIST

- [x] Verify #1459/#1454 merged and inspect Syntagma Hospital rules
- [x] Reconstruct single saved writer, M15d UI, existing synthetic crypto and shared Connections status
- [x] Implement disposable one-editor source/identity/replay snapshot transaction
- [x] Reuse existing M13m source-bound synthetic encryption
- [x] Add denial regression tests and CI
- [ ] Exact-head GitHub CI and PR review
- [ ] Connections owner supplies verified host identity, three separately scoped authorizations and trusted source receipts
- [ ] Mount real editor snapshot adapter only behind that host with approved IPC and memory handling
- [ ] Real encrypted draft persistence, restart/unlock preview and explicit clear
- [ ] Operator Fedora desktop acceptance

## NEXT

**Connections owner:** define and implement an authenticated transport/consent and key-release service with *separate* `tasks.draft.capture.encrypted`, `tasks.draft.preview.unlocked`, and `tasks.draft.clear.encrypted` grants, including caller attestation, fresh source-owner revision receipts, revocation/expiry and single-use operation binding. **TASKS owner:** after host evidence exists, implement a true per-editor snapshot adapter that reads the selected live editor only when the host requests it, tests race/staleness through the actual QML lifecycle, and submits the payload directly for host encryption. Never import the disposable fake-host grant into production or treat `FileView.onSaved` as durable verification.

## DECISIONS

No duplicate database, second source writer, task auto-save, auto-replay, provider-account permission widening, production credential/grant flags, new UI or local machine changes. This PR is an **M15e gated transaction prototype**, not completed authenticated capture. Operator retains final review and deployment authority; the shared Connections owner retains its host boundary.
