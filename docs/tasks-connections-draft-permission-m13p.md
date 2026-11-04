# 🏥💜 TASKS M13p // CPU++ Connections Scoped Draft Consent Contract

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS encrypted draft recovery, shared Settings/Connections authority  
**WORKER //** OPEN AI // CHATGPT · Hospital-compatible external doctor, not verified live Hospital-registered  
**ASSIGNMENT //** Scope and test consent/key-release boundary without granting production authority  
**BASE //** `main` `0c7f0f05a6a33eb00622f4942a94c7d359b271ec`, November 4, 2026  
**PERMISSION //** Repository-only addition of fake/isolated tests + documentation. No CPU++/Connections/Social/actual TASKS code edits, OS keyring access, local workstation changes, production activation or merge.

## IMPLEMENTATION

### Verified ownership and latest checkpoints

- **Settings home exists:** `widgets/CpuPlusW.qml` has `SETTINGS → CONNECTIONS`. Its existing shared owner is `services/connections/ConnectionsBroker.qml` and related C2 policies. `ConnectionsRegistry.qml` catalogs metadata and the C2 broker is a read-only Secret Service presence probe. `credentialActionsEnabled` is literal false; `ConnectionsBrokerPolicy.decision()` denies every credential-grant operation. The current registered credentials are NASA FIRMS and Proton, not TASKS draft keys.
- **TASKS source of truth:** `services/hub/ApolloHubTodoStore.qml` is the single saved-task writer, with exactly one `FileView` and one `todoFile.setText()`. Its existing encrypted recovery/store/unlock/host flags are false.
- **Synthetic foundations:** M13l native operator PASS, M13n keyring/Node subprocess repair merged, M13m PR #1254 merged (fake encrypted-source transaction), and M13o PR #1258 remains **open draft, unmerged** at M13p preflight. M13p does not depend on importing M13o or enabling its disposable storage driver.
- **Authority:** Syntagma `AGENTS.md`, Hospital protocol and authority boundaries were inspected; no competing open TASKS or Settings branch touching this new test fixture was observed. CPU++ Connections and Social account management have their own ownership and must not be modified without coordination.

### This milestone implements

1. `tests/tasks/fixtures/TaskDraftConnectionsPermissionM13p.cjs` is a **never-mounted, fake-only, pure Node policy** for the future shared broker handshake. Its three **separate, fixed** TASKS scopes are:
   - `tasks.draft.capture.encrypted`: explicit TASKS feature opt-in + trusted broker. Saves only unfinished drafts, never the authoritative task JSON.
   - `tasks.draft.preview.unlocked`: separate unlock plus editor-specific review, not implicit access because capture is enabled.
   - `tasks.draft.clear.encrypted`: explicit confirmation and current checkpoint identity before deletion; no generic account/key deletion.
2. A **status-only** projection of the existing C2a provider probe displays `KEYRING FOUND / UNLOCK NOT VERIFIED` for `SERVICE_ACQUIRED`. It never treats key presence, a Social label or a clicked toggle as verified unlock or authorization.
3. A strict review descriptor carries only the fixed feature ID, operation/scope and TASKS presentation surface. All user-supplied account, credential, wildcard, arbitrary consumer, authority and extra fields are refused. The existing Settings/Connections broker has **not** been changed to register the new provider: until a reviewed owner does so, the requester is strictly informational.
4. A small fake review lifecycle exercises pending/acknowledged/denied/cancelled/expired/revoked and final-state replay refusal. Its synthetic state is caller-authored and **not a real signed receipt, identity proof, durable consent, expiration oracle, or capability grant**. The display never includes the fake request ID or any keys/draft text.
5. Every return object, **including synthetic success**, always contains `productionActivation:false`, `hostAuthenticated:false`, `callerAuthenticated:false`, `userConsentAuthenticated:false`, `keyringUnlocked:false`, `keyReleaseAuthorized:false`, `realGrantActive:false`, and false for all TASKS capture/preview/persist/restore/delete/source-write permissions.
6. New `tests/tasks/test_task_connections_permission_m13p.cjs` covers exact allowlists, unrelated provider/scope/consumer rejection, status-only keyring presence, fake approval without authority, revocation, expiry, malformed receipts and guard continuity. CI includes M13m transaction and M11d single-writer regressions.

### Intended *future* real handshake (not wired in M13p)

```text
TASKS editor proposes draft capture/preview/clear intent
       ↓ data and UI intent only; never carries an encryption key
CPU++ SETTINGS / CONNECTIONS shows fixed scope + account/installation
       ↓ explicit operation-specific operator confirmation
Trusted OS host broker verifies invoking application + active session
       ↓ verifies feature opt-in, grant scope/expiry/revocation
OS Secret Service releases a scoped random installation key to host only
       ↓ host performs AES-256-GCM and private checkpoint transaction
TASKS receives status-only checkpoint/locked candidate information
       ↓ separate unlock/preview and source conflict check
TASKS editor shows recovery candidate, no direct saved-JSON writes
```

The actual host transport should use an OS-controlled authenticated IPC boundary, not self-asserted `consumer:"tasks"` JSON. A same-UID process may impersonate an application name; PID/UID alone does not reliably isolate same-user desktop apps. Reuse the existing C2 broker design, its host ownership and future revocation system instead of running standalone `secret-tool lookup` from QML. Keep consent and key release independent: a request descriptor or simulated UI confirmation never becomes permission.

### Suggested CPU++ and TASKS labels, not yet rendered

**CPU++ → SETTINGS → CONNECTIONS:** `TASKS DRAFT RECOVERY` (OFF), `KEYRING AVAILABLE / UNLOCK UNKNOWN`, `REVIEW CAPTURE PERMISSION`, `PREVIEW REQUIRES SEPARATE UNLOCK`, `SCOPED DELETION`, `HOST APPROVAL UNAVAILABLE`.

**TASKS → RECOVERY:** `ENCRYPTED RECOVERY OFF`, `LOCKED DRAFT AVAILABLE`, `UNLOCK TO PREVIEW`, `KEEP CURRENT EDITOR`, `RESTORE INTO EDITOR` and `DELETE THIS CHECKPOINT`. Only show locked/recovery available after a trusted host reports an actual checkpoint. These labels are proposed, not enabled buttons.

## HOW TO USE

Review the PR and its CI. There is no new operator-facing Settings toggle or production keyring action. A developer can run the fake-only tests inside a separately reviewed checkout:

```bash
node --test tests/tasks/test_task_connections_permission_m13p.cjs
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

Do **not** wire `TaskDraftConnectionsPermissionM13p.cjs` into `ConnectionsBroker` or `ApolloHubTodoStore` as an authorization service; it is only a test contract.

## VERIFY

- Exactly three predeclared TASKS scopes; unrelated provider/account ID, arbitrary wildcard and caller-supplied privileges rejected.
- Keyring status `SERVICE_ACQUIRED` means **present only**, never unlocked, authenticated or consented.
- A fake APPROVED state does **not** permit key release, draft capture, preview, restore, deletion, or saved-task writes.
- Fake expiry, revocation and terminal state replay produce refusal, not resurrection of a grant.
- A review request carries no password, key, draft content or presumed account principal.
- CPU++/Connections existing production broker and TASKS writer/flags remain unchanged and disabled.
- Green CI proves only fake-model contract and existing static guards, **not** real Settings/QML permissions, trusted user identity, host isolation, durable opt-in, real key release or restart/reboot recovery.

## WATCH OUT FOR

- **No user permission yet.** The fake review receipt is deliberately untrusted and can be forged. Never treat it as production capability.
- **Do not mistake keyring availability for unlock.** GNOME Secret Service can be running while a collection is locked, absent, or inaccessible.
- **Avoid a second credential system.** CPU++/Connections owns the eventual shared host authorization, while TASKS owns draft content and editor conflict handling. Social accounts only provide identity labels until independently authenticated.
- **Same-UID OS boundary:** `0600` files, a keyring and a caller-declared provider name do not protect against an already compromised same-user session. State the threat model and require a trusted broker before granting keys to one widget while denying another.
- **No implicit consent:** An account connected to Post-Apollo, the presence of a key, or enabling another app must not turn on TASKS draft capture. Capture opt-in, preview unlock, and deletion are distinct operations.
- **No real source revision yet:** M13m's fake source generation and M13o's local CAS do not authenticate actual saved TASKS file revisions. A future owner must supply a last-confirmed source receipt before real checkpoint activation.
- **No default sync:** NAS/company-wide integration and employee roles must not inherit a personal TASKS key or approval. Future multi-user operation needs separate identity, tenant, device and retention policies.
- **M13o is not merged at this checkpoint.** M13p is independent; its review should not be interpreted as M13o acceptance or production storage authorization.

## CHECKLIST

- [x] Reconstruct Hospital, current GitHub, CPU++ Connections and TASKS ownership
- [x] Define exact operation scopes and review vocabulary without grants
- [x] Refuse caller-invented provider/consumer/account/permission fields
- [x] Test keyring presence vs actual authorization and expiry/revocation
- [x] Retain disabled C2 broker, unchanged TASKS singleton and one writer
- [ ] CI green; independent security review; operator acceptance/merge
- [ ] Coordinate a single trusted host-broker owner with C2 Connections workers
- [ ] Host-authenticated session/grant/retention/key-release design
- [ ] Last-confirmed TASKS source revision contract
- [ ] Real user-facing opt-in/preview/clear, isolated native tests, restart/reboot verification
- [ ] Final production activation and operator acceptance

## NEXT

**M13q (proposed):** Build a disabled-only QML **status/view** adapter for TASKS that displays the shared Connections broker's actual read-only keyring status and the fixed TASKS permission scopes, without importing secret material or activating any grant. Coordinate with CPU++ Connections owner before adding a new Settings row or button. Real host-authenticated opt-in remains a separate integration milestone.

## DECISIONS

Keep **standard OS keyring + vetted AES-256-GCM, explicit per-feature opt-in, scoped grant and revocation, one authoritative TASKS writer, no automatic sync**. This PR adds **only a fake-only test contract, tests, CI and documentation**. No local changes, no user keyring access, no production QML edits, no PR merge, no registered Hospital attachment, and no claim of live recovery.
