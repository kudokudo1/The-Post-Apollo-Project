# 🏥💜 Connections C3e-V // Signed claim and plain C4d guest diagnostic consistency

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · protected C3e evidence receiver
STAFF ROLE // DOC · original protected Connections development
ASSIGNMENT // Preflight existing C3e-Q signed test claim against C4d/C3e-U observation, without authentication
CONCURRENT OWNER // C4b/C4d Silverblue source and C4b Identity-specific installation, separate from C5 consent and Identity gateway
PRODUCTION // HOLD

## IMPLEMENTATION

C3e-Q/R/S and C3e-U are already merged on main. Q proves which disposable test key signed a **claim** that contains a verifier challenge. R can consume challenges in a root-owned disposable SQLite ledger. U checks the actual exported C4d observation format and caller-supplied expected values. These are different evidence layers. Neither an unsigned guest report nor a test-signed claim is a trusted actual host measurement.

**C3e-V is a narrow, CI-only consistency preflight, not an independently authenticated host.** It composes existing receivers without modifying the C4b producer or adding a second verifier:

1. Require the C4d diagnostic line to satisfy the original U bounded canonical schema and **caller-supplied expected** RPM/script/interpreter/PID/start/UID/GID pins. Never infer expected values from the guest line.
2. Snapshot the Q signed statement once using the original secure nofollow bounded reader, then invoke Q's real pinned OpenPGP test-signature verification with its separately provided public key/fingerprint and exact 32-byte verifier challenge. Require the digest of the pre-verification snapshot to equal Q's SHA-256 of the **actual signature-verified bytes**. This refuses data replacement between reads.
3. Compare 11 shared fields exactly across the signed Q statement and the plain C4d observation, including installed package/script/interpreter digest, D-Bus/systemd PID and UID/GID, Linux process start ticks, unit and enforcing SELinux.
4. Only return CI diagnostic signedClaimAndPlainGuestReportAgreeInCI:true while explicitly keeping **all host/issuer/replay authority flags false**.

A valid match still does **not** cryptographically bind the exact plain UART line to the Q signature, prove the guest's OS identity, establish issuer custody, or use the C3e-R durable challenge ledger. Q's volatile challenge protects only one local verifier instance in this preflight. Signed Q data still might originate from a compromised guest or disposable CI signer.

This preflight deliberately uses the **Connections fake status service** and rejects the separate Identity Gateway unit/role. The C4b Identity [proposed installation contract #1785](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1785) packages a different service and must not use this Q/C4d comparison for Identity installed-host enrollment or live Sign In.

## HOW TO USE

Review the disposable [C3e-V source and tests](../tests/connections/test_connections_c3ev_signed_guest_diagnostic_pair.py) in GitHub. Workflow .github/workflows/connections-c3ev-signed-guest-diagnostic-pair.yml generates test-only OpenPGP signatures in temporary CI directories, compares them with the existing C4d schema, exercises tampering, guest/signed-value disagreements, wrong signer/challenge/role, changed byte snapshots, and re-runs existing C3e-Q/U/R suites. No workstation commands, package installation, host service, user account, key enrollment, credentials or production actions.

## VERIFY

- [ ] Exact-head pair tests pass; any apparent "matching" test result remains explicitly non-authorizing.
- [ ] Existing C3e-Q signed GPG tests, U schema/real guest artifact regression, and R durable challenge test suite pass.
- [ ] Meta Apollo Grammar and normal PR CI checks pass.
- [ ] Independent Nurse 2 exact-head technical review and operator merge acceptance.

## WATCH OUT FOR

The two test inputs can be forged to agree. Their equivalence is a useful **format-level integration guard** only. It is **not an independently authenticated host** and is not sufficient to promote a C4d guest report into C3e-R trusted evidence or Identity gateway enrollment.

The separate missing evidence must come from an independently enrolled issuer and real protected host witness: genuine RPM-OSTree installation/release authority, package and interpreter bytes, systemd/D-Bus/PID start, SELinux/cgroup/seat, verified external release and signer custody, bound challenge with rollback-resistant independent replay state, full rollback/removal, and separately approved C5 human intent. Neither copying guest fields into expected pins nor re-signing a guest JSON blob with CI's own key establishes that provenance.

C3e-V returns externalIssuerCustodyVerified:false, durableChallengeConsumptionVerified:false, signedGuestOriginAuthenticated:false, evidenceCryptographicallyAttested:false, installedGuestMeasured:false, hostAuthenticated:false, canApprove:false, credentialActionsEnabled:false and productionAuthority:false even when input compatibility passes.

## CHECKLIST

- [x] Rechecked actual C3e-Q/R/S/U contracts on current main and C4b/C4d/Identity ownership.
- [x] Prepared standalone protected C3e-V test-only receiver, tests, workflow and handoff.
- [ ] Verify exact-head CI and fix only actual scoped defects.
- [ ] Independent Nurse 2 security review of test-only match and immutable verified-byte snapshot.
- [ ] Merge only after technical review, despite standing user related-PR merge authorization.
- [ ] Separately sourced C4b signed origin and protected replay/consent integration before a real authority grant.

## NEXT / DECISIONS

Use this as a hard negative gate for future source-interface discussion. When C4b supplies actual independently authenticated release/process/signer and challenge provenance, design and review a **new production-specific trust contract**, rather than promoting these test-only diagnostics. Keep C4d/Identity/C5 owner branches untouched.

C3e/DOC ownership continues. No production activation, local machine changes or claimed live Hospital registration.
