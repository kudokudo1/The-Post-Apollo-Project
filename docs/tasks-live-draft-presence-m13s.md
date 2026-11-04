# 🏥💜 TASKS // M13s Live Unsaved-Draft Presence Boundary

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS opt-in encrypted recovery, currently status-only  
**ASSIGNMENT //** Connect real in-memory draft presence to existing TASKS Recovery view without releasing, copying, saving, encrypting or exposing draft content  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible; live registration unverified  
**BASE //** GitHub `main` at `505694763b353d9020c7f7facf09b725ed22936d`, November 4, 2026  
**PERMISSIONS //** Bounded GitHub branch/test/PR, no user workstation/local Quickshell mutation, runtime activation, keyring operations, source writer changes or automatic PR merge.

## IMPLEMENTATION

### Verified boundary

- CPU++ Connections TASKS field PR #1271 merged; user visually accepted the standard list/details layout. This milestone does **not** change that accepted CPU++ layout.
- Shared `ConnectionsBroker` remains a read-only Secret Service **presence** probe, not an authenticated key-release broker. `credentialActionsEnabled` is literal false.
- Actual TASKS source: `services/hub/ApolloHubTodoStore.qml`, exactly one `FileView` and one `todoFile.setText()`. Source snapshots do not provide a trusted durable revision or independent source-owner attestation. Encrypted recovery flags remain false.
- Actual editor seams: `widgets/hub/ApolloHubTodoMini.qml` holds the new task/rename input and `pendingWriteKind`; `widgets/tasks/TaskDetailsPane.qml` already exposes `dirty` and `pendingWrite`. `widgets/TasksW.qml` owns both instances and mounts `TaskSyncConnectionsPane.qml` with `TaskRecoveryStatusPaneM13q.qml`.
- GitHub preflight found no open TASKS or Connections implementation PRs. Syntagma `AGENTS.md` and relevant Hospital authority rules were inspected.

### Added status-only live seam

1. `ApolloHubTodoMini.qml` now exposes a **read-only boolean** `unsavedLocalEntryDraft`, computed from its existing input. The property is true when there is unsaved new-task text or when a rename input differs from its current saved task title; missing rename target with text is conservatively treated as an unsaved draft. It does **not** expose title, task ID, full text, or copied draft values. The existing Hub tile inherits only this read-only property, with no behavior change.
2. `TasksW.qml` creates an `editorSignals` object of **four booleans plus one source-status string**, and passes it to the existing SYNC Connections pane. The booleans are new-task/rename dirty, task-details dirty, entry write pending, and details write pending. `sourceState` comes from existing `ApolloHubTodoStore.storageState`. No task identity, content or credentials are included.
3. `TaskSyncConnectionsPane.qml` forwards those status-only fields to its existing RECOVERY submode; the other four Git and local mapping tabs are unchanged.
4. `TaskDraftPresencePolicyM13s.js` maps only known boolean/enum values into safe labels: `UNSAVED EDITOR CHANGE // OBSERVED`, `EDITOR SAVE // PENDING / NOT CONFIRMED`, `NO UNSAVED CHANGES IN MONITORED EDITORS`, or `EDITOR STATUS // NOT VERIFIED`. Unknown source text cannot appear raw in the UI. The model explicitly says **only NEW TASK / RENAME and TASK DETAILS are monitored** and PROJECT/PLANNER editors are not yet inspected. A source state of `ready` is never labeled a verified revision.
5. `TaskRecoveryStatusPaneM13q.qml` gains a read-only **LOCAL EDITORS // UNSAVED CONTENT STATUS** section between the existing shared keyring check and disabled-recovery permissions, using the same Gohu, cyan and orange style. It does not receive plaintext, enable recovery, create a FileView or Process, or call a saved-task mutation API.
6. `tests/tasks/test_task_live_draft_presence_m13s.cjs` exercises clean/dirty/pending/unknown source labels, no false durable source claim, QML binding strictness, no plaintext data propagation, existing single writer and no new OS/storage/host operations.

### Why this before real opt-in

The next protected operation needs to know which unsaved editor it is capturing, when a save is pending and whether the authoritative saved source is current. This patch establishes **visibility of the real editor state**, without treating an in-memory boolean or current `storageState` as a trusted revision, authenticated consent or durable checkpoint.

The future host must still establish explicit feature opt-in, scoped OS-key release, encrypted 0600/0700 private checkpoint transactions, retention and an independently verified saved-source anchor. A real restore must always preview in the existing editor and preserve the one writer.

## HOW TO USE

No action on the running desktop. After independent PR review/merge and separately authorized installation, open **TASKS → SYNC → RECOVERY**. The new section will report whether the **New Task / Rename** or **Task Details** editor currently has unsaved edits, and whether a save remains unconfirmed.

The already accepted **CPU++ → SETTINGS → CONNECTIONS → TASKS** field stays in its original layout and continues to report keyring/permission presence only. M13s does not create an opt-in toggle, keyring credential, encrypted recovery checkpoint or new reader of saved task bodies.

## VERIFY

- QML syntax for the five altered/mounted components and static signal wiring.
- Node tests for no-draft, observed dirty editor, pending save, unknown data and sanitized source states.
- Existing M13q Recovery/UI tests, M11d one-authoritative-writer guard, TASKS chassis/details UI checks and C2 broker read-only contract.
- No mutation, source writer, new key provider, `Process`, `FileView`, `secret-tool`, raw text propagation or auto-recovery.
- GitHub source/CI acceptance is **not** real Fedora render, click or crash/restart recovery. Real native desktop visual acceptance requires operator-approved local deployment.

## WATCH OUT FOR

- **Not an encrypted backup.** An unsaved editor status survives only as long as that QML session does. If Quickshell restarts now, its text may still be lost. The UI explicitly says so.
- The status intentionally covers **two editor families**, not all future PROJECTS/PLANNER fields. A clean monitored set does not mean no other unsaved work exists.
- The new-task input can be nonempty without having been submitted; that is an unsaved draft, not a confirmed saved task.
- Pending `onSaved` is not independent disk readback, so the status says SAVE PENDING / NOT CONFIRMED rather than SAVED.
- A CPU++ keyring probe remains service presence only. The M13p mock approval cannot be reused as a real grant. No opt-in or key release has been implemented.
- This patch touches the shared Hub mini **only to add a read-only derived boolean**. Hub editing/scroll behavior and TASKS single writer must remain identical; any UI collision should revert this one small property change.
- Do not reset or pull the user's dirty live Quickshell repository to try this branch. Keep the operator's visual acceptance distinct from CI results.

## CHECKLIST

- [x] Reconstruct current main, merged CPU++ Connections field, source and ownership
- [x] Identify real entry/details editor state without copying plaintext
- [x] Route bounded booleans from TASKS editor owners to Recovery subtab
- [x] Add status labels that do not imply encryption or guaranteed recovery
- [x] Add CI/QML/parser/legacy writer regression coverage
- [ ] CI checks, independent review and operator merge decision
- [ ] Native Fedora Recovery visual/status test under new local approval
- [ ] Scope authenticated opt-in broker + key release and source anchor with respective owners
- [ ] Implement reviewed encrypted draft capture, retention, unlock/preview and restart recovery
- [ ] Operator final acceptance and production activation

## NEXT

**M13t proposed:** actual user opt-in and a trusted consent/key-release host contract through the already owned CPU++ Connections system; include installation-scoped OS keyring service rules and explicit revoke/retention behavior. Do not release keys based on an app-supplied label or a QML boolean. Only after a trusted saved-source revision is available should the host capture these real draft buffers. Later test restart/reboot with user-approved nonproduction drafts, then carefully activate for real tasks under separate authorization.

## DECISIONS

M13s is a **real read-only UI observation** of two live TASKS editors, not a fake draft and not encrypted persistence. Preserve accepted CPU++ layout, the shared keyring broker, the existing sole JSON writer, and all disabled real-recovery gates. No local edits, OS credential mutations, production activation, merge or live Hospital registration.
