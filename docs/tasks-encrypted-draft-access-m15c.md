# 🏥💜 TASKS // M15c Encrypted Draft Recovery Access Interface

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS Encrypted Draft Recovery  
**ASSIGNMENT //** Integrate a real operator-facing encrypted capture/unlock-preview/clear action contract with the existing recovery screen, without claiming or activating a trusted credential host  
**STAFF ROLE //** DOC, external Hospital-compatible OPEN AI // CHATGPT; no live Hospital registration verified  
**CHECKPOINT //** M15b PR #1426 merged into `main` at `9f28fef8e370b993a80ee7ebdc694525b2a948d9`; M15c branch based on `d7955a8d89832fb3dae4175aa1831adba37bf6bd` on November 7, 2026  
**SCOPE/PERMISSIONS //** Bounded GitHub QML/JS/test/CI/docs implementation. No live Fedora file changes, restart or deployment; no OS key release, real draft capture, production activation, shared Connections ownership edits or PR merge. Operator explicitly waived Nurse 2 independent review for this assignment. Other safeguards remain.

## IMPLEMENTATION

### Baseline

M15a added an explicit read-only real saved-source structure check to **TASKS → SYNC → RECOVERY**. M15b proved AES-256-GCM private checkpoint storage, genuine disposable Secret Service key handling, and independent-process restart/unlock for **synthetic drafts only**, with the production broker and TASKS host still default-denied.

A live encrypted capture/preview button cannot responsibly activate yet:

- `ConnectionsBroker.qml` currently registers only NASA FIRMS and Proton providers. It contains no TASKS draft credential provider, grant authority, authenticated invoking-client identity or trusted key-release host. Its `credentialActionsEnabled` is literal false.
- `ApolloHubTodoStore.qml` still has the only authoritative saved-TASKS `FileView` writer and `todoFile.setText()` source write. Its encrypted-recovery, storage, unlock, and draft-host flags remain false.
- M13s currently exposes only booleans for NEW TASK/RENAME and TASK DETAILS unsaved content. It deliberately does not share actual editor text or IDs. Binding these booleans directly to a storage host would not capture a draft, and secretly adding plaintext transport would breach the approved opt-in boundary.
- M13p defines separate fixed scopes for `tasks.draft.capture.encrypted`, `tasks.draft.preview.unlocked`, and `tasks.draft.clear.encrypted`. M13t's synthetic operator cannot be used as genuine production consent.

### M15c implementation

- New `TaskEncryptedDraftAccessPaneM15c.qml` mounts within existing **TASKS → SYNC → RECOVERY**. It offers the standard top-row mode controls **CAPTURE / PREVIEW / CLEAR** and an operator-clicked **CHECK REQUIREMENTS** action. Changing modes changes the specified scope and its honest explanation. The three real protected action labels remain visible but **disabled**.
- The parent `TaskRecoveryStatusPaneM13q.qml` supplies only the existing M13s editor status, shared C2 provider status, the literal-disabled broker-registration/readiness placeholders, and the existing disabled TASKS recovery flags. This operation calls **neither** `ConnectionsBroker.requirement()` **nor** `ConnectionsBroker.authorize()`, preserving M13q's strict status-only boundary. There is no credential request. A future catalog registration does not automatically enable any of the buttons.
- New `TaskEncryptedDraftAccessPolicyM15c.js` is a pure finite-mode, exact-input, fail-closed view model. Every result, including an unexpected enabled flag or asserted provider registration, contains **false** for operation availability, host/user authentication, key release, encrypted capture, decrypt preview, encrypted clear, task source writing, automatic replay, draft deletion, and source checkpoint inspection. It does not accept names, paths, task data, encrypted payloads, credentials, source hashes, synthetic approval claims or free-form source text. Its rationale distinguishes provider present, editor missing, unregistered TASKS provider, and unexpected authority-state changes.
- `TaskEncryptedDraftAccessSmokeM15c.qml` is an isolated CI-only real Quickshell layout harness. On a private Xvfb display it exercises all three modes, verifies unchanged disabled powers and observes a deliberately forged activated-flag condition fail closed. It is never imported into production `shell.qml`.
- No new `FileView`, `Process`, secret-tool call, keyring host, backend, user content storage, automatic capture, settings toggle, auto-replay, restore, or plaintext draft wire is introduced. The previously merged M13q/M13s/M13z/M14a/M15a screens remain accessible; only the recovery page gains this contract view.

### Ownership boundary

The shared CPU++ Settings/Connections system continues to own real operator consent and credential authentication. The TASKS operator-facing screen may explain what would be requested, but cannot create approval by setting `checked:true` or pretending a name is authenticated. Exact scoped permissions remain independent:

| Operation | Required permission | Production authority |
|---|---|---|
| Capture unfinished editor draft | `tasks.draft.capture.encrypted` | Disabled |
| Unlock and preview an encrypted recovery candidate | `tasks.draft.preview.unlocked` | Disabled |
| Explicitly delete one checkpoint | `tasks.draft.clear.encrypted` | Disabled |

## HOW TO USE

After operator-approved merge and **separately authorized desktop deployment**, open **TASKS → SYNC → RECOVERY → ENCRYPTED DRAFT**.

Choose **CAPTURE**, **PREVIEW** or **CLEAR**, then click **CHECK REQUIREMENTS**. This checks only currently known public readiness metadata and displays the exact operation scope and missing production authority. The companion `SAVE ENCRYPTED DRAFT`, `UNLOCK DRAFT PREVIEW`, and `DELETE ENCRYPTED DRAFT` action remains disabled.

The same RECOVERY page retains **CHECK KEYRING STATUS**, which is only a read-only OS service-presence probe, and **CHECK LOCAL SOURCE**, which is a separately opted-in, read-only JSON check. Neither unlocks a draft.

No terminal instructions or user credentials are needed to inspect M15c. No real draft will survive a restart as a result of using this UI alone.

## VERIFY

`tests/tasks/test_task_encrypted_draft_access_m15c.cjs` checks all three fixed M13p scopes, no shared broker catalog/authorize calls, ordinary and forged authority-state refusal, no extra fields or plaintext echo, zero power in every projection, exact QML mount order, disabled protected action and the one existing TASKS source writer. CI reruns M13p/M13t, M13q/M13s/M13z/M14a, M15a and the C2a/M11d security baselines. Qt 6 `qmlformat` parses both changed QML components and the CI-only root.

The real Quickshell CI job runs the isolated pane with Debian Quickshell 0.3.2 under a private Xvfb X11 display, verifies three scopes remain disabled and refuses a future unexpectedly activated authority flag. A native CI PASS verifies layout/component evaluation in X11, **not Fedora/SwayPX compositor or actual encrypted recovery**.

**Final PR-head CI, CI fixes and final operator acceptance are separate checkpoints.**

## WATCH OUT FOR

**M15c is an interface and integration contract, not real encrypted draft persistence.** There is still no production authenticated Secrets Service caller, saved-source receipt, per-editor draft transport, explicit capture action, encrypted checkpoint preview data, or permitted deletion action. A visible mode label or checked requirement is not consent or evidence of a recovery candidate.

The current shared broker's `tasks-draft` catalog lookup returns unregistered. That is intentional and honest. Do not "fix" this by registering a static provider and setting `credentialActionsEnabled:true` without independent credential/consent host work. Existing M15b real cryptography was exercised only inside disposable CI. A task can still be lost after a crash until the final live capture path is authorized, implemented and natively verified.

## CHECKLIST

- [x] Confirm latest merged M15b, current main, Syntagma and no active competing TASKS PRs
- [x] Preserve separate capture/preview/clear operation scopes and original owner boundaries
- [x] Mount existing-style operator-facing recovery action preflight
- [x] Reuse existing keyring and editor status signals, without plaintext transport
- [x] Require explicit human click for requirements review and keep real actions default disabled
- [x] Add exact-schema security tests and real native QML acceptance workflow
- [ ] Final exact-head CI verification
- [ ] Operator merge decision, no Nurse 2 review at operator request
- [ ] Trusted OS-backed Connections consent, caller attribution, revocation and scoped key release
- [ ] Authorized live editor draft capture, encrypted checkpoint preview and explicit deletion
- [ ] Separate operator-approved Fedora/Wayland acceptance

## NEXT // M15d

Coordinate shared Connections' trusted consent/key-release interface with its owner; do not change shared code inside this TASKS job. In the TASKS-owned seam, introduce a **default-denied, data-minimizing draft packet boundary** that can collect one chosen editor's actual text **only after** a real host-authorized capture grant, then deliver to an independently authenticated encrypted host. M15b's private-storage pattern should be reused, not copied into a second writer or plain JSON backup.

The first true user-facing acceptance criterion is: opt in, edit a task without saving, capture an encrypted checkpoint, restart Quickshell, separately unlock and preview the checkpoint, and retain existing saved tasks without accidental replay. The current M15c does **not** satisfy that yet.

## DECISIONS

Keep M12l local-first single TASKS saved-JSON writer. No production keyring grant, automatic recovery, plaintext draft persistence, alternate source reader, file-copy backup, local machine write, PR merge or live Hospital registration. M15c only exposes and tests the currently denied recovery operation interface. User retains final authority over merge, deployment and acceptance; independent Nurse 2 review waived.
