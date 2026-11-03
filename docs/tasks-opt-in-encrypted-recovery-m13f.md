# 🏥💜 TASKS M13f // Opt-In Encrypted Recovery Across Restarts

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity / encrypted draft recovery  
**ASSIGNMENT //** Operator-selected encrypted recovery direction; independently test disposable authenticated encryption and fresh-process recovery without selecting real key storage  
**WORKER //** OPEN AI // CHATGPT, external Hospital-compatible doctor, no live Hospital registration verified  
**GITHUB BASE //** `d510b4e6225ce2dfc08bc48435f44640b52a3da9`, November 3, 2026  
**PERMISSIONS //** Repository-only synthetic test/CI/docs. No local workstation, production Quickshell, real source/drafts, key store, process or UI changes.  
**DECISION STATUS //** Operator accepted **opt-in encrypted recovery across restarts** as the product direction. This does not approve a particular key provider, decrypt/unlock UX, encryption integration, path, migration or production activation.

## IMPLEMENTATION

### Explicit operator choice

Following M13e's privacy decision dossier, the operator said **“support opt-in encrypted recovery across restarts.”** This supersedes *memory-only as the future product goal* and commits the design direction to:

1. No persistent recovery of an unfinished task draft unless its owner expressly opts in.
2. Draft recovery data is authenticated-encrypted at rest, not plaintext, hash-only or a file protected only by Unix mode bits.
3. A restarted process must not display draft text until an authorized unlock; while locked, a future UI may show only a neutral recovery indicator subject to the eventual visibility decision.
4. A draft must not be auto-replayed into canonical TASKS, auto-deleted because of age, exported or synced because it exists.
5. The one authoritative local TASKS JSON write path, legacy UI and M12l coordinator decision remain separate; the encrypted draft capsule is **not** a second canonical task writer.

This is an approved **architectural direction**, not an approved live storage feature or choice of key material.

### Source evidence and narrow test implementation

- [M13e PR #1086](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1086) merged into `main` at `d510b4e6225ce2dfc08bc48435f44640b52a3da9`.
- `ApolloHubTodoStore.qml` still has exactly one `FileView` and one `todoFile.setText()`; `ticketProducerEnabled`, `guardedWriterEnabled`, and `independentlyAuthenticatedTicketReceipt` remain literal `false`.
- The earlier M13a–M13e recovery models are fake/test-only; M13a's plaintext stage record is **not an acceptable live persistent draft format**. M13f does not start storing actual drafts inside it.
- There were no competing open TASKS PRs at branch creation.

M13f adds **only** a reusable test fixture and a Node.js test suite, an isolated CI workflow and this report. The pure fixture `TaskEncryptedRecoveryM13f.cjs` uses Node's built-in `crypto` to encrypt *synthetic* `M13F_FAKE_DRAFT` objects with AES-256-GCM:

- The caller supplies an **ephemeral 32-byte test key** and `optedIn:true`. Missing opt-in, wrong key length or invalid synthetic draft/identity refuses before creating an envelope.
- A random **96-bit nonce** is generated for every encryption. The 128-bit authentication tag and ciphertext are serialized in a strictly versioned, size-bounded JSON envelope. An exact synthetic installation ID, stage ID, owner epoch and UI surface are bound as AEAD **associated authenticated data (AAD)**, rather than being stored as cleartext titles or project context.
- `inspectLocked()` returns only `locked:true` and a neutral recovery-available marker for a structurally valid envelope. It neither decrypts a title nor authenticates the whole record; a fully verified indicator requires unlock.
- `openAfterUnlock()` requires `unlocked:true`, an exact identity, ephemeral key and matching authenticated ciphertext/tag. Wrong key, mismatched installation/stage/epoch/surface, changed encrypted bytes and invalid format all refuse, returning **no plaintext draft**.
- Every path still returns `persistAuthorized:false`, `writeAuthorized:false`, `replayAuthorized:false`, `restoreAuthorized:false`, `exportAuthorized:false`, `deleteAuthorized:false`, `clearDraftAuthorized:false`, `syncAuthorized:false`, `sourceTrusted:false`, and `productionActivation:false`.

Only `tests/tasks/test_task_encrypted_recovery_m13f.cjs` performs filesystem I/O. It writes **one disposable encrypted capsule** into a fresh private `mkdtemp` directory via `O_CREAT|O_EXCL|O_NOFOLLOW` and mode `0600`, fsyncs file and parent directory, then starts a new disposable Node process. The parent supplies a *fake ephemeral key through stdin* solely to demonstrate post-restart cryptographic recovery **without** writing the key to disk or putting it in command-line arguments, environment variables, GitHub artifacts or logs. The child emits only a fixed synthetic success/refusal marker; no draft content is printed. Its new process independently reads the stored encrypted bytes.

**This stdin handoff is a CI simulation of an external unlock/key provider. It is not acceptable as a production credential-delivery design by itself.** It does not prove that the desktop has an OS secret-service/keyring, that the key is safely retained across real restarts, or that the operator's unlock is authenticated.

## HOW TO USE

No desktop action is required and no recovery menu exists from this milestone.

```bash
node --test tests/tasks/test_task_encrypted_recovery_m13f.cjs
```

This is for GitHub CI/developer disposable fixtures only. It creates and removes its **synthetic temp files**; it does not accept a real TASKS file path.

## VERIFY

CI checks:
- Off-by-default encryption refusal.
- AES-256-GCM encrypted file, correct permissions and no synthetic draft title, description or key in serialized file.
- A **fresh process** reopening the same encrypted file with an ephemeral test key successfully recovers only the synthetic draft.
- Fresh process without key, with wrong key or without unlock refuses.
- Unique 96-bit random nonces; wrong identity/AAD; altered nonce, tag, ciphertext, version, algorithm and foreign fields refuse.
- Second exclusive file creation is refused (`EEXIST`); first bytes remain intact.
- Existing M13a–M13e and M11d single-writer and disabled-mode contracts remain green.

**Evidence scope:** Successful GitHub CI would prove AES-GCM API operation, test-only file persistence across two processes, readback and failure handling **on a GitHub runner**. It would **not** prove keyring availability, per-install identity, secured key release, crash/power-loss recovery, real same-user adversary resistance, future draft-deletion semantics, or actual user consent.

## WATCH OUT FOR

1. **Key provider and unlock are unresolved.** Before real development, verify desktop-native key service support on the user's Fedora/Quickshell environment. Candidate approaches may include an OS Secret Service-compatible keyring or a separately authenticated passphrase-derived key; neither has been chosen, installed or verified here. Do not use hard-coded secrets or pass keys via argv/env in a real system.
2. **Do not persist plaintext checkpoints** from M13a or other test harnesses. Future production recovery must store only encrypted draft data, with independent source/epoch verification and a reliable commit/rollback strategy.
3. **Metadata leaks:** ciphertext length, file existence and its modification time remain observable to a process with file access. This fixture does not pad draft lengths.
4. **Replay/rollback:** AES-GCM authenticates contents and bound AAD. It does not prevent an old valid encrypted file from being replayed at the *same* identity/version. A separate trusted monotonic revision or journal remains necessary.
5. **Key recovery:** loss of the actual unlock key would prevent draft recovery. A future operator-approved backup/key recovery policy must specify this clearly.
6. **Same-UID protection:** owner-private `0700`/`0600` mode and AES-GCM cannot guarantee safety against a malicious same-user peer that can steal a key while unlocked. Threat boundaries remain those accepted under M12l.
7. **Memory:** Node Buffers and strings can remain in memory; this is not secure heap erasure. No untrusted user inputs or real secrets are processed in these tests.
8. **Power loss:** fsync in an isolated CI test does not prove target-device power-cut durability. A real native, fault-injection test is separately required.
9. **No permissions:** this branch does not install a keyring, pick an encryption key, change Quickshell QML, enable a ticket, export or delete anything, write real drafts or alter local Git state.

## CHECKLIST

- [x] Operator selected opt-in encrypted recovery direction
- [x] Recheck merged M13e and GitHub/Syntagma ownership and main branch
- [x] Add synthetic authenticated encryption with identity-bound AAD
- [x] Add locked no-content view, explicit fake unlock and tamper refusal
- [x] Test cross-process readback through temporary encrypted file and key sent via test-only stdin
- [x] Preserve production one-writer/ticket-disabled gates
- [ ] GitHub CI, independent source review
- [ ] Operator PR review/merge and consent to actual implementation details
- [ ] Read-only verify real desktop key provider, auth/unlock UX, storage permissions and backup policy
- [ ] Verify native encryption/decryption and on-device crash/locking on disposable data
- [ ] Separately authorize live UI wiring and first real opt-in

## NEXT

After the reviewed CI contract, inventory the exact desktop keyring/Secret Service functionality **read-only**, without creating credentials. Present a concrete key-provider/unlock selection for the operator; then test on a disposal-only native Quickshell/host runner under that provider. Define per-install key rotation/recovery, locked UI metadata disclosure, retention/manual deletion and backup/export policy before touching any live draft.

## DECISIONS

**Selected by operator:** opt-in encrypted recovery across restarts, not memory-only as the target feature.  
**Provisional cryptographic test choice:** AES-256-GCM with random nonce, identity-bound AAD and ephemeral synthetic key, **not** final deployment approval.  
**Not selected:** production keyring/passphrase method, unlock/authentication, persistent location, backup, export/deletion policy, retention period, or any source privilege.  
**Unchanged:** M12l single logical TASKS authority, legacy live FileView writer, disabled ticket flags, local desktop, no verified live Hospital attachment or activation.
