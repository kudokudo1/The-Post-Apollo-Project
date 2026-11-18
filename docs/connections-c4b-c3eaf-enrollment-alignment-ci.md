# 🏥💜 C4b // Controller Policy ↔ Protected C3e-AF Signed Role Alignment (CI Only)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Connections · C4b Silverblue gateway / independently pinned controller evidence  
**STAFF ROLE:** External Hospital-compatible DOC successor with operator-authorized C4b continuation; live Hospital attachment unverified  
**ASSIGNMENT:** Compose C4b's externally controller-supplied, signed receipt-key enrollment with existing protected C3e-AF role enrollment without editing C3e-owned source  
**BRANCH STACK:** based on draft [C4b #2044](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2044). Never merge this stack before parent and independent review.  
**PRODUCTION:** HOLD. No real independent root custody or sign-in.

## IMPLEMENTATION

[PR #2038](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2038) merged with a complete passing official Fedora 44 Silverblue signed RPM / enforcing SELinux / two-reboot rollback regression. Its controller can verify the real native gateway's signed fresh BEGIN/UNAVAILABLE denial. The guest still supplies its own receipt public key, so this alone is *not* an independently authorized installed host.

The draft [C4b #2044](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2044) reads an allowlisted caller-selected controller policy bundle from owner-only files, then verifies a controller-root-signed C4b enrollment bound to host ID, receipt key and minimum release. It **does not prove** who set those controller files.

The merged [C3e-AF role enrollment](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1996) separately verifies a root-signed record binding **release root, witness key, receipt signer, host ID, release epoch and sequence, and exact canonical expected runtime snapshot hash**, before C3e-Z's root-local one-use CI challenge. The C3e signature root is again an externally provided test fixture, *not* an authorized operator key.

This C4b-owned component `c4b_c3eaf_enrollment_alignment_ci.py` composes those existing unchanged verifiers:

1. Read C4b's controller-owned policy bundle; validate its Ed25519 signed enrollment, guest denial signature, fresh controller nonce, host, source digest, minimum release version and revocations.
2. Read the **verified C4b host ID, release epoch/sequence and actual receipt-key hash** from the validated C4b enrollment. These can no longer be chosen by the C3e enrollment or by UART.
3. Validate the **separately caller-pinned C3e-AF role signature** against that exact host/version and the separately caller-supplied complete C3e-X runtime snapshot. C3e's existing role, canonical fields, public-key role separation, snapshot hash and Ed25519 signature checks remain authoritative for their CI scope.
4. Refuse unless the C3e enrolled **receipt public key is byte-identical by SHA-256** to the signer already validated by C4b. A valid C3e certificate for another host/version/key fails. The C4b root must differ from C3e enrollment root and all C3e consumer role keys.
5. Return only evidence-of-CI-consistency flags, with every production, host, C5/consent, permissions, external revocation/rollback and root-custody flag hard FALSE.

**Important source distinction:** C4b's `releaseSha256` and C3e-X's `rpmSha256` / full snapshot digest are **different schema claims**. This composition DOES NOT assume they identify identical bytes or the same installed artifact. `crossReleaseArtifactDigestAuthenticated` remains **FALSE** until an operator-approved signed mapping and independent installed-host measurements are implemented.

The C3e one-use ledger is not consumed by this *pre-admission* cross-check. Later issuer/seat evidence must still be verified by C3e and C5. This component has no network connection, writes, trust-root key generation, live host-service invocation or credential access.

## HOW TO USE

One dedicated fast workflow: `.github/workflows/connections-c4b-c3eaf-enrollment-alignment-ci.yml`.

The workflow exercises 26 cross-enrollment cases, existing 28 controller-policy, 35 signed enrollment, 28 nonce/UART, 25 receipt binding and C3e-AF suites. All signing roots in tests are synthetic disposable runner keys. The cross-check requires a distinct **controller-selected** C3e root public key and expected C3e runtime snapshot; neither may be supplied by the guest's proof line. A real protected authority cannot be inferred from successful CI.

No changes to your desktop or production Connections UI.

## VERIFY

- [ ] 26 new correct/mismatched dual-signed enrollment, host, signer, version, root alias, replay and false-grant cases PASS
- [ ] Existing C4b policy, signed enrollment and native receipt regressions PASS
- [ ] Existing unmodified C3e-AF role enrollment and one-use challenge tests PASS
- [ ] Applicable real Silverblue workflow PASS at exact commit, if triggered
- [ ] Independent Nurse 2 review; operator acceptance of parent #2044 and this stacked PR

## WATCH OUT FOR

A synthetic controller file and a signature by another synthetic key are still **not** real operator-approved authority. This code is a diagnostic pre-admission bridge and must not be used to label a host authenticated. C4b policy directory metadata does not prevent privileged local tampering, and C3e's expected runtime snapshot is CI caller-supplied instead of independently authenticated kernel/seat evidence.

**Trust-bootstrap decisions still required:** identify who owns the real enrollment signing root, where the private key is protected, how it is independently installed/rotated/revoked, which device/host/seat identity is authoritative, how protected issuer challenge and non-rollback floors are managed, and how C5 one-use operator consent is obtained. None has been invented or activated here.

## CHECKLIST

- [x] Verify #2044 official KVM 4/4 PASS; independent review still pending
- [x] Inspect current C3e-AF, C3e-Z/X/Y, C4b policy intake and Syntagma ownership rules
- [x] Add only C4b-owned read-only cross-enrollment comparator
- [x] Preserve all C3e code and production settings unchanged
- [x] Add 26 adversarial cross-enrollment test fixtures and dedicated CI
- [ ] Exact-head tests / independent security review / operator acceptance
- [ ] Actual protected enrollment authority and cross-release/host witness implementation requires separate approved scope

## NEXT

Complete exact-head CI and any verified fixes. Request independent review, then coordinate with the current C3e owner on the canonical trusted issuer/installed-host evidence contract. Do **not** interpret a successful CI root key signature as the missing real key custody decision.

## DECISIONS

No auto-merge, production key creation, local PC writes, C3e/Identity/C5 changes, login/credentials or real Hospital registration claims.
