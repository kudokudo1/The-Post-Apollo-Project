# 🏥💜 Universal Connections // Protected operator witness enrollment preflight

PATIENT // `The-Post-Apollo-Project`  
ROOM // Universal Connections · protected C3e/Identity witness integration  
STAFF ROLE // DOC · explicitly reassigned by operator 2026-11-19; live Hospital registration not verified  
ASSIGNMENT // Independent signer-enrollment contract, **Phase 1: format and deny-only verifier**  
CONCURRENT WORK // Prior C3e/Identity worker PAUSED; C4b accepted and source frozen; C5, PX and CPU++ remain separate owners  
BASE // `f8c4f9d0c6d394b9746fba20f5ffa13d8442919b`  
PRODUCTION // HOLD · no live keys, trust enrollment, native service, credentials or sign-in

## IMPLEMENTATION

This small additive package **reuses the merged protected C3e-AF signed key-role enrollment verifier**. It does not create a competing enrollment document format, modify C3e-AF / C3e-Z, change C4b's already-accepted integration or implement a production signer.

The new `C3eOperatorWitnessEnrollmentPreflight.py` is a strict CI-only **read-only preflight**. It requires:

1. **Explicit, separately supplied Ed25519 enrollment-root fingerprint.** SHA-256 of the public key must exactly match this input; the key is never learned from the candidate enrollment or an adjacent artifact. The fingerprint's *source* is not authenticated by this module.
2. **A C3e-AF domain-separated, canonical, root-signed role enrollment.** Existing C3e-AF validates exact host scope, release epoch/sequence, the entire expected runtime snapshot digest, and four separated identities: enrollment root, release root, witness signer, receipt signer. The preflight calls this existing verifier unchanged.
3. **A caller-supplied external minimum release floor**, as a positive pair of epoch/sequence values. An enrolled release below the provided floor refuses. The floor is not independently stored or rollback-resistant here.
4. **Caller-supplied revoked root and role SHA-256 rosters.** Strict ascending unique lowercase 64-character hashes are required. Any revoked enrollment root, release root, witness key or receipt key refuses. These rosters are *not* cryptographically vouched for by an actual external owner here.
5. **No state mutation or authority grant.** A successful preflight returns only a format-compatible diagnostic, public role fingerprints and every `operatorEnrollmentRootCustodyVerified`, `independentWitnessSigningKeyCustodyVerified`, `independentReleaseFloorCustodyVerified`, `externalChallengeIssuerVerified`, `externalRollbackResistanceVerified`, `realInstalledHostAuthenticated`, `authenticatedActiveSeatVerified`, `c5HumanConsentVerified`, `hostAuthenticated`, `canApprove`, `canBeginSignIn`, `credentialActionsEnabled`, `productionAuthority` fixed to **false**.

The new 22-case adversarial test suite uses temporary Ed25519 identities and the existing C3e-AF/C3e-Z disposable fixtures. It verifies root-pin substitution, revoked keys across all roles, duplicated/noncanonical revocation lists, stale floors, wrong host, forged enrollment signatures, unsigned key replacement, extra authority fields, role aliasing, changed runtime snapshot, and the fact that the preflight **does not issue or consume** a one-use challenge.

## HOW TO USE

This is a GitHub-source and CI-only contract. The source is not imported by a production daemon, QML, browser identity adapter or protected key store. There are no manual workstation commands or activation steps.

Workflow: `.github/workflows/connections-c3e-operator-witness-enrollment-preflight.yml` runs the 22 new tests and unchanged C3e-AF/C3e-Z regression suites in a disposable Ubuntu GitHub runner with a pinned test-only cryptography dependency. No private signing key is added to an RPM or GitHub artifact.

## VERIFY

- [ ] Exact-head workflow completes the 22 new adversarial cases
- [ ] Exact-head existing C3e-AF/C3e-Z regressions pass
- [ ] Grammar and any other triggered checks pass
- [ ] Independent NRS-2 exact-head source/security review
- [ ] Separate operator decision on merge; no automatic merge

## WATCH OUT FOR

**Signing a record does not prove who controls the signer.** The current test root, the expected public-root fingerprint, release floor and revoked-key rosters are all **supplied by one disposable CI harness**. Even when they match, a malicious caller choosing its own root and signed enrollment can produce a positive *test-only format* result. It is not independent real-world enrollment.

**The actual Silverblue guest-local receipt-key binding already passes.** Existing C4b `runtime_receipt_binding_ci.py` measures the running guest's four signed UNAVAILABLE receipts, creates a guest-local signed test release with that runtime public key and rejects substitution. The official Fedora two-reboot CI completed successfully. Its root was minted inside the guest, not independently enrolled. Do not rebuild this accepted C4b feature.

**No challenge custody or hardware/OS origin transfer has occurred.** Existing C3e-Y and C3e-R use root-local disposable SQLite state that an administrator can roll back. C3e-AF's expected process snapshot is supplied by the test caller. This new preflight neither persists a trusted floor nor proves actual installed host, active logind seat or C5 human approval. A later production service needs a separate operator-approved trusted key store/issuer, authenticated signer enrollment and revocation, externally durable one-use challenge/floor history, live native host/seat measurements, and independently reviewed consent.

## CHECKLIST

- [x] Operator explicitly reassigns this chat to protected C3e/Identity witness integration
- [x] Restore Syntagma rules and existing GitHub ownership/recovery checkpoint
- [x] Reuse C3e-AF signed role schema rather than minting another one
- [x] Isolate the source preflight, adverse tests, workflow and this contract in a new draft branch
- [ ] Exact-head CI and independent review
- [ ] Operator accepts and separately authorizes merge, if appropriate
- [ ] Operator names real enrollment custodian and independently anchored root, key revocation/rotation/recovery and history storage
- [ ] Implement reviewed owner-controlled key custody + native witness interface **only after** that authority is established
- [ ] C5 protected operator consent and PX writer integration remain separate

## NEXT

Complete the scoped source/CI review gate. The next *actual trust implementation* must first identify who controls the real enrollment key, where its public fingerprint is pinned outside the candidate's control, how a revoked key and rollback floor survive compromise/recovery, and which independently authenticated process signs a fresh actual Silverblue host/seat observation. **Do not use a caller-supplied positive `testOnly` result as authorization.**

## DECISIONS

This is a bounded Phase 1 implementation under the operator's new C3e/Identity assignment, not authorization to restart the previous worker, transfer C4b/C5/PX ownership, provision private keys, install native services, merge a PR or activate sign-in. Live Hospital Room/Session registration remains unverified.
