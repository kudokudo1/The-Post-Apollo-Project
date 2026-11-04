# 🏥💜 TASKS // M13o Standard-Security Storage Foundation

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS encrypted draft recovery  
**WORKER //** OPEN AI // CHATGPT · external Hospital-compatible, live Hospital registration not verified  
**ASSIGNMENT //** Standard Linux/desktop encrypted-draft storage architecture and disposable private-file contract  
**BASE //** `main` at `8ce977f64b98aac4611e1371a228338e2070e637` (November 4, 2026)  
**AUTHORITY //** Repository-only isolated fixtures, CI and documentation. No workstation modifications, QML production changes, real user data, actual keyring writes, live activation or PR merges.

## IMPLEMENTATION

### Starting evidence

- M13m PR #1254 **merged** with source-binding and fail-closed encrypted draft transaction model. M13l's operator-run Fedora smoke previously returned `M13L_NATIVE_QML_IPC_AND_CLEANUP_PASS` using disposable data, confirming native QML → Node host → private D-Bus/Secret Service → reply and process exit.
- Current TASKS continues to persist version-3 JSON through `services/hub/ApolloHubTodoStore.qml`, with one `FileView`, one `todoFile.setText()`, and every real encrypted-draft/ticket/guarded-writer flag literally false.
- There were no other open TASKS or Settings PRs during preflight. Syntagma `AGENTS.md`, Hospital and authority protocols were inspected. CPU++/Settings ownership remains **separate** and is not modified.

### Standard-security choices (future production contract)

1. **Explicit opt-in:** Default OFF. Settings/CPU++'s shared security/account area may manage user credential permissions, but a separate TASKS-specific opt-in is required for saving unfinished drafts. Global API/provider permissions are *not* consent. Recovery preview requires an explicit user action and an unlocked keyring.
2. **Use established OS security:** GNOME Secret Service / OS keyring stores an installation-scoped random encryption key, subject to OS unlock policy. Encrypt draft payloads with a vetted AES-256-GCM implementation (as previously tested), fresh nonce per checkpoint, and associated data binding installation, editor/stage, epoch and source revision. Do not invent login passwords, reuse account tokens as encryption keys, pass secrets in process arguments/environment/logs, or embed keys in ciphertext files.
3. **Private local files:** A dedicated application-owned directory (0700) and ciphertext file (0600), no symlink traversal, bounded sizes, atomic same-directory rename, file fsync, directory fsync, exact readback, and a fail-closed lock to prevent two writers from committing concurrently. No network sync by default.
4. **One checkpoint record:** Keep the encrypted envelope and the checkpoint's proposed sequence/source ledger in **one** atomic file, instead of two independently renamed files that can disagree after a crash. Existing TASKS saved JSON remains the *only* authoritative saved-task source. A recovered draft returns to an editor preview, never writes the saved JSON itself.
5. **Conflict and rollback:** Compare checkpoint's source generation/digest and latest-sequence receipt with last-confirmed source state before showing a preview. A file-local revision counter detects accidental stale writers, but **does not stop an attacker restoring an old copy of the entire checkpoint**. Strong rollback protection would require a trusted external monotonic anchor. Do not claim that capability is present on this desktop.
6. **Retention and opt-out:** Include an explicit `Delete encrypted draft` operation, bounded storage use, and retention controls in the future Settings/TASKS UI. On opt-out, stop future capture first, then let the user choose whether to delete retained ciphertext. Deleting a file is not guaranteed secure erasure on SSD/COW/snapshots/backups. Key loss means recovery may be impossible.

### What this PR implements now

- `tests/tasks/fixtures/TaskEncryptedDraftPrivateStorageM13o.cjs`: a **test-only, disposable root** persistence driver. It refuses every directory except an existing user-owned, 0700, non-symlink, directly under `/tmp/postapollo-m13o-disposable-*` on non-root Linux. No free-form path is accepted for files.
- It accepts only the existing **M13m fake-only encrypted prepared checkpoint** and uses `simulateReadback`/locked inspection to validate the synthetic record. It combines ciphertext and fake ledger in a single bounded `checkpoint.json`; it does not persist the actual task JSON.
- Under an exclusive `writer.lock` directory, it checks the last on-disk checkpoint sequence (compare-and-swap), installation, epoch and source anchor. It refuses stale sequence, missing prior state, corrupt/symlinked/insecure prior file, or a pre-existing lock. **No stale-lock stealing** is attempted.
- It stages to a randomly named, exclusive 0600 file with `O_NOFOLLOW`, flushes the staged file, renames it over the previous checkpoint atomically on the same filesystem, flushes the parent directory, reads exact bytes back, and only then returns the status `SIMULATED_PRIVATE_ATOMIC_RENAME_AND_READBACK_PASS`.
- A locked-only inspection returns no decrypted text. An explicit synthetic clear operation checks the current sequence, removes only the known fake ciphertext file, fsyncs the directory and verifies absence. No keyring item is deleted.
- **All returned permission booleans remain false, including successful synthetic transactions.** No production QML import, source writer or key-release route was added.
- `tests/tasks/test_task_encrypted_draft_private_storage_m13o.cjs`: verifies fake ciphertext privacy, permissions, fresh-process inspection, stale writer refusal, source/installation change, insecure directory and symlink rejection, lock collision, explicit clear, and unchanged production source. CI also re-runs M13m + M13f and writer inventory.

### Boundaries

This is a real filesystem **test**, unlike M13m's pure memory model, but it persists **only synthetic data in a newly created disposable test root**. It does not authenticate operator consent, call a real OS keyring, capture live drafts, bind to an actual durable TASKS generation, or provide multi-process hostile-UID isolation. File+directory fsync is a standard durability technique, not proof against all hardware failures.

## HOW TO USE

No changes to your desktop or TASKS widget are needed. The review target is the GitHub draft PR, not a local installation. Once reviewed, a developer may test in an isolated checkout with:

```bash
node --test tests/tasks/test_task_encrypted_draft_private_storage_m13o.cjs
node --test tests/tasks/test_task_encrypted_draft_transaction_m13m.cjs
python3 tests/tasks/test_task_writer_gate_inventory_m11d.py
```

There is **no user-facing Settings toggle yet**. Do not import the test driver into real TASKS or direct it toward `~/.config`, `Quickshell.dataDir`, or real login-session Secret Service.

## VERIFY

- Private root must be owner-only, canonical, non-root, and under a uniquely named `/tmp` disposable test directory.
- Synthetic ciphertext and a fake ledger are committed together using exclusive staging + fsync + same-directory atomic rename + fsync + readback, with a lock.
- Stale checkpoint and source-anchor conflicts refuse rather than overwriting newer records.
- Corrupted, symlinked, wrong-permission existing records refuse, never treated as missing/empty.
- Locked inspection and status output never expose fake draft plaintext or encryption keys.
- Explicit clear refuses absent confirmation/incorrect sequence and verifies ciphertext removal.
- Existing real TASKS writer inventory, legacy encrypted tests, and production-disabled source remain unchanged.
- CI green establishes disposable Linux file behavior only, not production secure draft recovery or a reboot/hostile power-loss acceptance test.

## WATCH OUT FOR

- Crash after successful rename but before directory flush/readback may leave ambiguous state. The API refuses rather than incorrectly claiming a durable result; next launch must inspect and reconcile it, not auto-overwrite.
- Lock directories remain on interrupted processes. In production, recover stale locks only with independently checked ownership/age/process state, not by blindly deleting another process's lock.
- A compromised same-UID process can access the user's files/keyring depending on OS policy; 0700/0600 cannot isolate from malware running as the same user.
- SHA-256 source digests are not signatures or authenticated durable source generations. M13o has **no independently trusted rollback ledger**; accidental conflicting revisions are checked, adversarial whole-file rollback remains possible.
- Real user consent and OS key release are separate from an in-memory `optedIn:true` and `unlocked:true` test flag. Those flags **must never grant production authority**.
- Do not claim the future encrypted checkpoint file is a backup of already saved tasks. It is for *unsaved editor drafts*, not an alternate TASKS source of truth.
- Deletion of ciphertext and deletion of a keyring secret are different operations and require reviewed, narrowly scoped permissions.

## CHECKLIST

- [x] Verify merged M13m and current TASKS/Settings ownership
- [x] Standard-security storage contract with private permissions and crash-safe staging
- [x] M13m fake-only encrypted record and stale CAS
- [x] Locked inspection, explicit synthetic clear and fail-closed lock
- [x] Automated privacy/security and one-writer regression checks
- [ ] Green CI, independent technical review, operator merge/acceptance
- [ ] Security owner finalizes trusted key/consent API and real source generation
- [ ] TASKS recovery preview controls separately approved
- [ ] Opt-in test using real draft data, process restart/reboot, conflict and key-loss drills
- [ ] Final production activation and operator acceptance

## NEXT

**M13p proposed:** design a disabled-only Settings/CPU++ permission handshake for key provider status and explicit TASKS opt-in with independent scope, authenticated consent/OS key release, and a real last-confirmed TASKS source revision. Review retention/clear UX and key-loss behavior. Keep direct source writes with the single existing TASKS writer. Only then add a live encrypted-draft capture toggle and an operator-approved native restart test.

## DECISIONS

Standard Linux desktop controls, no bespoke credential framework, no hardware security dependency, no global key reuse, no default network sync. Current artifact is **synthetic and isolated**, not a production storage authority. No local writes by the external worker, no production QML modification, no keyring action, no live Hospital registration, no merge, no real activation.
