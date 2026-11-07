# 🏥💜 Universal Connections // C3b systemd / D-Bus origin evidence

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · parallel protected-host verification  
STAFF ROLE // Nurse 2 (NRS-2), external Hospital-compatible (not live registered)  
ASSIGNMENT // Prove independent OS records identify the same fake protected status host inside disposable Fedora Enforcing VM  
SCOPE // GitHub-only C2r guest test extension, isolated C3b probe/policy, regression tests and CI  
PRODUCTION ACTIVATION // NOT AUTHORIZED

## IMPLEMENTATION

After merged C3a PR #1428, a private D-Bus status observation can be bound to a daemon-assigned unique connection name, yet this does **not** establish protected process origin. C3b takes a separate, test-only step by extending the already proven C2r Fedora 44 VM with **independent OS-record checks for the fake read-only service**.

`tests/connections/c3b_origin/C3bOriginCheck.py` does not launch any service. Only after C2r explicitly starts its root-owned fake status service, this read-only probe queries the real guest system bus for the current unique name owner, its Unix PID, and its UID. It also reads systemd's `MainPID`, `User`, `ActiveState`, `FragmentPath` and `ControlGroup`, plus the kernel's `/proc/PID/status`, `cmdline`, `cgroup`, and SELinux process context. The probe verifies agreement across independent sources and rechecks the name owner before accepting the observation.

The strict fake-only evaluator rejects a changed owner, PID/UID mismatch, unexpected process arguments, incorrect systemd unit, group/other-writable or nonroot-owned executable/unit/bus policy, missing NoNewPrivileges, non-Enforcing kernel, and a process outside `postapollo_connections_t`. It checks the three fixed protected fixture paths. All status objects keep `hostAuthenticated`, `credentialPresent`, `grantActive`, `canApprove` and `canUseApi` **false**.

C3b is mandatory within the disposable C2r test: `guest_confined_smoke.sh` invokes the new checker while the service is alive, `boot_confined_vm.sh` stages the script and requires its exact `C3B_PASS` marker on the guest serial console, and the existing C2r workflow runs the new adversarial unit tests before launching its VM.

No files in the active successor-owned C2y/C2z Silverblue workstream are touched. C3b does not bind a production Quickshell service or store credentials.

## HOW TO USE

No local desktop steps. The existing `Connections C2r confined SELinux status host on Fedora VM` GitHub workflow runs against the draft PR. The operator's CPU++ → SETTINGS → CONNECTIONS still exposes read-only, explicitly unverified status and disabled broker actions.

## VERIFY

Require at the **exact PR head**:

- [ ] Offline C3b policy tests reject forged service origin, UID, PID, command, weak file permissions and SELinux state.
- [ ] Official SHA256-pinned Fedora Cloud 44 image boots with its own kernel, `-nic none`, and Enforcing SELinux.
- [ ] Existing C2r custom domain, world-readable-file denial, D-Bus and unit restrictions pass.
- [ ] Live bus-reported unique owner PID/UID equals systemd MainPID and actual process UID.
- [ ] Process command, cgroup, protected files, NoNewPrivileges and SELinux domain match expected fake service.
- [ ] `C3B_PASS // OS_DBUS_PID_UID_SYSTEMD_SELINUX_ORIGIN_COHERENCE_TEST_ONLY` appears on the VM serial console; VM gate fails if absent.
- [ ] Production CPU++ `hostAuthenticated` and `credentialActionsEnabled` stay false.
- [ ] Independent review and operator acceptance.

## WATCH OUT FOR

This checks **coherence of observed system records in an ephemeral Fedora test image**, not cryptographically authenticated provenance. A malicious/compromised root, compromised bus daemon or unsigned replacement fixture is outside its proof. The tested executable is **fake** and unsigned; it is not a deployable broker. Matching Unix UID and PID is insufficient to authenticate a specific Post-Apollo widget or human operator. SELinux policy domain tests are limited to the checked protection boundaries.

C2y/C2z actual Fedora Silverblue layering and two-reboot rollback are separate acceptance gates. A successful C3b Fedora Cloud VM is **not** proof that Silverblue installation has passed. This work grants no credential, NASA, Proton or TASKS authority.

## CHECKLIST

- [x] Reacquire main, Syntagma/Hospital protocol, previous C3a merge and active C2z ownership.
- [x] Scope C3b to independent protected-host origin observations.
- [x] Add test-only status evidence observer and adverse policy tests.
- [x] Stage checker and enforce acceptance in the existing C2r Fedora VM gate.
- [ ] Exact-HEAD CI green and inspect logs.
- [ ] Independent review and operator merge decision.
- [ ] Later signed, root-managed package chain and authenticated operator/client permission system.

## NEXT

Fix any exact-head test failures without disabling owner, OS-user, SELinux or file-protection checks. If the full guest proves coherent origin, coordinate the next separate production-safety milestone: protecting installed service provenance and authenticated per-consumer consent/revocation. Do not implement real provider permissions in this PR.

## DECISIONS

GitHub-only review. No local writes, C2y/C2z edits, system service installation, production authentication claims, real credentials, provider network traffic, activation or merge.
