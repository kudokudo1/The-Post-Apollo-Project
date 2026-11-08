# 🏥💜 Connections // C3e-D signed external floor challenge (synthetic)

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · release trust and externally authenticated release floors  
STAFF ROLE // Nurse 2 · NRS-2 · externally Hospital-compatible; not live registered  
ASSIGNMENT // C3e-D independent *signature provenance* of external floor statements  
BASE // `e468546b1e7df5a82b116284f1d0923acedb26e7`  
PERMISSIONS // GitHub-only branch, synthetic GPG keys, CI and docs. No desktop, real release keys, production activation, credential grants or PR merge

## IMPLEMENTATION

Merged C3e-C PR #1483 stores the last admitted release epoch/sequence in a crash-durable, private CI SQLite checkpoint. Its independent security audit (PR #1483 comment 6720291210) passed the narrow test but found the **external floor was not authenticated**: the caller could provide any syntactically valid numbers, and an old valid database can be restored.

C3e-D introduces a bounded, synthetic **challenge-bound signed floor statement** before calling C3e-C's unchanged SQLite admission code:

1. The verifier generates a fresh 256-bit challenge using `secrets.token_hex(32)`, rather than accepting a candidate-supplied nonce.
2. A test-only `request_proof(challenge)` callback simulates a **separate external authority** returning exact JSON bytes plus an OpenPGP detached signature. The callback is *not* a production network or IPC connection, and neither signing key is installed on the workstation.
3. The verifier checks the statement against a **separately supplied pre-pinned public signing key** in a fresh temporary GPG keyring, requiring a single valid `gpgv` signature from its exact fingerprint.
4. The signed statement binds a strict purpose/audience, release ID, synthetic node ID, release-signing root fingerprint, and the exact challenge. An old response cannot be replayed for a different challenge; a different node, purpose or signing-root context cannot reuse it.
5. The signed policy epoch and minimum release sequence are required to be positive actual integers; they are then passed as C3e-C's external floors. C3e-C still performs the existing **separate** root-signature/delegated manifest verification, database-root pinning, collision checks and monotonic SQLite transaction.
6. Tests generate four disposable identities (release-policy root, release signer, external-floor signer, adversarial signer) in isolated GPG homes. They verify actual detached signatures, malicious key swap, replay, signed bad scope, missing/unavailable authority, malformed floor data, changed signature, changed release policy, old but valid release refusal and ordinary SQLite release-state durability.

This branch adds only `tests/connections/c3e_release_trust/C3eExternalFloorProof.py`, its 15-case adversarial test, one new GitHub workflow and this recovery file. It does not modify C3e-A/B/C, C3d RPM, C4b Silverblue recovery, CPU++ production QML/JS, the signed-release installer, systemd, or real credentials.

## HOW TO USE

No workstation actions. GitHub workflow: `.github/workflows/connections-c3ed-signed-external-floor.yml`. The code is **not installed** into a production widget or service and the callback is a synthetic source injected by the test harness. All GPG material is destroyed with the runner's temporary directory.

## VERIFY

For the exact PR head:

- [ ] 15 C3e-D real GPG tests pass with independent key, challenge, node, root and purpose binding.
- [ ] Replaying a previously signed response to a second challenge is refused.
- [ ] Wrong key/public key, external anchor matching the release-policy root, changed signature, missing proof, zero/boolean floors are refused.
- [ ] An authorized signed statement advances C3e-C only after valid independently root-signed release admission.
- [ ] A genuinely signed but stale statement cannot bypass the higher **local** checkpoint.
- [ ] 16 C3e-C durable-floor, 18 C3e-A root/delegation and 6 C2n deny-only regression tests pass.
- [ ] Meta Apollo Grammar passes and changed files are limited to this independent seam.
- [ ] Independent technical/security audit and operator acceptance remain separate.

## WATCH OUT FOR

**A valid external signature authenticates the statement's signer, not the truth or freshness of that signer's backing state.** The test signer can sign arbitrary floor values and runs on the same disposable CI runner as the candidate. C3e-D is therefore only a cryptographic proof-of-mechanism. It does **not** establish an actual operator-owned external freshness authority, a TPM/remote service with independently protected monotonically increasing state, protected root enrollment/custody, enrollment/recovery ceremonies or a production communication transport. A compromised authority or a caller that can substitute the independently pinned key remains outside the test threat model. The authenticator's key fingerprint is still supplied by the test caller: it is **not** retrieved from a trusted OS-managed key store.

The 256-bit challenge is generated in the verifier process, and a signed response must match it; that prevents simple replay of recorded responses without granting the operator authority to the candidate. A malicious *legitimate* authority signing a stale floor can still misrepresent the current global state; the local durable floor may reject some downgrade attempts, but cannot recover erased history after a privileged database restore.

This pilot does not bind verified candidate bytes to actual immutable installation, does not attest running Python code, does not solve root-compromised machine backups, does not manage release-root rotation, and does not authorize user consent, provider network requests, NAS, Social/TASKS or production credentials. The C4b Silverblue recovery assignment remains separately owned and out of scope.

## CHECKLIST

- [x] Reacquire latest main, merged C3e-C, independent post-merge audit and C4b owner.
- [x] Isolate C3e-D to source-only signed external-floor proof and adversarial test fixture.
- [x] Add explicit deny-only assertions and synthetic GitHub GPG workflow.
- [ ] Verify exact-head CI and correct concrete failures.
- [ ] Independent source/security review, operator acceptance and merge.
- [ ] Later: decide operator-controlled root custody, TPM/remote external state, onboarding/rotation/recovery, protected identity and native release lifecycle.

## NEXT

Validate exact-head CI and preserve test evidence on the PR. Fix narrow defects without weakening signer isolation, nonce checking, root binding, or C3e-C monotonic state. Treat true operator-controlled external floor provisioning as a **separate design and authorization decision**, not a hidden implementation detail.

## DECISIONS

GitHub-only fake release trust experiment. No live Hospital registration, machine mutation, production services or keyring, user accounts, real API credentials, system package installation, C4b files, or merge by this report.
