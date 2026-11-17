# 🏥💜 C4b Identity // Actual Guest Runtime Receipt-Key Binding (CI Only)

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** C4b Identity Silverblue signed RPM + installed service lifecycle  
**ASSIGNMENT:** Successor DOC following operator's explicit authorization to take over unavailable C4b worker  
**HOSPITAL:** External Hospital-compatible; no verified live registration or session attachment  
**OWNERSHIP:** Existing C4b `tests/connections/identity_silverblue/**`, new dedicated C4b workflow, this documentation. No C3e/Identity/C5 source changes  
**PRODUCTION:** HOLD

## IMPLEMENTATION

C4b #1785 already passes an actual offline Fedora 44 official Silverblue VM install, protected signed RPM, enforcing SELinux, isolated native gateway with four Ed25519-signed `UNAVAILABLE` receipts, network confinement, teardown and two-boot rollback. C3e-AH #2014 additionally verifies signed source manifest plus a real Linux process on an **Ubuntu fixture**, but had not been run on C4b's actual guest.

A genuine key-custody mismatch remains in the separate existing CI contracts:

- `release_manifest_ci.py` creates a random **controller-side** receipt public key fingerprint in a synthetic release manifest. It does not ship that receipt private key to the guest.
- `guest_identity_service_probe.sh` deliberately creates a **different** short-lived Ed25519 signing seed at `/run/postapollo-identity-silverblue-ci-only/signer.ed25519`. Its real installed gateway signs four UNAVAILABLE receipts under this guest-local private seed.
- Before this phase, the real guest verifies each signed receipt against its own runtime signer, but does **not** sign and check the exact source-manifest fingerprint of this runtime key.

**This phase changes only the disposable guest test:**

1. A new isolated Python verifier, `runtime_receipt_binding_ci.py`, checks that a canonical purpose-bound Ed25519-signed **CI release manifest** identifies the same raw 32-byte runtime public key used to verify the actual service's four denial receipts.
2. The full manifest still requires the exact C4b nine-file source roster, package name, unit, RPM archive SHA-256, epochs and sequence, using the unchanged Identity `silverblue_release_candidate_v1.py` verifier.
3. After real `SO_PEERCRED` PID/UID/GID, process start, cgroup and SELinux continuity checks and **all four** live gateway denial signatures pass, the guest verifies the installed file bytes and RPM archive. It mints an **in-memory, guest-local test-only release-root key** and signs the manifest with the actual runtime receipt public key fingerprint.
4. It checks the signed release against that same public key, then **intentionally substitutes a different ephemeral key**. The substitution must fail or the entire real guest test fails. The host controller also requires one exact positive marker and one exact substitution-refusal marker before counting the test's final rollback as successful.
5. The guest receipt private seed remains inside the ephemeral `/run` filesystem, chmod 0600, is not exported to UART, RPM, GitHub artifacts, the isolated release verifier, or the ISO seed. The new release-root private key exists only in memory in the guest-side verifier process and is destroyed when that process exits.
6. The old signed-RPM, rollback, SELinux, deny-only service and cleanup paths remain mandatory and unmodified in purpose.

**Important:** The new release signing root is **created by the guest being measured**. This is a real installed-guest cryptographic wiring proof, NOT independent external admission, host identity or revocation authority. It does not make the original controller-generated fixture receipt key correspond to the guest key. Actual independently issued, operator-enrolled release-to-service receipt binding remains a separate task.

## HOW TO USE

The dedicated fast GitHub workflow is `.github/workflows/connections-identity-silverblue-receipt-binding.yml`. It runs adversarial synthetic source/key tests and the existing Identity Silverblue source contract.

The **real** Fedora/KVM boot is the existing `.github/workflows/connections-identity-silverblue-real-boot.yml`, automatically triggered by changes to the C4b sources. It now requires, in addition to its prior stage/rollback markers:

- `C4B_ID_PASS // GUEST_LOCAL_RELEASE_BOUND_TO_ACTUAL_GATEWAY_RECEIPT_KEY`
- `C4B_ID_PASS // SUBSTITUTE_RECEIPT_PUBLIC_KEY_EXPLICITLY_REFUSED`

Both must occur **while the actual service is running, after four verified signed UNAVAILABLE receipts and before cleanup/rollback**. No new systemd service, persistent key, guest Internet access or user PC action is required.

## VERIFY

- [ ] At exact PR commit: 25 new release/root/receipt substitution, frame, role, floor, source-pin and no-authority tests PASS
- [ ] Existing C4b signed RPM source contract and Identity release tests PASS
- [ ] Existing official disposable Fedora Silverblue real-KVM boot/rollback with the **two new exact marker requirements** PASS
- [ ] Existing Grammar and other applicable CI checks PASS
- [ ] Independent Nurse 2 review of key custody, verifier import path, guest scope, negative substitution check, isolation and rollback; operator-controlled merge/acceptance

## WATCH OUT FOR

No source-root, runtime public key, receipt body or startup process is independently authenticated **outside** the offline guest. The guest itself constructs its own signed release, and a privileged guest adversary can supply other local expected values, replace its release-root key or forge a guest-local witness. The original controller-side synthetic release's `receiptKeySha256` is still separate from the guest signer; this change verifies that the real installed service can be bound to a fresh in-guest signed release **without exporting its private signer**. A future independently trusted controller must enroll/approve that runtime public key with its own separate private root and fresh challenge protocol.

Signed release does not automatically authenticate the running native binary, loaded Python code, Linux host, user seat, externally protected release floor or C5 human consent. The signed denial receipts remain `UNAVAILABLE`; they never authorize `BEGIN`, `CANCEL`, `RECOVER`, credential access or sign-in. All `hostAuthenticated`, external issuer/custody, sign-in, consent, credential and production fields remain FALSE.

The real KVM test must finish before any claim of official guest PASS. Unit CI cannot substitute for this.

## CHECKLIST

- [x] Inspect canonical Syntagma `AGENTS.md`, Hospital and permission rules; verify C4b merge #1785, C3e-AH merge #2014 and issue #2018
- [x] Explicit operator-authorized successor takes C4b implementation; previous C3e ownership retained by its room
- [x] Preserve guest key generation and actual four runtime signer receipts
- [x] Add independent C4b runtime public-key mismatch checker and fast adversarial suite
- [x] Stage read-only verifier code inside official test-only Silverblue seed and require real guest pass/refusal evidence
- [ ] Run exact-head fast and KVM CI; fix any verified failure
- [ ] Nurse 2 review and operator merge decision
- [ ] External release/witness root custody and C5 consent remain out of scope, must not silently activate

## NEXT

Complete exact-head CI and real guest verification. The next **separate** interface milestone is to produce a challenge-bound public-key and signed real process observation from the genuine installed guest, enroll that public key under an independently controlled release/witness root outside the guest, and verify it from protected C3e. Coordinate with Identity consumer and C5 human consent owners. Require operator approval for trust bootstrap, root rotation/revocation, privileged workstation mutations, and any production activation.

## DECISIONS

No automatic merge, live deployment, local PC/Quickshell modification, provider access, credentials, production keys, native login activation or assertion of Hospital registration. All modifications remain on an isolated C4b successor branch.
