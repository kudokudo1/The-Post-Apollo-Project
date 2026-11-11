# 🏥💜 C4b // Identity Gateway Silverblue installation contract V1 (separate assignment)

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** C4b Identity Gateway Silverblue (new test-only assignment; **not** C4d Connections status)  
**STAFF ROLE //** external Hospital-compatible DOC implementation, live registration unverified  
**ASSIGNMENT //** independently inspectable signed Identity **RPM**, supervised Silverblue service origin, SELinux/seat/process and rollback proof  
**AUTHORITY //** operator expressly authorized this separate assignment November 10, 2026, without merging, workstation installation or production activation  
**STATUS //** Phase 1 signed package and ephemeral manifest tests verified; real Silverblue installation, RPM layering and first reboot observed; strict installed-file verification and second rollback boot pending; running systemd/SELinux Identity gateway unverified  
**OWNERSHIP //** `tests/connections/identity_silverblue/**`, its new workflow, this document. Identity DOC retains `services/identity/**`, `tests/identity/**`; protected C3e retains the trust reviewer/importer; C5 retains consent.

## IMPLEMENTATION

This **does not reuse C4d's fake Connections status host**. It packages the *actual existing* Identity-installed test gateway from `tests/identity/fixtures/identity_gateway_installed_ci` and the seven exact modules already used by Identity DOC's merged Ubuntu dpkg/systemd test. The source files are read-only inputs; no forked auth, extra protocol, QML edits or new credential path.

- `signed_identity_gateway.spec`: exact allowlisted eight source files under `/usr/libexec/post-apollo/identity/` (root-owned mode 0555), one CI-only unit (0644), no RPM scriptlets/triggers or automatic enablement. Product name `post-apollo-identity-silverblue-ci`, separate from the existing Ubuntu `post-apollo-identity-ci-fixture` and C4d status host.
- `post-apollo-identity-silverblue-ci.service`: non-enabled test unit. A disposable authorized-test marker and external transient runtime environment are required. Dedicated nonroot service identity, private runtime and explicit no-elevation settings; the actual confinement still needs a **new Identity-specific SELinux test policy** and kernel verification. An inert unit file is not proof that `systemd` ever started it.
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

GitHub Actions only: open the dedicated C4b Identity Silverblue draft PR and inspect the `C4b Identity Silverblue signed RPM contract` run. Expect a signed disposable RPM and isolated-keyring verification. Do not install the RPM locally, trust it for a real sign-in, or accept this as a completed two-boot test.

## VERIFY

**Phase 1 acceptance:** exact-head source/adversarial contracts PASS, real Fedora 44 RPM build with original eight modules and inert unit, OpenPGP signature untrusted-before/imported-after in separate RPM DB, separate synthetic Ed25519 release-root signature over exact RPM+module+receipt-key public fingerprint with negative signature/key/floor/roster tests, no pre/post scripts or new credentials, no private signing key exported.

**Verified in prior official Silverblue CI:** disposable offline Fedora Silverblue 44 installer, independently checked signed Identity RPM, real rpm-ostree layering, and first boot into the installed package. [Guest run #42947183789](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42947183789) revealed **nine timestamp-only `T` mismatches** in `rpm -V` output. That run failed closed before rollback. The correction permits timestamps only on the exact nine allowlisted files, while requiring clean `rpm -V --nomtime`, full verified digests/modes/owners, and all deny-only service gates. **Not yet verified:** second rollback reboot, complete teardown, independently enrolled release root/receipt-key custody, running Identity process/socket/SELinux/seat identity, or signed negative receipts. These remain Phase 2+ requirements.

## WATCH OUT FOR

The Identity gateway fixture currently refuses all real login, peer, seat and operator intent, independently of signing. This denial is deliberate and must never be relaxed by the C4b worker. The future installed host test requires pinned offline Python dependencies and an approved Identity SELinux domain, not a quick `systemctl start` on the operator's desktop. Preserve the C4d branch and protected C3e/C5 ownership.

## CHECKLIST

- [x] Separate operator authorization / owner-scoped GitHub branch
- [x] Existing Identity DOC gateway, witness, adapter and Ubuntu fixture inspected
- [x] Signed RPM/source/signature and synthetic release-root tests PASS on previous exact head (must retest on new source commits)
- [ ] Identity-specific signed release manifest with separate authority and revocation floors (reviewed)
- [ ] Real offline official Silverblue RPM-OSTree install, second boot, supervisor/SELinux evidence, deny-only IPC
- [ ] Real rollback and complete absence of guest package/keys/policy/runtime
- [ ] Independent protected C3e technical review and Identity DOC interface acceptance
- [ ] Operator final acceptance and separately authorized merge
- [ ] Production activation: **HOLD**, not included in this assignment

## NEXT

Finish official Silverblue installed-RPM integrity and real rollback verification, then add actual Identity running-service and SELinux evidence without changing `c2v_silverblue/**` or the existing C4d branch. Coordinate external pins and immutable module set with Identity DOC and protected C3e; escalate any desired shared-controller changes before editing.

## DECISIONS

This is a separate authorized **development assignment**, not a transfer of the old C4d room or a production release. Draft PR only. No local Fedora writes, cross-owner source changes, merges, live key deployment, provider operations or production login activation.
