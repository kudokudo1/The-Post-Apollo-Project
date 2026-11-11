# 🏥💜 Connections C3e-Y // Signed complete Identity CI host record and one-use challenge

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · protected C3e evidence and replay
STAFF ROLE // DOC · existing protected Connections development owner
ASSIGNMENT // Full-record signature and separately issued one-use challenge, CI-only denial contract
CONCURRENT OWNERS // C4b Silverblue, Identity DOC, C5 human consent, separate C4d guest observer
PRODUCTION // HOLD

## IMPLEMENTATION

C3e-X #1846 is independently reviewed and merged on main. It checks four genuine Ed25519 UNAVAILABLE receipts against four sets of caller-provided synthetic kernel/process snapshots. The existing Identity receipts cryptographically cover command/action/nonce/state but **do not sign the full runtime snapshots**. C3e-X also refuses duplicate nonces only within one bundle.

C3e-Y is a bounded separate CI-only composition with FOUR new owned files: C3eYSignedHostChallenge.py, twenty-seven adversarial tests, a dedicated workflow and this contract. It does not change C3e-X, C3e-Q/R/U/V/W, C4b/Identity/C5 sources, Quickshell or production settings.

1. The disposable GitHub runner explicitly creates a root-owned mode-0700 directory directly under /run, with a mode-0600 SQLite file. The independent CI issuer (not the simulated guest signer) creates 32 random challenge bytes, records only their SHA-256 as ISSUED along with fixed purpose/audience and test release epoch/sequence, and commits to disk BEFORE exposing the challenge. Receiver calls must never bootstrap missing ledger state.
**C3e-AA hardening after C3e-Y merge:** The root-local issuer now stores a monotonic lexicographic `(releaseEpoch, releaseSequence)` floor in the same SQLite transaction as each newly issued challenge. An older release cannot receive another challenge, and a previously issued challenge is refused if a newer release became current before consumption. The conditional consume transaction rechecks the floor to close the issuance/verification race. A new CI-only ledger schema v2 deliberately refuses v1 fixtures rather than silently migrating or creating state. Higher epochs may begin with a lower sequence; no version downgrade within the same root-local ledger is allowed. This is not an external anti-rollback authority because an administrator may restore an older entire database or replace the issuer itself.

2. The simulated witness signs a canonical bounded JSON *statement* using a **distinct Ed25519 witness key**, domain-separated and purpose-bound to the exact deny-only Identity role/audience and fixed release test epoch and sequence. The statement binds the SHA-256 of the **complete canonical C3e-X four-snapshot evidence bytes**, all four signed Identity receipt-frame SHA-256 values in exact order, caller-expected snapshot bytes digest, independently supplied receipt public key hash, and SHA-256 of the preissued challenge. The evidence/receipt content is not merely a textual name; altering even one byte changes a signed hash.
3. The verifier requires a caller-pinned witness public key that differs from the separately caller-pinned Identity receipt key. It verifies the full-record signature and EVERY hash/action/audience/epoch/sequence/challenge binding. Then it calls the unchanged C3e-X checker, which verifies the existing four **real Ed25519-signed** UNAVAILABLE denial receipts and the consistency of all PID/start/UID/GID, process/exe/RPM digests, exact unit, cgroup, socket peer, proposed SELinux CI label and bundle nonces. Any mismatch REFUSES before challenge consumption.
4. Before C3e-X rechecks the evidence, the receiver freezes the caller's mutable receipt list into an immutable tuple and copies the caller-supplied expected pins. A caller cannot substitute a different valid-looking frame or kernel snapshot between signed-digest validation and denial consistency checking. Both validated byte sets remain synthetic CI inputs.

Only after all checks pass does the root-private test ledger conditionally and atomically transition the challenge from ISSUED to CONSUMED and retain the digest of the verified signed statement. The update checks challenge, audience, epoch, sequence and prior state; duplicate threads and new verifier instances cannot consume it again. A failed signature or false process snapshot preserves ISSUED state for a valid retry.
5. The only three positive outputs are explicitly suffixed InCI or RootLocalCI. All external issuer custody, rollback resistance, independent host origin, signed guest admission, C5 consent, sign-in, credential, approval and production fields remain **false**.

## HOW TO USE

Inspect the dedicated GitHub Actions workflow connections-c3ey-signed-host-challenge.yml on the C3e-Y draft PR. It runs in a disposable Ubuntu GitHub runner. The root CI step alone creates /run/c3ey-ci-* SQLite fixtures; an ordinary user invocation deliberately REFUSES. Other checks run earlier C3e-X 15-test regression and the existing C2n hard-negative policy tests.

This is a **synthetic, deny-only** witness-protocol test, not a native daemon. Do not install the module on a workstation or use the results to grant a real Identity command or TimeW vault permission. The C4b worker still owns actual Fedora Silverblue kernel/systemd/SELinux process observation and its authenticated transfer. The C3e-Y statement is currently signed by a disposable key in test code, NOT a separately enrolled real host/source attestor.

## VERIFY

- [ ] Exact-head C3e-Y 27 adversarial tests PASS on disposable CI root.
- [ ] Existing C3e-X 15/15 and C2n regression PASS.
- [ ] GitHub Grammar and any triggered existing root/release/signed RPM workflows PASS.
- [ ] Independent Nurse 2 exact-head security review before authorized owner merge.

Adversarial coverage: monotonic release-floor downgrade and race refusal, superseded outstanding challenges, missing/tampered floor metadata, unknown/replayed externally issued test challenge, incorrect witness/receipt key, identical key roles, tampered unsigned snapshot before/after signing, reconstructed signature over a forged snapshot still refused by C3e-X, wrong action/receipt or replaced signing instance, changed audience/purpose/release floor, wrong statement hashes, noncanonical/duplicate JSON, changed command nonce, concurrent single-use consumption, absent/unsafe/symlinked ledger, malformed epoch types and disabled host/credential authority.

## WATCH OUT FOR

**The signature binds the complete claimed record, not the truth of its provenance.** A synthetically generated witness can sign fabricated process snapshots. A public-key argument called independently_pinned_witness_key does not prove it came from a separately enrolled and protected hardware/OS authority. Similarly, the caller-provided expected installed RPM/exe digests and SELinux labels are not independently authenticated kernel measurements. These inputs are trusted CI fixtures ONLY. The receipt-key role is separate, but both fixture keys can still be minted under the same disposable test runner.

**The durable CI ledger is not externally rollback-resistant.** The test issuer and verifier share a root-local disposable /run SQLite DB. Its transaction survives process restart and allows exactly one consumption within that DB state, but a privileged actor can restore the DB from backup. It has no external monitored root, approved clock/expiry authority, key revocation, authenticated process-source channel or logind seat. Do not confuse an issued challenge from this *separate CI issuer* with actual production independent issuer custody. A successful consumed record is not human intent, permission or host authentication.

The actual signed host witness needs a separate independently protected producer that measures the official installed RPM, signed release-root/receipt-key lineage, exact kernel PID/start/UID/GID/cgroup/SELinux/executable and active unlocked logind seat and signs those measurements together with broker-issued fresh challenge and audience. C4b owner must prove host loss/replacement and dedicated SELinux negative policy tests; C3e independently reviews the authenticator and external nonce custody; C5 alone owns per-action human approval. No enrolled keys, credentials, host privilege, provider sign-in or production activation are part of this CI milestone.

## CHECKLIST

- [x] Recheck AGENTS, Hospital protocols, current C3e-X merge, main and ownership.
- [x] Add a new DOC-owned purpose-specific complete-record signed witness receiver with root-local preissued challenge.
- [x] Add 21 root-isolated adversarial tests and dedicated workflow.
- [ ] Verify exact-head CI, any requested changes and Nurse 2 independent security review.
- [ ] Owner merge after all review gates under existing authorization; final operator acceptance separate.
- [ ] C4b independently authenticated real release/source/process/seat witness and C3e external challenge custody.
- [ ] C5 user consent, Identity native production approval and operator authorization after further review.

## NEXT

After exact-head CI and NRS-2 review, reconcile an owner-authorized C3e-Y merge. Next actual protected C3e implementation should bind a genuine independently authenticated host-source and external rollback-resistant challenge authority to this full-record signed format, then separately confirm C5 one-use user intent. Preserve all negative auth flags until that complete production review.

## DECISIONS

No C4b, C4d, Identity, C5, TimeW, QML, workstation or production files changed; no live Hospital registration assumed. This is a repo-only protected C3e DOC lane change, initially draft for review. C3e-X and old R ledger remain unchanged. Key custody and production sign-in remain HOLD. Operator retains final acceptance.
