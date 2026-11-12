# 🏥💜 C4b // Identity Gateway Silverblue installation contract V1 (separate assignment)

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** C4b Identity Gateway Silverblue (new test-only assignment; **not** C4d Connections status)  
**STAFF ROLE //** external Hospital-compatible DOC implementation, live registration unverified  
**ASSIGNMENT //** independently inspectable signed Identity **RPM**, supervised Silverblue service origin, SELinux/seat/process and rollback proof  
**AUTHORITY //** operator expressly authorized this separate assignment November 10, 2026, without merging, workstation installation or production activation  
**STATUS //** Phase 1 signed RPM and synthetic release-envelope tests verified. Phase 2 real offline Silverblue installation/layering/two-boot rollback verified. Phase 3 supervised nonroot AF_UNIX gateway, four signed `UNAVAILABLE` receipts and complete rollback verified in an earlier **unconfined** run. Phase 4 real **enforcing `postapollo_identity_ci_t`** gateway and kernel PID/start/cgroup/peer continuity for four signed denials verified in [#43067641932](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/43067641932). The **independent AF_INET SELinux denial, disposable custom-policy cleanup and combined two-boot rollback remain unverified together**. Most recent exact-head CI suffered GitHub Actions `startup_failure` before any job steps.  
**OWNERSHIP //** `tests/connections/identity_silverblue/**`, its new workflow, this document. Identity DOC retains `services/identity/**`, `tests/identity/**`; protected C3e retains the trust reviewer/importer; C5 retains consent.

## IMPLEMENTATION

This **does not reuse C4d's fake Connections status host**. It packages the *actual existing* Identity-installed test gateway from `tests/identity/fixtures/identity_gateway_installed_ci` and the seven exact modules already used by Identity DOC's merged Ubuntu dpkg/systemd test. The source files are read-only inputs; no forked auth, extra protocol, QML edits or new credential path.

- `signed_identity_gateway.spec`: exact allowlisted eight source files under `/usr/libexec/post-apollo/identity/` (root-owned mode 0555), one CI-only unit (0644), no RPM scriptlets/triggers or automatic enablement. Product name `post-apollo-identity-silverblue-ci`, separate from the existing Ubuntu `post-apollo-identity-ci-fixture` and C4d status host.
- `post-apollo-identity-silverblue-ci.service`: non-enabled test unit. A disposable authorized-test marker and transient runtime environment are required. Dedicated nonroot identity, private runtime and `NoNewPrivileges=true` are retained. In disposable guest CI only, a compiled **Identity-specific SELinux test policy** plus a labeled, byte-identical temporary Python entrypoint and ephemeral systemd override produced the observed `postapollo_identity_ci_t` domain. The RPM-installed unit alone does not enable or prove that confinement; no workstation/production SELinux policy is installed.
- `build_signed_identity_gateway.sh`: guarded GitHub-only Fedora 44 RPM builder; disposable OpenPGP key signs package. Only public-key/fingerprint, signed RPM and hashes leave the builder. Never uploads a private release root or receipt signer.
- `verify_signed_identity_gateway.sh`: a **separate fresh Fedora container** creates its own RPM database, requires that the package signature be untrusted **before** explicit public key import, then verifies the package signature and exact role with no scriptlets. This establishes CI package signature correctness, *not* independent operator production key custody.
- `test_identity_signed_rpm_contract.py`: exact source roster, service start-gate and negative release/authority contracts. The CI workflow checks these and builds/verifies the RPM. No package is installed on the operator's Fedora machine.
- `release_manifest_ci.py` + `test_identity_release_manifest_ci.py`: separate ephemeral **Ed25519 release root** in the GitHub controller signs canonical purpose/role-scoped RPM SHA-256, the complete eight-module **plus systemd unit** SHA-256 roster, release epoch/sequence test floors, and a *distinct* disposable receipt-signing public-key fingerprint. Root and receipt private keys exist only in process memory; the RPM builder never receives them. The verifier rejects duplicate/noncanonical JSON, missing/extra module, wrong root, mismatched receipt key, modified package bytes and old floors. All returned authority flags are false. The public test root is **not operator-enrolled production custody**; a successful test proves only release-envelope mechanics.


**Booted-RPM integrity policy (test-only):** The signed package contains eight exact Identity modules (0555) and one inert unit (0644). Real OSTree composition changes modification timestamps. The guest's dedicated `verify_booted_rpm_mtime_only.py` parser accepts only RPM `.......T.` records for one of nine signed package paths, without duplicates or unexplained exit codes. Separate `rpm -V --nomtime` must be strictly clean, and per-file root ownership, permission mode, nonsymlink type and package ownership are still mandatory. This is not an installed-host identity or production-release admission decision.

The existing `installed_gateway_witness_v1.py` is **Ubuntu dpkg-specific** and cannot authenticate this RPM. Identity DOC must not route this test witness into `InstalledIdentityCommandAdapterV1` or enable sign-in merely because an RPM signature is valid.

## PROPOSED DOWNSTREAM INTERFACE // PENDING C3e + Identity DOC REVIEW

A future **Identity-specific, independently sourced, fail-closed witness** should bind all of these, without reading expected values from the guest's own command socket, UART line or QML:

1. **Release authority (independent of host):** purpose-bound release-root public key/pin, monotonic epoch/sequence and rollback/revocation floor, signed RPM SHA-256 and complete eight-module manifest, approved installed systemd unit/SELinux policy and **separate receipt signer key fingerprint**. The test RPM's disposable GPG key is *not* this root and cannot authorize host enrollment.
2. **Observed installed origin:** actual official Fedora Silverblue OSTree deployment identifier and RPM layer, signed package owner/content, root-owned nofollow file modes, active `systemd` unit/MainPID/UID/GID/cgroup, kernel `/proc/PID/stat` start ticks and /proc executable/argv, SELinux enforcing domain and locked/unlocked active logind seat. Recheck process/release/key/seat after restart, replacement and before and after each signed command receipt.
3. **Negative evidence and teardown:** unexpected package root/role/policy, stale/revoked version, unapproved receipt key, tampered or missing module, writable/symlinked path, wrong PID/start/cgroup/SELinux/seat, service replacement and host loss must each refuse. Real *two-boot* install/layering and rollback must prove the RPM, policy, signer keyring, service and test runtime are gone. No trusted-host value on guest-generated report or unsupported witness input.
4. **Authority output remains false:** `signedGuestOriginAuthenticated`, `evidenceCryptographicallyAttested`, `hostAuthenticated`, `canApprove`, `credentialActionsEnabled`, `productionAuthority` and `canBeginSignIn` must remain **false** for this disposable, deny-only fixture, irrespective of valid code/package/supervisor observations. Only a separately approved production authority and C5 one-use intent could consider a live command.

These are **interface requirements to review**, not a published, accepted production API. Identity DOC owns the future adapter; C3e owns independent security signoff. Source digest alone is not Python memory integrity; test-only independent CI root is not production root custody.

## HOW TO USE

GitHub Actions only: inspect open, unmerged [PR #1785](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1785), its signed-RPM contracts, real official Silverblue KVM workflow, and separate test-policy compiler. No desktop action. A previous **unconfined** real guest passed signed deny-only IPC and full two-boot rollback. A later real guest separately proved **actual dedicated enforcing confinement** with four signed refusals, but the **combined independent network-denial and rollback test has not passed**. Neither earlier result establishes operator-enrolled production trust, a protected seat witness, or C5 human consent.

## VERIFY

**Phase 1 acceptance:** exact-head source/adversarial contracts PASS, real Fedora 44 RPM build with original eight modules and inert unit, OpenPGP signature untrusted-before/imported-after in separate RPM DB, separate synthetic Ed25519 release-root signature over exact RPM+module+receipt-key public fingerprint with negative signature/key/floor/roster tests, no pre/post scripts or new credentials, no private signing key exported.

**Phase 2 real OS lifecycle [#42951211291](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42951211291): PASS.** Official offline Fedora Silverblue 44 installer, signed Identity RPM, first real OSTree deployment/reboot, full nine-file integrity with timestamp-only exception and clean `rpm -V --nomtime`, second rollback reboot, absence of Identity package, installed modules/unit, signer DB and test marker; SELinux remained enforcing.

**Phase 3 running service [#42993936702](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42993936702): PASS within deny-only CI scope.** Offline signed Fedora cryptography/CFFI/pycparser runtime dependencies; nonroot actual canonical installed Identity gateway supervised by systemd; PID/UID/GID/cgroup, kernel socket and process context observed; signed UNAVAILABLE for BEGIN, STATUS, CANCEL and RECOVER; test runtime/user/key deletion before real second rollback, and all four installed RPMs absent after rollback. **Crucial limitation:** observed SELinux domain was `system_u:system_r:unconfined_service_t:s0`. This is not dedicated SELinux confinement.

**Phase 4 actual kernel confinement and continuity [#43067641932](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/43067641932): PASS for the confined service and signed-refusal stages, complete workflow FAILED later.** Official offline Silverblue guest loaded the test-only module while enforcing, executed the installed nonroot gateway as `system_u:system_r:postapollo_identity_ci_t:s0` using a labeled CI-only entrypoint and `NoNewPrivileges=true` transition, verified kernel `SO_PEERCRED`, systemd MainPID, `/proc/PID/stat` start ticks, four real/effective/saved/FS UIDs/GIDs, cgroup and SELinux label around each signed `UNAVAILABLE` BEGIN/STATUS/CANCEL/RECOVER receipt. This proves *observed guest process continuity and actual dedicated domain*, not independently protected release-root custody, logind seat, or real C5 consent.

**Next combined SELinux/rollback gate: STILL BLOCKED.** The negative socket probe must itself run as `postapollo_identity_ci_t` without `RestrictAddressFamilies`, namespace or socket seccomp denial, observe kernel `EACCES`/`EPERM` creating an AF_INET socket, and prove the test policy, key, account and unit disappear before the actual second-boot rollback. A temporary journal-backed unit replaced an unreliable `systemd-run --pipe` attempt, but its latest execution verdict is unavailable: [#43071256155](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/43071256155) failed without retrievable complete guest evidence and the next attempts [#43098247648](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/43098247648) ended in GitHub `startup_failure` before running. Compile-only PASS does not close this combined gate. Independent C3e/Identity DOC security review remains mandatory.

## WATCH OUT FOR

The Identity gateway fixture currently refuses all real login, peer, seat and operator intent, independently of signing. This denial is deliberate and must never be relaxed by the C4b worker. The future installed host test requires pinned offline Python dependencies and an approved Identity SELinux domain, not a quick `systemctl start` on the operator's desktop. Preserve the C4d branch and protected C3e/C5 ownership.

## CHECKLIST

- [x] Separate operator authorization / owner-scoped GitHub branch
- [x] Existing Identity DOC gateway, witness, adapter and Ubuntu fixture inspected
- [x] Signed RPM/source/signature and synthetic release-root tests PASS on previous exact head (must retest on new source commits)
- [ ] Identity-specific signed release manifest with separate authority and revocation floors (reviewed)
- [x] Real official Silverblue RPM-OSTree install, second boot, signed deny-only IPC (CI-only)
- [x] Real rollback and complete absence of guest package/keys/runtime (no custom policy installed yet)
- [x] Dedicated enforcing SELinux domain and kernel peer/PID start/cgroup/SELinux continuity verified with four signed refusals in real guest (prior run)
- [ ] Independent kernel AF_INET socket denial without a systemd network sandbox, custom policy removal and complete two-boot rollback in the **same** real guest
- [ ] Additional process replacement/host loss and protected-seat negatives at the independent trust-review boundary
- [ ] Independent protected C3e technical review and Identity DOC interface acceptance
- [ ] Operator final acceptance and separately authorized merge
- [ ] Production activation: **HOLD**, not included in this assignment

## NEXT

Restore actual GitHub Actions execution for this PR and retrieve bounded real-guest markers. Then close the **independent enforcing SELinux AF_INET denial + disposable policy/key/user cleanup + real two-boot rollback in one run**. The dedicated running gateway and signed-refusal continuity are already demonstrated, but not the remaining combined gate. After that, coordinate the protected release/receipt signer, logind-seat and consent seams with C3e, Identity DOC and C5 without editing their owned files.

## DECISIONS

This is a separate authorized **development assignment**, not a transfer of the old C4d room or a production release. Open PR, unmerged and without operator final acceptance; a ready-for-review GitHub flag is not authorization to merge. No local Fedora writes, cross-owner source changes, live key deployment, provider operations or production login activation.
