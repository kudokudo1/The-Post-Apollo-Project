# 🏥💜 TASKS M13m // Disabled Encrypted-Draft Transaction Contract

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS single JSON writer continuity and opt-in encrypted draft recovery  
**ASSIGNMENT //** Define and exercise a fail-closed recovery transaction contract with synthetic source binding, stale protection, preview and consent boundaries  
**WORKER //** OPEN AI // CHATGPT · external Hospital-compatible doctor, no verified live Hospital registration  
**GITHUB BASE //** `main` `dafdf58e82ce6e7dc82d93632226552b73a840cd`, November 4, 2026  
**PERMISSIONS //** Repository-only test, CI and documentation; no modification to live Quickshell, actual TASKS data, login keyring, production authentication, writer, QML, service registration, or PR merge.

## IMPLEMENTATION

### State and ownership confirmed

- M13l's **actual Fedora** native smoke returned `M13L_NATIVE_QML_IPC_AND_CLEANUP_PASS` after PR #1223's held-open stdin lifecycle repair, confirming synthetic QML → Node → private D-Bus/GNOME Keyring → returned status → host exit → cleanup. It is not real user-draft recoverability or reboot acceptance.
- The authoritative `services/hub/ApolloHubTodoStore.qml` remains at Git blob `279b06abd0ec4a7373dbf5be1ac1494766ca0f04`. Its sole `FileView` writes `Quickshell.dataDir + "/apollo-hub-todo-v1.json"` through one `todoFile.setText()`; in-memory `TodoPolicy` supports saved document version **3** while retaining legacy compatibility. FileView `onSaved` is the current normal mutation confirmation, but `onSaved` alone is **not independently authenticated durable readback**.
- The optional M12q ticket writer and recovery/security flags are literally false: `guardedWriterEnabled`, `ticketProducerEnabled`, `independentlyAuthenticatedTicketReceipt`, `encryptedRecoveryEnabled`, `encryptedRecoveryStorageAuthorized`, `encryptedRecoveryUnlockAuthorized`, `encryptedDraftHostEnabled`, and `encryptedDraftHostWriteAuthorized`.
- The M13f synthetic AES-256-GCM primitive authenticated the fake draft against installation ID, stage ID, epoch and surface, but did not itself compare draft source generation/digest or a trusted monotonic ledger. M13k/M13n's native host is intentionally hard-wired to a fake key/name and private test bus.
- No competing open TASKS PR was detected at assignment preflight. Syntagma `AGENTS.md` and OPERATE permissions were rechecked. No local machine operations performed.

### This milestone adds

1. `tests/tasks/fixtures/TaskEncryptedDraftTransactionM13m.cjs`: **pure, never-imported Node policy prototype**. It composes the existing M13f fake AES-GCM seal/open functions with a fake last-confirmed TASKS source, SHA-256 source digest, synthetic source generation, fake installation-scoped epoch, stage/surface, proposed checkpoint sequence and fake ledger. It accepts only explicitly marked fake JSON and fake editor drafts, and performs **no I/O, Secret Service access, real TASKS mutation or UI import**.
2. `createSyntheticCheckpoint()`: returns a ciphertext checkpoint *proposal* only if mock opt-in is true, source is synthetic version-3 JSON, source hash/generation equal the fake last-confirmed ledger, installation/epoch match and checkpoint sequence advances by exactly one. The source/sequence binding is itself placed inside the AES-GCM-authenticated fake plaintext; the public wrapper repeats source/stage metadata but changing these values cannot silently change the decrypted draft's authenticated context.
3. `simulateReadback()`: compares the exact proposed ciphertext bytes to a caller-provided synthetic readback and verifies fake ledger metadata. It is deliberately labeled `SYNTHETIC_BYTES_MATCH_NOT_DURABLE`. There is **no disk write, fsync, rename, durable ledger update or claimed producer authentication** in this module.
4. `inspectLocked()`: accepts only bounded encrypted wrapper data and returns a **content-free** locked indicator. It never exposes draft titles, project, task contents, surface or operation.
5. `evaluateSyntheticRecovery()`: refuses unavailable fake ledger, stale/nonlatest checkpoint, alternate installation/epoch/stage/surface, source digest/generation mismatch, active editor draft, missing distinct user review or missing unlock. It does not expose fake decrypted plaintext before these checks. After successful authenticated M13f fake decrypt, it also checks the encrypted source binding before returning only an **explicitly synthetic preview marker** with `PREVIEW_ONLY_NO_APPLY`.
6. **All return paths, including synthetic success, contain false** `productionActivation`, `userConsentAuthenticated`, `keyReleaseAuthorized`, `sourceTrusted`, `persistAuthorized`, `decryptAuthorized`, `previewAuthorized`, `restoreAuthorized`, `writeAuthorized`, `replayAuthorized`, `deleteAuthorized`, `clearDraftAuthorized`, `exportAuthorized`, `syncAuthorized`. A string, boolean, fake ledger, or synthetic success signal can never grant real authority.
7. `tests/tasks/test_task_encrypted_draft_transaction_m13m.cjs`: tests encryption, fake source binding, strict input schema, exact readback, replay and rollback signals, missing unlock, active-draft conflict, missing review, wrong key, wrong identity, and tampered ciphertext. It audits one-writer and literal-false production flags.
8. The M13m CI workflow runs the new tests and existing M13f / M13k / writer-inventory regressions. No QML compilation or live Fedora test is needed because **no production QML changes exist in this milestone**.

### Proposed real transaction contract (future milestone, NOT implemented)

```text
USER EXPLICITLY OPTS IN
     ↓ authenticated by settings/security owner, not an env var
UNSAVED EDITOR DRAFT + CONFIRMED SOURCE ANCHOR
     ↓ capture owner: one authoritative TASKS coordinator
CHECKPOINT PREPARE
     ↓ authenticated scoped OS key + AES-256-GCM with AAD binding
CIPHERTEXT WRITE TO PRIVATE TEMP FILE
     ↓ permissions + fsync(data) + atomic rename + fsync(directory)
DURABLE CHECKPOINT RECEIPT / TRUSTED REVISION FLOOR
     ↓ verify exact ciphertext + durable source/ledger invariants
RECOVERY AVAILABLE (LOCKED METADATA ONLY)
     ↓ distinct user unlock + preview intent + current-source compare
REVIEW IN EDITOR; NEVER WRITE SAVED TASKS DIRECTLY
     ↓ separate deliberate Save by normal TASKS method
SINGLE EXISTING JSON WRITER
```

Note that an *atomic rename* and a *trusted monotonic revision floor* across multiple files are not the same thing. Two independent rename operations cannot produce cross-resource atomicity. The durable ledger and ciphertext must be committed together through one trusted transactional storage owner or a recovery-safe journal protocol. A mere SHA-256 source digest identifies bytes; it does not prove they were authored by a trusted producer, and a copied older ledger plus older ciphertext can bypass a naive local rollback check. A future security review must specify which rollback adversary is in scope and whether hardware-backed counters or another trusted monotonic anchor are actually available.

### Intended UX, not yet mounted

The future CPU++/Settings security area owns the **user-controlled opt-in and credential/key permissions**; the TASKS widget owns per-draft editing and recovery presentation. A user should see clear controls such as `Draft recovery OFF/ON`, `Locked recovery available`, `Unlock to preview`, `Keep current draft`, `Restore into editor` and `Delete encrypted checkpoint`. Enabling general app integration in Settings is **not implicit consent** to draft capture. A recovered draft must never directly overwrite confirmed saved TASKS data, and conflict resolution must preserve both versions until the user chooses. No plaintext preview on lock screen or notification. Clarify key loss: without the proper key, encryption can make a draft permanently unrecoverable.

## HOW TO USE

No desktop action is needed for this design milestone. Review the GitHub PR and its CI; there is no operator-facing recovery toggle yet.

For a developer in a **separate reviewed checkout**, synthetic-only tests run:

```bash
node --test tests/tasks/test_task_encrypted_draft_transaction_m13m.cjs
node --test tests/tasks/test_task_encrypted_recovery_m13f.cjs
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

Do **not** import the M13m fixture into `shell.qml` or `ApolloHubTodoStore.qml`, connect it to actual task data, or treat fake opt-in/unlock booleans as real authorization.

## VERIFY

- Strict fake-only source and draft schemas; fail if a real source/draft value is supplied.
- AES-256-GCM envelope does not reveal fake plaintext or fake encryption key.
- Encrypted binding includes a precise source generation/hash, installation, epoch, stage/surface and checkpoint sequence.
- Unknown/stale checkpoint sequences, changed current source, active edit buffer, absent review and key unlock refuse before returning any preview.
- Wrong key, changed context and ciphertext authentication failures refuse.
- Synthetic positive results explicitly deny **all** production authority.
- Existing TASKS `FileView` remains singular; no added runtime `Process`/writer/persistence.
- Static tests pass in GitHub CI, but this does **not** prove real durable storage, authenticated identity, normal-user key release, actual reboot recovery or safe production UX.

## WATCH OUT FOR

- `M13m` is a **contract and executable test model**, not production draft protection. It is not a replacement for the legitimate OS key provider, a real consent service, a durable transactional ledger or secure-memory handling.
- Source generation is **not currently stored** in the version-3 TASKS JSON. M13m's generation exists only in fake data. Integrating with real saved TASKS requires a separately owned revision source and readback proof, not simply treating `Date.now()`, `nextId`, a file mtime or a user-supplied epoch as trustworthy.
- SHA-256 comparisons prevent accidental mismatch in the model; they are not signatures, authenticated source receipts or protection against an adversary controlling both the data and the purported baseline.
- AES-GCM ciphertext authenticity alone is not protection against restoring an old correctly encrypted checkpoint. The sequence floor must be independently trustworthy.
- Settings/CPU++, the shared account manager, the TASKS writer and the OS credential broker have different ownership; do not silently move permission keys or scope into the TASKS widget.
- The first production milestone should **capture only explicitly approved draft buffers**, encrypted to a scoped key, with strict retention/clear behavior. Production restore into a saved task file is not proposed.
- If privacy requirements prevent background draft capture, require explicit per-draft save. Either model needs informed opt-in, key unlock/release policy, disk quotas and defined retention/opt-out deletion semantics.
- Prior native PASS of fake encrypted host is valuable infrastructure evidence, not user acceptance of production recovery.

## CHECKLIST

- [x] Syntagma/Hospital policies, current TASKS source and repository state checked
- [x] Synthetic AES-GCM transaction candidate bound to fake last-confirmed source
- [x] Explicit source conflict, stale checkpoint, identity and active-draft guard
- [x] No-authority readback/locked-indicator/preview decisions
- [x] CI and source-only no-new-writer regression
- [ ] CI green, independent review, operator decision/merge
- [ ] Security owner defines authentic opt-in, key release, durability/rollback policy
- [ ] Settings/CPU++ design and actual TASKS recovery controls approved
- [ ] Separate real-host source-binding/durable checkpoint implementation under authorization
- [ ] Native opt-in test, restart/reboot recovery, conflict and key-loss drills
- [ ] Operator final acceptance and activation decision

## NEXT

**M13o proposal:** build the real security-owner contract for authenticated explicit opt-in, installation-scoped key release, durable ciphertext+ledger transaction, atomic source anchor and retention. Implement disabled-by-default host API behind an independently reviewed authority boundary, with a clearly separated recovery-preview control in TASKS. Only after those are tested should an operator authorize local activation.

**Recovery pointer:** Patient `kudokudo1/The-Post-Apollo-Project`; sole source writer `services/hub/ApolloHubTodoStore.qml`; fake AES-GCM `tests/tasks/fixtures/TaskEncryptedRecoveryM13f.cjs`; native synthetic host `tests/tasks/fixtures/TaskEncryptedDraftHostM13k.cjs`; M13l/Fedora operator result `M13L_NATIVE_QML_IPC_AND_CLEANUP_PASS`. Do not use an old local `/tmp` checkout after reboot.

## DECISIONS

**Verified:** Synthetic native QML process/crypto/keyring, current single JSON writer, real recovery disabled, no competing open TASKS PR at preflight.  
**Implemented:** Fake-only transaction contract, source-binding tests, strict preview/refusal behavior and design requirements.  
**Not established:** Trust in source/ledger, OS key release, actual user consent, durable checkpoint atomicity, rollover/rollback guarantees, real draft collection, recovery UI, reboot persistence or production safety.  
**Not performed:** Local changes, live Hospital registration, source writer edits, PR merge, production activation, or migration.
