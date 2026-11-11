# 🏥💜 Connections C3e-Z // Signed Identity release bound to complete host record (CI only)

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · Protected C3e evidence / issuer trust
STAFF ROLE // DOC · original protected Connections developer
ASSIGNMENT // Join existing independently pinned synthetic signed release, C3e-Y complete signed host record and preissued CI challenge
CONCURRENT OWNERS // C4b Silverblue, Identity DOC, C5 consent, C4d guest observation
PRODUCTION // HOLD

## IMPLEMENTATION
C3e-X #1846 and C3e-Y #1864 are already merged. C3e-Z adds FOUR new DOC-owned files: read-only composition module, 20 adversarial tests, dedicated CI workflow, and this contract. It reads but does not modify the merged Identity-owned silverblue_release_candidate_v1.py, and does not edit C4b/C4d/Identity/C5/runtime/UI code.

1. Caller supplies distinct Ed25519 release-root, host-witness and denial-receipt public keys. The module refuses any key-role alias.
2. Verify independently supplied synthetic signed Identity release: exact nine-path file roster with SHA-256 pins, signed RPM hash, package, unit, role, receipt signer fingerprint, and release epoch/sequence.
3. Before consuming a challenge, require equality between the signed release, CI expected host snapshot and C3e-Y witness: RPM sha256, exact installed identity-gateway-ci entrypoint SHA256, Identity unit, receipt public-key fingerprint, epoch and sequence. Require exact release, not merely a newer-than-floor release.
4. Freeze caller-owned file and process-pin mappings before running source and host checks, preventing mutation between the signed release verification and C3e-Y intake.
5. Only after source checks pass, invoke existing unchanged C3e-Y complete signed record, four Ed25519-signed UNAVAILABLE responses and one-use root-local challenge consumption. Invalid source or forged records leave the test challenge ISSUED.
6. Return positive results ONLY with InCI/RootLocalCI suffixes. All host/issuer/custody, consent, sign-in, credential and production authorization values remain FALSE.

## HOW TO USE
CI-only workflow: .github/workflows/connections-c3ez-release-bound-host-evidence.yml. Its disposable GitHub runner uses ephemeral test signer keys and a root-private /run/c3ey-ci-* SQLite challenge. There is no local workstation installation, native browser/Identity command, or widget control. Existing C3e-X, C3e-Y and Identity synthetic release candidate tests run as regressions.

## VERIFY
- [ ] Exact-head 20 C3e-Z adversarial tests and deny-only static gate.
- [ ] Previous 15 C3e-X, 21 C3e-Y and Identity signed release candidate tests.
- [ ] GitHub Grammar, root-signed fake RPM and release regressions as triggered.
- [ ] Independent Nurse 2 source/security review of this exact head before merge.
- [ ] Separate post-merge Nurse 2 review of C3e-Y #1864 remains outstanding.

## WATCH OUT FOR
Passing signatures prove only that disposable CI keys signed claimed bytes. The source and expected kernel fields are not independently authenticated, and no actual official Fedora installed process, active logind seat, protected SELinux identity or trusted native caller is measured here. The keys remain caller-pinned test fixtures. Multiple distinct CI keys are not evidence of independent real-world key custody.
The root-local C3e-Y SQLite replay ledger is **not externally rollback-resistant**. Its stored state can be reverted by a privileged party. A CI challenge is not an externally custodied production one-use authorization, and a signed command denial is not C5 human consent. No result from C3e-Z may enable sign-in.
C3e-Z's signed file roster matches the installed gateway entrypoint, but the ephemeral Python interpreter executable in C3e-X is not independently admitted by the signed release. Actual kernel-source/executable binding, production root enrollment and revocation still require separately reviewed C4b/C3e integration.

## CHECKLIST
- [x] Verify Syntagma, C3e ownership, C3e-X/Y merge, Identity release verifier and C4b worker state.
- [x] Add four isolated DOC-owned files for signed release/runtime pairing and adversarial tests.
- [ ] Exact-head CI tests and independent Nurse 2 review.
- [ ] Owner merge after all gates and operator-authorized process; operator final acceptance separate.
- [ ] Resolve C3e-Y post-merge review gap.
- [ ] C4b independently signed installed host+seat/SELinux witness; C3e external replay custody; C5 human consent; Identity production acceptance.

## NEXT
After source/CI verification, request NRS-2 exact-head review. Genuine host-source provenance and externally protected challenge authority are the next actual trust integration, not a synthetic test flag.

## DECISIONS
Protected C3e/DOC role retained. No real credentials, release enrollment, production activation, local user machine writes, other worker file changes, or claimed live Hospital registration. Technical success is not operator final acceptance.