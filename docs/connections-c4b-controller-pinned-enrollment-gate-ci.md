# 🏥💜 C4b Identity // Controller-Pinned Receipt Enrollment Gate (CI Only)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** C4b signed Silverblue Identity gateway / controller trust boundary  
**STAFF ROLE:** External Hospital-compatible DOC successor under operator-authorized continuation; live Hospital registration not verified  
**ASSIGNMENT:** Refuse guest-supplied receipt public keys as host identity without a separately signed, pinned controller enrollment  
**SCOPE:** Additive C4b-owned verification contract, adversarial suite, CI workflow and reference documentation only  
**STATUS:** Draft, unmerged, production trust HOLD

## IMPLEMENTATION

Earlier [#2025](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2025) **merged with 5/5 workflows passed** on the real official Fedora Silverblue signed RPM, enforcing SELinux, four `UNAVAILABLE` receipts, controller-issued fresh nonce and two-boot rollback. It introduced actual external **challenge freshness**, but the guest included its own receipt **public key** in the UART proof. A malicious guest can sign a plausible answer with a newly generated unrelated key. The last step of verification cannot decide that such a key was previously approved.

This new `controller_pinned_enrollment_gate_ci.py` is a read-only **deny-only contract**, intentionally not wired into production. It accepts:

- A strictly canonical Ed25519 **controller-root-signed** purpose/role-scoped enrollment certificate with an exact package, unit, audience, diagnostic-only scope, 128-bit enrollment ID, C3e-compatible signed host ID, signed release SHA-256, release epoch/sequence, and the SHA-256 of the **exact gateway receipt public key**.
- A separately pinned controller **public root key**, never taken from the guest proof.
- A separately pinned C3e-compatible host identity, signed release digest and minimum release epoch/sequence, never from UART.
- An exact externally supplied revocation-ID snapshot. Empty snapshots work **only in synthetic CI**; the function cannot prove a live operator-approved revocation ledger is present.
- One actual signed `BEGIN` **UNAVAILABLE** receipt containing the controller's fresh nonce and a public key supplied by the guest.

It verifies the role/scope/schema first, a canonical byte-level Ed25519 enrollment signature against the independently supplied root, an exact release digest and version floor, and revocation. Only then does it compare the public key **from the guest** against the **controller-signed receipt key hash**. It rejects a swapped or forged guest key even when the impostor produces an otherwise genuine Ed25519 signature over the correct fresh nonce. It then reuses the already merged challenge verifier to inspect the signature, action, nonce, and denial. The root and signer must be different keys.

### Key distinction

The unit tests generate separate, short-lived signing keys in the GitHub runner **only to exercise the contract**. They do not enroll any actual Silverblue host, publish or rotate a protected key, maintain a trust ledger, or authenticate a remotely observed Linux process. The previous C4b VM still uses its self-generated ephemeral key and reports **diagnostics only**. It would and should fail this new enrollment gate if its guest key were submitted without a separately approved controller enrollment.

## HOW TO USE

Dedicated fast CI: `.github/workflows/connections-identity-silverblue-controller-enrollment.yml`. It executes 35 adversarial enrollment/signature/release/revocation/cross-host/guest-substitution cases, plus the previous C4b challenge, receipt binding and Identity release regressions.

The existing real Fedora KVM signed-RPM workflow remains unchanged; it does **not** pretend an operator root exists. No production QML, broker, native service, sign-in or C5 files are modified.

## VERIFY

- [ ] 35 new synthetic independent-root enrollment and cross-host refusal tests on exact PR head
- [ ] 24 existing controller challenge tests, 25 runtime key binding tests, 7 Identity release tests
- [ ] Applicable C4b real Silverblue regression, signed RPM source and Grammar workflows
- [ ] Independent NRS-2 review of role/domain/key separation, revocation source and guest substitution
- [ ] Operator review/merge approval

## WATCH OUT FOR

**This is a software contract, not proof of trust-root custody.** A verified signature establishes that *some holder* of the supplied root's private key signed this record. It does not establish that the root was independently enrolled, securely stored, authorized by an operator, protected against replacement or sufficiently rollback-resistant. The source digest and floor must also arrive through separately authenticated controller channels. No use of a CI fixture should turn on host authentication.

The legitimate certificate signature and correct runtime receipt key are necessary, not sufficient, conditions for actual host authorization. A trusted host must also demonstrate independently authenticated process/seat/installed image and enforce one-use C5 consent.

All `hostAuthenticated`, `canBeginSignIn`, `credentialActionsEnabled`, `productionAuthority` and related flags are **FALSE** in every result.

## CHECKLIST

- [x] Read Syntagma AGENTS, Hospital continuity and permissions; confirm merged #2025, existing C4b owner and current GitHub main.
- [x] Add a separate controller-pinned certificate verifier, not trusting guest-supplied keys as enrollment.
- [x] Reject signed forged guest key, unexpected role or host ID, rollback, revoked enrollment, wrong release and replayed nonce.
- [x] Add exact-head CI and standalone recovery/documentation contract.
- [ ] CI verification and independent review
- [ ] Actual operator-enrolled root custody/rotation/revocation, external floor, installed host attestation, C3e/Identity/C5 integration

## NEXT

Finish exact-head tests and independent security review. The **next major implementation** requires an operator-approved external signing-root enrollment and revocation/rollback ledger, plus an independently authenticated installed-host/seat binding delivered to protected C3e. Do not generate production keys automatically or reclassify a GitHub key pair as independently protected.

## DECISIONS

No private key export, local Fedora writes, actual production root enrollment, production sign-in or credentials, cross-owner changes, automatic merge or live Hospital registration claim.
