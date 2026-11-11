# Social PHONE P35 // Isolated encrypted Personal contact metadata vault

> **STATE:** GitHub-only draft, synthetic crypto tests; **not** a production-enabled host or Favorites/Notes UI.
>
> **Patient:** \`kudokudo1/The-Post-Apollo-Project\`.
> **Staff:** external Hospital-compatible DOC. **Room / Assignment / Session:** No live registration verified. Bounded objective: P34's local Personal favorite/note document -> authenticated encrypted file storage, without adopting TASKS or Favorites++ ownership.
> **Checkpoint:** P34 [PR #1856](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1856) merged. P35 uses its existing pure metadata policy. PR #1851 contact address rows also merged.

## IMPLEMENTATION

\`services/phone/PhonePersonalContactVault.py\` implements a **dormant Python library**, with deliberately no public command line, QML/DBus integration, automatic key provisioning or local host activation.

- AES-256-GCM authenticated encryption using PyCA \`cryptography\`. Each committed document gets a fresh cryptographic 96-bit nonce; algorithm, version and profile UUID are associated with the AEAD additional authenticated data. No private name, phone number, email address, match proof, favorite state, or note body is written in plaintext. The on-disk record has exactly \`schema\`, \`version\`, \`algorithm\`, \`nonce\`, \`ciphertext\`.
- Requires an **in-memory 256-bit master key from a future explicitly authorized trusted host**. Independent HMAC-SHA256 subkeys segregate file naming, AES-GCM encryption and P34 contact matching. Keys do not enter command arguments, environment variables or files. The library neither stores nor retrieves a master key.
- Each caller-selected \`contact-vault-v1\` directory is restricted to **one phone profile**. File name is a keyed digest of the profile UUID, never a plaintext profile/name. If an older inaccessible file, wrong key, unexpected file or orphan temp file exists in the directory, read/write refuses rather than silently creating a shadow vault.
- A missing directory is read as an empty P34 document **without creating a folder**. Only an explicit \`commit\` can create a 0700 owner-only directory and atomically replace a 0600 single-link ciphertext file. Existing file, lock file, and parent folder ownership/permissions are checked. Writes use exclusive 0600 temp files, file fsync, OS file locking, revision compare-and-swap, atomic replace and directory fsync.
- \`read\` decrypts and validates the exact P34 document schema and checks that every record belongs to the requested phone profile. The returned plaintext document is **only for a trusted in-process caller** after consent checks. No notes are returned to QML or any public IPC by this source.
- \`commit\` requires a valid revised P34 document, exactly \`expected_revision + 1\`, against a re-read and authenticated on-disk revision under the file lock. Stale writes, malformed records, authentication failures and invalid profiles refuse instead of overwriting. An explicitly confirmed, revision-checked \`erase\` removes only the selected ciphertext file; unrelated store data is untouched.

## HOW TO USE

There is **no user-facing switch** in PHONE for this stage. The code has no executable entrypoint. A later trusted Personal host must verify a real current \`contacts.read\` grant, current phone profile/BlueFerry owner, a direct user action and keyring/unlock status, then call the library with a key supplied in memory. This engine does **not** decide authorization itself.

Generic Favorites++, AppControl favorites, ApolloHub Notes, existing wallet state, TASKS keyrings, iPhone contacts and the Personal read preference are unchanged. Real favorite stars and notes editing remain disabled until the host's authority, key lifecycle and UI can truthfully confirm encrypted save success.

## VERIFY

- New synthetic \`tests/phone/test_phone_personal_contact_vault.py\` checks fresh nonce, authenticated AES-GCM seal/unseal, no plaintext in files or names, 0700/0600 permissions, fresh-process recovery from a fake key passed through test stdin, wrong-key/profile refusal, tampered/malformed records, atomic failure preservation, revision conflicts, orphan and hardlink/symlink denial, explicit deletion and absent-library failure.
- Separate P35 GitHub workflow installs \`cryptography==50.0.2\` on the **ephemeral CI runner only** and runs the actual crypto tests plus the existing P34 identity policy. General Social PHONE CI compiles both the vault and the synthetic test without requiring the crypto package on the operator's desktop.
- These tests prove the test API and disk format with fabricated data only. **They do not prove** GNOME Keyring integration, real Fedora runtime package availability, unlock flow, malicious same-UID isolation, crash/power-loss resistance in every filesystem, actual operator reboot recovery, key rotation, hardware-backed protection, or authenticated app-specific consent.

## WATCH OUT FOR

- A 0700 directory and 0600 file add OS discretionary access control but **are not the encryption key**. AES-GCM protects at-rest content only while the caller-supplied key remains secret. An unlocked Secret Service collection can often be read by eligible same-user-session clients; this vault does not solve that authority boundary.
- The caller must choose an isolated, trusted, canonical absolute parent path and **a distinct root per phone profile**. The library refuses unexpected files rather than silently migrating or cleaning them.
- A missing key is **not** recovered by trying another key or resetting the store. A wrong master key cannot decrypt the previous file. The future host needs explicit backup/recovery/rotation and must not create a replacement key automatically when encrypted data already exists.
- AEAD detects tampering; it does **not** provide independent historical rollback protection if an attacker replaces an entire valid old ciphertext record. Revision checking serializes cooperating writers, not arbitrary malicious same-UID processes.
- Python immutable plaintext strings and secret bytes may exist transiently in process memory and swap. There is no host memory-zeroing guarantee.
- The P34 HMAC is only a candidate match from the first up to 100 currently returned BlueFerry contact records, not a verified durable person identity. This module does not automatically match, relink, publish or reveal notes.

## CHECKLIST

- [x] Preserve P34 match policy and existing Favorites++ ownership.
- [x] Implement real authenticated encryption rather than treating private file permissions as encryption.
- [x] Implement private, revisioned, atomically replaced ciphertext with explicit erase.
- [x] Fail closed on corrupt data, missing dependency, wrong key, stale revision, unexpected files and unsafe local file state.
- [x] Keep all production authorizations, key management and UI disconnected.
- [x] Include synthetic tests and dedicated CI.
- [ ] Inspect exact-head CI.
- [ ] Operator PR review/merge.
- [ ] Select a trusted key provider and explicit unlock/key recovery experience.
- [ ] Implement a separately authorized host interface binding current \`contacts.read\` and device profile to one encrypted save.
- [ ] Verify approved disposable native Fedora test, then first real contact favorite/note UI; user accepts separately.

## NEXT

**P36:** Build the approved *trusted-host key lifecycle and one-shot write authorization boundary*, preferably beginning with a disposable synthetic Secret Service item and a private test session. Reuse the keyring capability lessons from TASKS M13g/M13h, but do **not** share TASKS' key or plaintext store. Do not auto-unlock GNOME Keyring or install new packages on the user's Fedora desktop. Confirm recovery, lock/unlock and explicit save semantics before connecting the visible FAVORITE star and NOTES editor.

## DECISIONS

- No production activation and no silent local state changes.
- No plaintext secrets in Favorites++, ApolloHub Notes, read preference, IPC, logs or paths.
- No implicit key generation, guessing or substitute cipher when the crypto dependency is absent.
- No direct call or message effect.
- One vault root per phone profile, never populated from untrusted QML-provided profile IDs alone.
- GitHub remains technical source of truth; real desktop acceptance and Hospital live registration remain separate.
