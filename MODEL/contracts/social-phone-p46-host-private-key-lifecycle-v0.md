# Social PHONE P46 // Host-private master key provisioning and recovery

**Patient** `kudokudo1/The-Post-Apollo-Project`  
**Staff role** external Hospital-compatible PHONE DOC. Live Hospital Room/Assignment/Session not verified.  
**Recovery pointer** P45 [PR #1957](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1957) is an OPEN, green, unmerged draft on `main`. P46 is based on P45's exact head but its PR targets `main` to prevent another side-branch-merged false delivery. P43 and P44 originally show merged but P44 was missing on main, repaired inside P45.  
**External issue** [#1885](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1885).

## IMPLEMENTATION

This is a **coherent host-private key lifecycle slice**, not a standalone boolean trust adapter:

1. `PhonePersonalKeyProvisionP46.py` prepares a fresh 128-bit opaque key selector and a distinct random 256-bit P35 master key from OS CSPRNG. Both exist only in memory and are redacted from object representation. A separately installed and independently authenticated host may eventually provision that exact master into the existing P45 Secret Service `post-apollo-phone-personal-protected-v1` attribute namespace. The mechanism only runs after two caller-provided readiness checks and an **external atomic unused-key-ID reservation**. It uses an absolute `/usr/bin/secret-tool store --label=...` invocation with the 43-character canonical URL-safe base64 key passed on stdin **without newline**, no key in argv/environment, timeout and bounded empty stdout. It reads back using P45's strict lookup, compares full bytes in constant time, and returns an authorization-false, content-free result. On any failure, including a write that may already have reached the provider, it **never automatically retries, clears or overwrites**. `secret-tool store` itself can replace matching attributes; the external durable reservation is mandatory.

2. `PhonePersonalRecoveryEnvelopeP46.py` seals the same master entirely in memory under a **separate**, externally safeguarded 32-byte recovery secret. Its AES-256-GCM key is HMAC-domain separated and salted, with fresh nonce; envelope header includes canonical schema, epoch and ciphertext, but **does not contain the master key or plaintext profile ID**. Authenticated data binds the exact profile and epoch. Import checks strict canonical JSON, unique keys, URL-safe encoding, length, signature-independent minimum epoch check and GCM tag. Wrong key, altered epoch, profile, salt, nonce, ciphertext or rollback epoch all fail closed. It never writes a recovery file, stores a recovery key, imports a keyring item or activates restored data.

3. Adversarial disposable tests prove first-use preparation and mocked store/lookup arguments, no PATH shadowing, failure-no-retry, no key in returned errors, anti-tamper/strict recovery envelopes, and that a restored in-memory master can decrypt a real P35 AES-GCM *synthetic* contact vault. Dedicated CI reruns existing P45, P44, P35, P36 and P40R tests.

**Trust boundary:** Both readiness/reservation callbacks are forgeable by ordinary Python, so they are testable plumbing, **not** externally enrolled host authorization. The Secret Service namespace is only metadata attributes, NOT a physically isolated collection or UID. The full real host must attest SELinux/process/cgroup/seat, pin libsecret executable and collection, enforce locked state without a prompt, own a durable reservation ledger and hold genuine one-use C3e/C5 action authority before installing or using any real Personal master. Python byte objects also cannot be reliably wiped from memory, which must be considered during protected service design.

## HOW TO USE

No live operator action. No real Personal key is created, imported, looked up, rotated, or erased by this PR. There is no CLI, QML SAVE, IPC, migration, or installed background service. The real Social → PHONE Favorites/Notes editor remains **preview only** with SAVE hard disabled.

## VERIFY

Run dedicated P46 GitHub Actions workflow on the exact PR head. Validate no real `secret-tool` calls in CI, no private content on stdout or stderr in module errors, and recovery test against P35 encrypted vault using only throwaway values. Require P45 mainline-completeness assertion and full P44 encrypted Favorite/Note test matrix.

Official `secret-tool` behavior: [GNOME libsecret source](https://github.com/GNOME/libsecret/blob/main/tool/secret-tool.c), [secret-tool manual](https://manpages.debian.org/trixie/libsecret-tools/secret-tool.1.en.html). Key storage may update an existing same-attribute item, and stored stdin newline is preserved. Both are reasons to require canonical no-newline material and externally reserved selector.

## WATCH OUT FOR

- No production host release, keyring auth, external signer pinning or human consent is established here. A successful cryptographic roundtrip is not a save grant or rollback-proof backup.
- `store` is a real, state-changing operation **if a future host invokes it**, but this repository PR does not invoke it. Do not call it manually or wire it to QML. Native machine mutation requires separate operator permission.
- The **recovery secret must be held independently** of the encrypted Personal vault and master. A lost recovery secret or missing sealed vault file cannot be reconstructed from a hash or selector.
- The caller-provided minimum epoch is NOT an independent anti-rollback ledger. No real restore, rotation, deletion, backup-file transfer or password-based recovery is approved. Rotation requires P35 encrypted vault re-encryption with durable crash-recovery and both old/new keys held securely; deletion requires independent confirmed archive/erasure sequencing and C5 consent. No `secret-tool clear` shortcut.
- C4b Identity Silverblue #1785 still OPEN; C3e-AB #1939 is a diagnostic merge, not an enrolled host; genuine C5 PHONE per-action signed consent remains missing.

## CHECKLIST

- [x] Verify P45 still open and P44 still absent from `main`.
- [x] Continue only PHONE-owned modules, tests, workflow, contract.
- [x] Implement CSPRNG key preparation and host-private readback-verified Secret Service store mechanism.
- [x] Implement separate-key encrypted, profile/epoch-bound recovery envelope.
- [x] Test failure and uncertain provider operations without retries, ciphertext-only disposable recovery.
- [ ] Exact-head dedicated P46 CI and integration regressions.
- [ ] P45 independent review/merge, then P46 review/merge to `main` with real post-merge completeness check.
- [ ] C3e/C4b/Identity enrolled host and one-use ledger, C5 genuine signed PHONE consent.
- [ ] PHONE actual host installation and collection lifecycle (lock/unlock), durable key reservation, recovery transfer and rotation/erase, protected lease through P35 commit.
- [ ] Enable persistent SAVE only after authenticated result/readback and native Fedora acceptance.

## NEXT

Deliver protected installed PHONE host with **independent release/process/seat attestation**, nonforgeable host-owned key reservation, collection lock state, and issued one-use C3e + signed C5 authorization. Wire P46 key creation/recovery to that host (without QML key access), P41b editHmac and P44 one-action encrypted CAS through final save/readback. Native Fedora and operator acceptance remain distinct release gates.

## DECISIONS

New source is dormant in the repository. No actual user keyring, local machine, personal note, device, service, external owner code, PR merge or production activation changes. Final acceptance remains with the operator.
