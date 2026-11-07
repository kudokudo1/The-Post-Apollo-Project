# 🏥💜 Universal Connections // C4a signed fake status RPM on Silverblue

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Universal Connections · C4a Silverblue Signed-Service Integration
STAFF ROLE // DOC, external Hospital-compatible; no live registration verified
ASSIGNMENT // Bridge accepted C2z two-reboot recovery with already merged C3d signed fake status-service RPM
SCOPE // GitHub-only disposable Fedora 44 CI, no production service/users/keys/permissions
OWNER BOUNDARY // Reuse C3d builder and spec without modifying Nurse 2's owned files. Preserve C2v/C2x baseline behavior.

## IMPLEMENTATION

C2z proved real Silverblue OSTree install, reboot, rollback and second reboot using inert C2t. C3d proved native signed fake-service RPM provenance, file verification and service-origin checks in mutable Fedora Cloud. Neither separately proved that a signed fake-service RPM is present after a real **Silverblue** reboot and absent after rollback.

C4a adds an **explicit opt-in** to the C2v test harness. Only the dedicated C4a GitHub job supplies C4A_SERVICE_RPM_DIR, staging the C3d signed RPM and temporary public test signer alongside the original C2t fixture on the read-only seed ISO. Without the opt-in marker, C2v/C2x still layer only C2t.

1. The guest verifies the exact three service payload paths, no scriptlets/triggers, artifact SHA-256s, and native OpenPGP signature refusal before importing the test signer. It accepts the signature only after importing that public signer into a separate writable /var test RPM keyring, never the immutable booted system RPM trust store.
2. The existing detached rpm-ostree worker layers **both** local RPMs in one transaction. The independent monitor requires **both exact package names** in the same pending OSTree deployment and an idle transaction before authorizing reboot.
3. The first actual reboot must boot both RPMs. C4a verifies exact RPM identity, installed file ownership and rpm -V integrity, and that the fake service is neither enabled nor active and has no D-Bus name owner.
4. The second actual reboot after rpm-ostree rollback must remove both RPMs and all three protected fake-service paths. The guest removes its disposable keyring.
5. The host requires explicit C4a serial evidence in addition to the existing C2v two-reboot success markers.

The fake RPM has no install/start scriptlets, dedicated account creation or real permissions. The guest stays network-disabled and SELinux Enforcing. Production Connections QML and credential authority are untouched.

## HOW TO USE

No desktop action. Dedicated GitHub workflow: .github/workflows/connections-c4a-silverblue-signed-status.yml. It builds two unrelated ephemeral CI signers/fixtures and invokes the existing tests/connections/c2v_silverblue/boot_official_silverblue.sh with the explicit signed-fixture directory. Private test signing keys never leave their disposable Fedora builders.

## VERIFY

- [ ] Bash syntax, C4a source contract, existing C3d provenance contract and C2n deny-only tests.
- [ ] Both disposable RPM builders export only public CI artifacts and signed test RPMs.
- [ ] Official Fedora Silverblue 44 image checksum, real installer, initial boot, SELinux Enforcing and no-network gate.
- [ ] Untrusted-before-import and verified-after-import signatures, exact RPM payload file list, no scriptlets.
- [ ] Independently observed same pending deployment containing BOTH exact packages and idle transaction.
- [ ] Real first reboot, signed RPM file ownership/integrity and inactive fake service.
- [ ] Actual rollback reboot, both RPMs absent, all fake service files gone, disposable keyring deleted.
- [ ] Existing normal C2v/C2x acceptance runs remain valid.
- [ ] Independent review and operator acceptance before merge.

## WATCH OUT FOR

**Trust:** The ephemeral package signer and its public key are supplied by the same CI build. This demonstrates integrity-check mechanics, NOT an independently trusted release or signing authority.

**Scope:** The fake status service deliberately remains INACTIVE on Silverblue. This is not a test of running C3b/C3c D-Bus/systemd/SELinux service identity on Silverblue; that separate proof was from a mutable Fedora Cloud VM. No production package distribution, release key custody, consent, API use or caller authorization is proven.

**Diagnostics:** C2z retains guest-local Bash tracing. Never move those traces into a production credential-bearing service without redaction, retention and access controls.

**Ownership:** Only two shared C2v test scripts were changed under explicit opt-in, plus new C4a CI/test/docs. C3d's own files are untouched. Coordinate future modifications of that owned seam.

## CHECKLIST

- [x] Current Hospital/source/ownership preflight.
- [x] Reuse accepted C2z and C3d with a dedicated opt-in path.
- [x] Add source and guest signed-service gates.
- [x] Add CI and static deny-only contract.
- [ ] Run and inspect full exact-head GitHub CI.
- [ ] Independent review; operator acceptance and separate merge approval.
- [ ] Separate release trust and per-caller operator consent integration.

## NEXT

Inspect full GitHub CI failure/acceptance evidence. Fix only observed defects without weakening exact pending deployment, both reboots, signature checks, offline network, SELinux Enforcing or service-inactive requirements. Leave PR draft until operator disposition.

## DECISIONS

Operator authorized bounded C4a CI-only work after C2z acceptance. No workstation modifications, production activation, permanent signer trust, credentials, real NASA traffic, cross-Team QML changes or merge are authorized. No verified live Hospital registration.
