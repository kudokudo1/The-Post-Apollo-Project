# 🏥💜 DOC 1 // Installed Forest host candidate is still not protected C3e custody

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM / ROLE:** Universal Connections · Protected C3e / DOC 1, external Hospital-compatible; no verified live registration  
**BOUNDARY:** Cross-owner Forest Core B5c installed candidate public status → C3e nonadmission  
**STATE:** Disposable GitHub CI only · **PRODUCTION SIGN-IN / FOREST PRIVATE DATA HOLD**

## IMPLEMENTATION

A Linux process can run an actual RPM-installed file, own an inherited Unix `SOCK_SEQPACKET` descriptor and submit a correctly structured packet. That establishes only the observed **local test process and bytes**. It does **not** prove separately administered key enrollment, private database custody, an authenticated recipient, current revocation/history, protected one-use authorization or a terminal receipt.

The original Forest Core [B5b #2390](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2390) owns `scripts/forest/native_host_candidate_b5b.py`. Its single immutable public response reports `UNKNOWN_HOLD`, `privateBytesSubmitted=0`, `sourceAuthenticated=false`, `recipientAuthenticated=false`, `permissionGranted=false`, `productionAuthority=false` and `revocationFencedAck=false`. The original [B5c #2391](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2391) builds that exact source into an **unsigned CI-only RPM**, installs it in a disposable Fedora 44 container, launches a genuinely separate unprivileged process from `/usr/libexec/post-apollo/forest-ci/forest-host` using `/usr/bin/python3 -I -B` and an inherited unnamed socket, and then removes the package. Its tests check installed bytes and process/FD evidence, not installed production enrollment.

This DOC 1 milestone introduces a **distinct C3e-only read-only diagnostic consumer** that parses at most 1024 bytes, rejects duplicate keys, nonfinite JSON, invalid UTF-8, extra/private fields, any positive permission/recipient/source claims and nonzero private-data submissions, and returns a fixed nonauthorizing observation. No local signer, SQL database, direct native writer, remote transport, production permission, root enrollment or protected reply is added. It does **not** turn the Forest Core public HOLD status into an Identity `UNAVAILABLE` receipt or an approved Forest issuer.

The consumer takes a controller-calculated source SHA-256 as a **CI argument**, which the Fedora job checks against the actual RPM-installed file. This is a byte correspondence diagnostic, **not an independently enrolled root fingerprint**. Its output explicitly sets `packageDigestIsOperatorEnrollment=false`, `installedForestHostOperatorApproved=false`, `independentForestEnrollmentRootVerified=false`, `currentForestHistoryAndRevocationVerified=false`, `originalProcessSeatRecipientAuthenticated=false`, `privateForestDatabaseCustodyVerified=false`, `protectedOneUseChallengeSpent=false`, `forestListSessionsAllowed=false`, `forestPrivateTitleDisclosureAllowed=false`, `forestProvisionalEgressAllowed=false`, `protectedTerminalOutcomeVerified=false`, `safeToRetry=false` and `productionSignInAllowed=false`.

**A missing packet is `UNKNOWN_HOLD_NO_RETRY`.** A syntactically valid public denial cannot settle an attempted private operation. `protected_forest_admission()` always refuses.

## HOW TO USE

No workstation, NAS, installed host or user-account action. This PR adds only four DOC 1-owned CI/test/doc paths:

- `tests/connections/c3e_release_trust/C3eForestInstalledCandidateNonAdmissionCI.py`
- `tests/connections/test_connections_c3e_forest_installed_candidate_nonadmission.py`
- `.github/workflows/connections-c3e-forest-installed-candidate-nonadmission-ci.yml`
- This documentation.

GitHub Actions first runs the 20 strict public-packet cases on `ubuntu-24.04` and inherits the original B5b native tests. A separate job invokes **the unchanged B5c RPM build script**, installs its resulting test-only package in a **fresh Fedora 44 container**, executes the new C3e tests as unprivileged `nobody` with the actual installed executable and socket, verifies the package files again and uninstalls it. No Forest Core-owned files are edited, and the installed candidate remains test-only.

## VERIFY

The 20 strict negative tests include a real-format public HOLD with all C3e authority false; absent ACK; cross-product/Identity source; forged `LIST_SESSIONS`, recipient, source, revocation ACK, positive production fields, nonzero private bytes, boolean masquerading as integer zero, forged safe actions, private title injection, duplicate/trailing/oversize/nonfinite JSON, malformed controller digest, self-hosted runner refusal and unconditional protected admission denial.

Four **separate native cases inside Fedora's installed RPM environment** verify the byte-exact root-owned package file and RPM owner, true `/proc` child commandline/inherited socket inode, public HOLD returned from the actual running installed program, all eight attempted protected control tokens returning only public HOLD, and private-looking input receiving no reply. These four cases run in addition to the strict 20.

Exact-head CI and independent Nurse 2 review are necessary. This new integration does **not** certify signed release, Silverblue immutable deployment, active unlocked human seat, protected filesystem, independent custodian or actual private data egress. Do not label it native production acceptance.

## WATCH OUT FOR

- **Cross-owner authority remains separate.** Forest Core owns B5b/B5c installed-host candidate and any future private DB opener/serializer. DOC 2 owns a future independently authenticated Forest-original source and recipient/seat evidence, but cannot silently relabel its Identity C4b Silverblue service as Forest. DOC 3 owns separately authorized `LIST_SESSIONS`, private titles, provisional disclosure/revocation and generation consent. DOC 1 owns independent enrolled custodian/currentness semantics.
- **Candidate packaging is not operator selection.** The B5c installed CI location is `/usr/libexec/post-apollo/forest-ci/forest-host`, not the proposed but **unapproved** production `/usr/libexec/post-apollo/forest/forest-host`. No production service, systemd unit, trusted runtime UID, storage root, private DB or authenticated recipient exists from this milestone.
- **No trust-root loophole.** A passed SHA comparison under a caller-provided source digest and an actual Linux PID cannot replace independently provisioned signing/revocation/history custody, current issuer state, original command/recipient binding or actual terminal settlement. The old C3e Identity fixture keys cannot be reused as Forest authority.
- **Review debt is not erased by GitHub merges.** DOC 1's [#2388](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2388) RFC and Forest Core B5b/B5c had no independent PR reviews recorded at this checkpoint. DOC 1 [#2382](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2382) has independent scoped corrective PASS, with #2374's original historical REVISE preserved.
- **Production remains HOLD:** ForestW rendering, title reads, SEND/voice, model inference, protected Forest C5 approvals, C3e Sign-In and TimeW restore remain separate.

## CHECKLIST / NEXT

- [x] Reconcile reviewed #2382, merged RFC #2388 and new Forest B5b/B5c source and exact installed paths.
- [x] Add bounded C3e public-nonauthority consumer and adversarial tests.
- [x] Add actual B5c RPM-installed interop job with no cross-owner source edits.
- [ ] Verify exact-head GitHub jobs and raw native evidence.
- [ ] Obtain independent Nurse 2 C3e review for this PR and separately review outstanding #2388 RFC; Forest Nurse 2 owns Forest Core review.
- [ ] Operator/Forest Core ACCEPT actual production host identity, protected private DB opener, recipient channel and original serialization boundary. DOC 2 then adds installed source evidence subject to explicit approval.
- [ ] Operator names separately administered Forest-purpose custodian/key enrollment and protected history/revocation/one-use recovery policy. DOC 1 develops approved integration only then.

## DECISIONS

**Local-first development and eventually independently administered protected custody** remains the accepted staging direction, not an enrolled host/root. This source-only integration is an executable negative test of an installed *candidate*, not an authorization layer or production deployment. **HOLD.**

## Follow-up // Fixed public refusal diagnostics

The operator deferred NAS and second-PC setup ([#2119 decision](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119#issuecomment-7132962989)). Existing C3e test-only parser hardening remains within DOC1 scope; this does not introduce another synthetic issuer or change the reviewed #2432 custody architecture. Malformed UTF-8/JSON exceptions previously retained rejected bytes/text as a nested exception. The decoder now emits only fixed refusal codes outside its exception handler, including bounded deeply nested malformed input; duplicate-key and nonfinite refusals retain their existing codes. Three added tests cover exception chains, fixed codes and fresh result isolation. This does not erase Python traceback locals, guarantee safety against an in-process code modifier or imply a production disclosure occurred. No valid packet schema, native Forest source, actual RPM harness, protected admission, authority or retry behavior changes. Expected dedicated test count: 23 strict plus 4 installed; inherited Forest B5b 13 unchanged. Fresh exact-head CI and independent Nurse 2 review required; previous #2397 results remain historical evidence only.
