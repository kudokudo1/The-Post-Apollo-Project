# 🏥💜 Universal Connections // C4b signed confined runtime on Silverblue

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · C4b signed confined runtime in Silverblue
STAFF ROLE // DOC, external Hospital-compatible; live Hospital registration not verified
ASSIGNMENT // Establish whether C4a's signed fake status-service RPM can be explicitly started under the C2r/C3b enforcing service-origin contract on genuine Fedora Silverblue 44
SOURCE BASE // main 30a11bf7ca75dc0d713bf059b52b6bfa19fb3440
AUTHORITY // GitHub-only disposable CI; no local writes, production activation, operator credentials or merge
OWNERSHIP // C4b test lane only; C3b/C3d source, production Connections QML/broker and other rooms remain independently owned

## IMPLEMENTATION

C4a (PR #1464, merged, exact-head CI green) established official Fedora Silverblue 44 ISO, ephemeral signed fake-service RPM verification, first real boot with package in /usr and rpmdb, and real rollback reboot removing the package. The service was intentionally never activated. C3d (PR #1451, merged) proved systemd/D-Bus/SELinux origin and signed RPM files for an explicitly started fake host in an ordinary mutable **Fedora Cloud** VM. C4b is a separate and more restrictive environment.

The C4b opt-in path stages existing C2r compiled custom SELinux policy, pinned dbus-next 0.2.3 wheel (SHA-256 58948f9aff9db08316734c0be2a120f6dc502124d9642f55e90ac82ffb16a18b), C3b origin probe, and existing read-only bus policy client on the existing offline seed ISO. C2t and C3d RPMs are signed in two disposable Fedora builders as before. No signer private keys or network are given to the VM.

Only the dedicated C4b GitHub workflow sets both C4A_SERVICE_RPM_DIR and C4B_RUNTIME_ASSETS_DIR. Normal C2v/C2x and C4a-only tests remain separate and must still pass. The guest copies only the test fixtures into /var, survives the normal C4a staged RPM layer and first real reboot, then:

1. Confirms C4a's signed test RPM file integrity, package ownership, SELinux Enforcing and no-network guest.
2. Installs existing C2r custom SELinux test policy in this disposable guest. It attempts to apply the actual SELinux executable entrypoint label to signed package-owned /usr on immutable Silverblue **without an overlay, remount, copy, permissive or untrusted fallback**. A refusal is a real test blocker, not permission to weaken OS protection.
3. Creates temporary service and test-reader Linux users, an offline pinned Python venv, and a world-readable nonsecret file labeled shadow_t as a negative SELinux control. These exist only in the VM.
4. Requires the signed service unit to be static and inactive before explicit start; reloads the isolated system D-Bus policy and refuses unauthorized name claims.
5. Explicitly starts only the fake read-only unit, verifies its exact Linux user, systemd status, kernel NoNewPrivileges, SELinux confined process domain, and actual denial of the world-readable negative control.
6. Reuses the unmodified C3b kernel/systemd/D-Bus owner/PID/UID/cgroup/executable-parent origin verifier. Requires the permitted read-only GetStatus for one test reader, denies approve/ownership requests, and denies the outsider.
7. Stops the service, verifies D-Bus name release, removes test principals, venv and SELinux module, and requires cleanup before allowing C2v's original rpm-ostree rollback/reboot.
8. After the real rollback reboot, requires signed fake service files absent, no service or name owner, no test users/modules/venv, then removes its /var scratch assets. The host requires explicit runtime markers **in addition to** C4a's exact source-backed two-boot success.

## HOW TO USE

No workstation commands. GitHub workflow: .github/workflows/connections-c4b-silverblue-confined-runtime.yml
Test-only source: tests/connections/c4b_silverblue/guest_confined_runtime.sh
Source contract: tests/connections/test_connections_c4b_silverblue_contract.py

## VERIFY

- [ ] Exact-head C4b shell syntax and deny-only tests.
- [ ] Two signed disposable RPM builders, independently built offline SELinux test module, pinned wheel, C3b origin and bus-policy probe staged without a private key.
- [ ] Real official Silverblue 44 image hash/installer, no-network guest, SELinux Enforcing, independently authorized pending layer and first real reboot.
- [ ] Immutable /usr signed test executable is successfully confined by the existing custom policy without a writable overlay or permissive fallback.
- [ ] Explicit fake service startup in confined domain; actual deny on world-readable shadow_t probe; kernel/systemd/bus process-origin coherence; reader can only GetStatus, outsider denied.
- [ ] Stop/release service, delete temporary policy/users/venv; actual signed RPM rollback and second reboot; verify all signed fake-service and test-state removal.
- [ ] Exact-head C2v/C2x/C4a regression CI unchanged.
- [ ] Independent technical/security review and operator decision.

## WATCH OUT FOR

**Known unverified seam:** immutable Silverblue /usr may refuse a newly installed SELinux entrypoint relabel; policy installation after OSTree composition may not authorize an executable transition. If it fails, diagnose using real CI. Do not use usroverlay, remount read-write, setenforce 0, broad allow rules, relabel arbitrary executables, or silently replace package provenance.

The package is signed by an ephemeral same-builder CI signer, **not** an independently trusted Post-Apollo production release authority. The original user and D-Bus group are test-only, not authenticated human intent or application caller identity. Even successful C4b would not authorize real installation, production service startup, API keys, credentials or provider calls. SELinux policy module is test-only; no use on the operator machine.

C4a PR #1464's independent audit/operator acceptance were not established by this worker. Its already verified merged test technical baseline is reusable, without silently declaring the prior assignment finally accepted.

## CHECKLIST

- [x] Inspect Syntagma and current GitHub branch/ownership; no C4b branch or PR at entry.
- [x] Create new isolated C4b branch.
- [x] Implement explicit opt-in test staging, guest runtime guard, host acceptance, dedicated CI and static contracts.
- [ ] Observe exact-head CI, diagnose/refine only evidence-supported failures.
- [ ] Independent review, operator acceptance; separate merge decision.
- [ ] Separate production trust and consent milestones.

## NEXT

Open draft PR and inspect the earliest C4b CI failure. If the Silverblue immutable entrypoint fails, retain enforcing/immutable guarantees, report the blocker and develop a separately authorized safe policy/OSTree compose strategy. Keep all privileged effects within disposable KVM guests.

## DECISIONS

Proposed C4b CI-only work accepted via operator "continue" after C4a technical results. GitHub-only test modifications; no local machine write, production activation, merge, credentials, provider traffic, security relaxation or ownership transfer.
