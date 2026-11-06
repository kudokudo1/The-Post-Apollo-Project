# 🏥💜 Universal Connections // C2s disposable install and rollback

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
STAFF // External Hospital-compatible Doctor; OPEN AI // CHATGPT  
ASSIGNMENT // C2s integrity-checked fake host package staging, negative tamper refusal, install and rollback  
PERMISSIONS // GitHub branch/draft PR and disposable CI only; no live Hospital registration or local desktop writes  
BASE // November 6, 2026 main after merged C2r #1338 and handoff #1343

## IMPLEMENTATION

C2r proved a **dedicated SELinux domain** `postapollo_connections_t` in a real Fedora 44 guest with SELinux Enforcing. C2s keeps that known-good service/domain test and adds a bounded **test-only bundle staging and rollback harness**.

The GitHub runner creates a tar.gz fixture from the repository's fake status host, read-only client, C2n static systemd unit and D-Bus policy, the disposable Fedora-built `.pp` SELinux module and an exact SHA-256-pinned offline `dbus-next` wheel. It generates an internal file-digest manifest and an external archive digest. It boots the same pinned official Fedora Cloud 44 QEMU/KVM guest **without any network interface** and stages the bundle through cloud-init. This archive is NOT an RPM, signed artifact, distributor-certified package or installer for the user's desktop.

Inside the disposable guest, the test checks that the service, Linux account and module are absent; verifies the archive digest and exact seven allowed flat archive entries; corrupts a copy of the archive and confirms its digest fails *before changing OS state*; extracts and verifies the internal file manifest; then invokes the already validated C2r guest script to install and explicitly start the fake service. All C2r checks (dedicated UID, `NoNewPrivileges`, `postapollo_connections_t`, deliberately denied `shadow_t` dummy file, allowed read-only GetStatus, refused unauthorized callers/approval/name claims and clean stop) must succeed.

Finally C2s performs an **explicit rollback**: removes the test-only service executable, static unit, D-Bus policy, client, dummy and runtime files; unloads only the disposable SELinux module; reloads systemd and D-Bus; deletes the test-created accounts and groups; and verifies no service, D-Bus owner, account or custom domain remains. SELinux must remain Enforcing throughout.

## HOW TO USE

No new desktop application or menu step. Existing CPU++ SETTINGS → CONNECTIONS remains status-only and read-only. These tests run in a one-use GitHub VM only, which is discarded afterwards.

## VERIFY

The required CI evidence is: clean VM baseline, official Fedora image and `dbus-next` checksums, custom SELinux module build and Enforcing kernel, exact archive manifest, tampered archive refused before installation, C2r confined-service/denial regression, static unit not automatically enabled, explicit start/stop, and successful rollback with no residual service/policy/user/bus name. No production QML credential grant may be opened.

## WATCH OUT FOR

**A SHA-256 manifest is integrity detection, not source authentication or package signing.** This test intentionally does not create or sign an RPM or register an RPM package transaction, and therefore does not establish rpm-ostree/Fedora Silverblue compatibility, trusted repository metadata, automatic transaction rollback, signed provenance, or safe upgrades. It verifies a temporary install/cleanup sequence only inside a disposable VM. The guest starts a FAKE STATUS host, not an authenticated API broker.

The reference policy may require independent narrowing beyond the one tested dummy-file denial. System D-Bus service name and SELinux identity do not by themselves authenticate a human operator or source application. Actual consent, task-source revision, real key management, signed immutable deployment and machine acceptance remain CLOSED.

Cross-room coordination: merged TASKS M13t PR #1304 contains an independent source-bound consent **simulation**. Connections C2r/C2s do not issue approvals. A coordination comment is recorded on #1304: three exact recovery scopes, authenticated operator and caller, single-use revocable grants, monotonic saved-source revision/compare-and-commit, no key release until separately approved. TASKS retains task editor/source ownership; this room owns shared protected host infrastructure.

## CHECKLIST

- [x] Recheck C2r #1338, handoff #1343 and TASKS M13t #1304 merged
- [x] Record shared-owner TASKS consent contract without touching TASKS code
- [x] Add integrity manifest and tampered-package refusal
- [x] Add SELinux-enforcing Fedora VM install/rollback test
- [ ] Verify exact-head GitHub CI and fix test-only issues
- [ ] Independently review confined policy grants and installation paths
- [ ] Build signed OS-native package / rpm-ostree-compatible deployment and uninstall contract
- [ ] Complete actual operator/host authentication and consent review
- [ ] Obtain operator acceptance before any desktop installation or production activation

## NEXT

On green CI, plan signed RPM provenance and full negative checks (network, keyring, write access) in a separate disposable Fedora Silverblue system test. Real credential issuance and encrypted TASKS recovery remain separate ownership and acceptance gates.

## DECISIONS

Draft branch and GitHub CI only. No merge, no user's Fedora changes, no desktop installer, no real credentials, task content, NASA access or source-writer modifications. Read-only fake service and deny-all CPU++ broker retained.
