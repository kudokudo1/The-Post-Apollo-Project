# 🏥💜 C4b Identity // Controller-Issued Fresh Challenge Against Actual Silverblue Gateway (CI Only)

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** C4b Identity Silverblue signed RPM and real installed-service lifecycle  
**STAFF ROLE:** External Hospital-compatible DOC successor; original C4b worker unavailable, operator explicitly reassigned continuing development  
**ASSIGNMENT:** Extend merged #2021 from guest-self-signed receipt key consistency to a **fresh controller-origin challenge** verified outside the real guest  
**OWNER:** C4b test harness and dedicated CI only; no C3e/Identity/C5 source changes  
**STATE:** Draft GitHub branch, review pending; **PRODUCTION HOLD**  
**HOSPITAL:** No verified live Hospital registration or in-app attachment

## IMPLEMENTATION

Merged [#2021](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2021) had 4/4 workflows green, including the real official offline Fedora 44 Silverblue KVM guest. It linked the actual guest signer public key to a test-only signed release **minted inside the guest**. That proved local consistency, but not a fresh external challenge or independent enrollment.

This phase adds a real **CI controller → read-only installer ISO → OSTree signed RPM / real systemd gateway → public signed denial → controller** path:

1. In `run_official_silverblue_identity.sh`, the separate Fedora-hosted test controller invokes a bounded Python helper to generate a cryptographically random 32-byte fresh nonce and store it in a private-on-runner 0600 file **before creating the ISO**. A copy of the **public nonce** is included in the offline seed. **No signing private key** is shipped.
2. The isolated `guest_identity_ostree_cycle.sh` validates the seed challenge and stages it at `/var/lib/postapollo-id-ci-assets/controller-challenge.txt` with root:root 0600. This survives the temporary OSTree install reboot but is deleted by the existing final `rm -rf "$store"` rollback cleanup.
3. The real `guest_identity_service_probe.sh` validates the exact root-owned nonce bytes, then sends this controller-origin nonce as the `clientNonce` of the real **BEGIN** request to the installed gateway. It validates the returned Ed25519 signature and `UNAVAILABLE` state against the actual signer used by the guest; the existing `SO_PEERCRED`, MainPID, kernel start, UID/GID, cgroup and SELinux origin checks remain active.
4. Only **public** data, the 32-byte runtime public key and the corresponding signed BEGIN denial frame, is exposed as one bounded `C4B_ID_CHALLENGE_PROOF` line on the offline QEMU UART. The existing sanitizer allowlists that one public proof, retaining independent provenance limits and no raw private key, argv or secret material.
5. **After** the existing required signed RPM / dedicated SELinux / four UNAVAILABLE actions / cleanup / two-boot rollback success markers, the controller verifies exactly one proof, canonical base64url, Ed25519 signature, exact BEGIN action, `UNAVAILABLE` state, no request ID, and exact fresh nonce from its own pre-ISO 0600 reference. It refuses replayed older receipts, substituted signers and duplicate proofs.
6. The host controller emits a distinct final fixed marker only after that verification. No production flags change and no authority is conveyed to QML.

The 24 new adversarial tests check genuine Ed25519 signed-denial handling, wrong host nonce, signed replay, wrong public signer, mutated signature/body/action, a signed non-denial, duplicate/missing proofs, controls, malformed base64, oversize data, wrong permissions/symlinked nonce path, and hard-false grants. Existing 25 runtime binding + 31 signed RPM + 7 Identity release regression cases remain in CI.

## HOW TO USE

The [dedicated fast CI workflow](../.github/workflows/connections-identity-silverblue-controller-challenge.yml) tests nonce/proof handling without a VM. The existing [real official Silverblue boot workflow](../.github/workflows/connections-identity-silverblue-real-boot.yml) runs the real KVM guest and is the ONLY source of actual installed-service evidence.

No local workstation commands or Quickshell restart are needed. The user and their live Fedora environment are not touched.

The challenge file and full serial data are deleted with disposable runner/container cleanup. The only uploaded marker artifact is bounded printable public diagnostic content, with short retention.

## VERIFY

- [ ] Exact-head **24** new controller challenge/proof adversarial tests pass.
- [ ] Existing C4b **25** runtime signer-binding and **31** signed RPM contract tests, plus Identity **7** release candidate tests, pass.
- [ ] Real signed RPM official Fedora 44 Silverblue VM reaches original two reboots and rollback, emits exactly one bounded proof, and host controller verifies the original nonce against the real BEGIN denial.
- [ ] Grammar and relevant GitHub checks pass.
- [ ] Independent Nurse 2 source and security review with operator-controlled merge acceptance.

## WATCH OUT FOR

**This is a genuine external challenge, but not genuine external host trust.** The controller chooses the nonce outside the guest and verifies the response outside the guest. However, **the guest sends its own, un-enrolled receipt public key** in its proof. A hostile guest could substitute another key, sign a valid denial, and still satisfy signature and nonce freshness if no separately enrolled key is pinned. The same risk applies to guest-authored kernel or SELinux status markers. This work measures real installed-service behavior in a controlled CI environment, not independent kernel attestation or proof of actual production operator enrollment.

No external HSM/trusted root, protected one-use issuer, external rollback-resistant release floor, authenticated logind seat, C5 human consent or real Identity sign-in is provided. Signed `BEGIN` still returns **UNAVAILABLE** and never starts login.

Do not use the CI proof or public key for production pairing or credentials. A production release or witness root must be explicitly enrolled and controlled separately, with challenge issuer custody and process/seat provenance independently trusted by C3e and Identity.

## CHECKLIST

- [x] Recheck #2021 merge, current main and C4b ownership; follow Syntagma AGENTS + Hospital authority protocol.
- [x] Add real controller nonce issuance, guest staging, native signed denial capture and separate host verifier.
- [x] Keep all keys in original guest scope, send only public frame/key, retain signed RPM / SELinux / rollback gates.
- [x] Add malicious replay, substitution and malformed evidence regression tests.
- [ ] Verify fast CI and real KVM exact PR head; fix only evidenced failures.
- [ ] Independent review and operator merge authorization.
- [ ] Separate external operator root enrollment, issuer ledger, host attestation and C5 approval (not in this PR).

## NEXT

Verify the actual real-Silverblue challenge cycle and hand off the proof **format**, not authority, to protected C3e. The subsequent cross-owner assignment is to pin and enroll the runtime public key under a separately protected controller/witness root with rotation, revocation and secure-boot/process origin constraints. That requires a separate operator trust-bootstrap decision.

## DECISIONS

CI-only scope. No workstation writes, permanent keys, production login, provider access, C3e/Identity/C5 modifications, merge, credential action or claim of live Hospital registration.
