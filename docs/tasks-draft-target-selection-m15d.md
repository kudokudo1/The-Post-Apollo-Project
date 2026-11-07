# 🏥💜 TASKS M15d // Explicit Draft-Editor Target, Before Encryption

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS opt-in encrypted draft recovery  
**ASSIGNMENT //** Select exactly one actual unsaved TASKS editor target using status-only live signals, without transferring plaintext before trusted host authorization  
**STAFF ROLE //** DOC / external Hospital-compatible OPEN AI // CHATGPT. No verified live Hospital registration.  
**CHECKPOINT //** M15c PR #1454 merged into `main` at `b73a5745dc715b532e03fa2299026926408ab714`. Branch created from that exact commit on November 7, 2026.  
**SCOPE/PERMISSIONS //** GitHub-only TASKS-owned QML, pure JS, tests, CI and documentation. Operator granted standing permission to merge verified TASKS work. No Fedora modifications, production activation, new TASKS file writer, Connections broker edit, actual key release, credential action, real draft capture or automatic replay. Independent Nurse 2 review waived by operator in this assignment.

## IMPLEMENTATION

### Mechanism first

A saved task and an unfinished editor draft are different things. The saved source lives in `ApolloHubTodoStore.qml` and has one `FileView`/one `todoFile.setText()` writer. Unfinished edits exist inside existing Quickshell editors: `ApolloHubTodoMini.qml` for NEW TASK/RENAME and `TaskDetailsPane.qml` for DETAILS. They currently report dirty/pending *booleans* through `TasksW.qml`, `TaskSyncConnectionsPane.qml`, and M13s on the RECOVERY screen.

M15c introduced three disabled recovery action modes and explained which permissions are missing. It does not know **which** unsaved editor the future encryption host should capture, especially when two editors are dirty or a write is in flight.

### M15d files

- **`widgets/tasks/TaskDraftTargetPolicyM15d.js`**: A finite, pure policy accepting *exactly* M13s's existing five fields: `entryDirty`, `detailsDirty`, `entrySavePending`, `detailsSavePending`, `sourceState`. It allows only `none`, `entry`, `details` selections. It refuses malformed/extra data, requires explicit operator choice for either dirty editor, refuses selecting during any save or when source is loading/error/unsupported, identifies when both editors are dirty, and invalidates a selected editor once it becomes clean. It never treats a FileView callback as a verified source revision.
- **`widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml`**: Reuses existing `ModeButton` grammar inside the CAPTURE mode to show **NONE / NEW / RENAME / DETAILS** selection choices and a dynamic status/explanation. No text, ID, key, hash, credential, file or source path enters the component. Selection only updates an in-memory enum and invalidates the previous requirements review. The existing SAVE ENCRYPTED DRAFT button stays disabled.
- **`widgets/tasks/TaskRecoveryStatusPaneM13q.qml`**: Passes through the *same pre-existing* `editorSignals` metadata to the new target chooser. It does not call `ConnectionsBroker.requirement()`/`authorize()`; M13q's status-only broker boundary remains unchanged.
- **`tests/tasks/test_task_draft_target_selection_m15d.cjs`**: Checks exact schema and no plaintext echo, both dirty / single dirty / no dirty, invalid source, pending save, stale selection, default-off authority, correct QML path and unchanged single writer / C2 broker.
- **`TaskDraftTargetSmokeM15d.qml`**, **`.github/workflows/tasks-draft-target-selection-m15d.yml`**: A disposable real Quickshell 0.3.2 Xvfb test, which exercises both editors dirty, choosing each explicitly, refusing pending saves, and invalidating a now-clean selection. Separate GitHub jobs rerun the predecessor M15c, M13s, M13q, M13z, M14a, M15a, C2a and M11d regressions.

**This adds no ciphertext storage and does not claim crash recovery works yet.** M15b's tested encrypted-file/keyring persistence remains disposable-CI-only; the shared Connections broker still denies production credentials and key release. The important new contract is: **an operator must name exactly one dirty editor, and no draft plaintext may cross into RECOVERY just to make that choice.**

## HOW TO USE

After a verified merge and a separately approved deployment, open **TASKS → SYNC → RECOVERY → CAPTURE**. The section **CHOOSE UNSAVED EDITOR** shows the live status of NEW TASK/RENAME and DETAILS without showing any private content. Select the desired target. If neither editor is dirty, a save is pending, or the source is not ready, the interface refuses selection.

The protected **SAVE ENCRYPTED DRAFT** control remains disabled until actual host-scoped consent and key authorization exist. Selecting a target does **not** store a backup.

## VERIFY

- The source policy validates only exact boolean/enum metadata and finite supported source states. No task title, description, ID or key material is constructed or transported.
- With two simultaneous dirty editors, a target is never chosen automatically.
- Save-in-progress and uncertain source state forbid selectable targets.
- A previously selected target becomes stale if its editor is no longer dirty.
- All status outputs explicitly deny encryption, capture, key release, source writing, checkpoint creation, preview and draft clearing.
- The production store remains **one FileView / one setText**. Shared CPU++ Connections remains `credentialActionsEnabled:false`.
- Quickshell CI uses private Xvfb and synthetic **booleans only**. It does not launch the production desktop or inspect real user data.

**Exact-head CI verification:** pending. Final PR merge, CI status, and local Fedora visual acceptance must be independently checked.

## WATCH OUT FOR

The existing five M13s signals are not a durable proof of the specific task identity or saved source revision. In particular, the *DETAILS* editor's underlying selected task could change while its dirty boolean remains true, so a later trusted host must establish a fresh in-editor snapshot identity and source conflict guard at capture time. This UI choice is an ephemeral hint, not a capability token, consent receipt or authorized selector for real plaintext.

**Dependency:** A trusted, revocable, authenticated scoped key-release host is owned by the shared Connections subsystem. TASKS must not bypass that owner by interpreting the selected enum or an OS keyring presence check as authority. The M13p scopes remain separate for capture, unlock/preview and ciphertext deletion.

The operator's merge authorization does not authorize Fedora installation, desktop reloads, plaintext draft persistence, source file modification or production key-release activation. This code does none of those.

## CHECKLIST

- [x] Recheck current main/PR ownership and Syntagma protocol
- [x] Preserve both existing editors, one saved-source writer and M13q passive broker contract
- [x] Add explicit in-memory editor target selection using only five existing metadata signals
- [x] Preserve draft retention and fail-closed behavior in ambiguous/pending/stale cases
- [x] Add strict unit/production-inventory tests and real native QML CI
- [ ] Exact-head CI; address failures without changing production protections
- [ ] Merge after green CI under operator's standing authorization
- [ ] Separate approved Fedora native acceptance
- [ ] Trusted Connections host + real opt-in key release
- [ ] Actual encrypted editor draft capture, restart unlock/preview, source conflict and clear

## NEXT // M15e

Build the **host-authenticated editor snapshot boundary**, not another status dashboard. When the Connections owner supplies a revocable, scoped real capture grant, the host must request one fresh identity-bound editor snapshot and validate both the source revision and selected editor identity before accepting a plaintext payload for immediate encryption. Never use this M15d boolean-only choice as an authorization secret or evidence of durable save. The decrypted candidate must remain preview-only until separately confirmed.

## DECISIONS

No new production plaintext channel, no unsafe UI-side key release, no alternate TASKS source writer, no additional FileView, no network sync, no automatic draft deletion or replay, no local Fedora modifications. Merge authorization is available for a CI-clean bounded PR; user retains final acceptance of the deployed UX. Nurse 2 review waived.
