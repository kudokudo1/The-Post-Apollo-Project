# 🏥💜 Connections // C2v Offline Silverblue Recovery

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ Settings  
STAFF ROLE // External Hospital-compatible Doctor, OPEN AI // CHATGPT (not live registered)  
ASSIGNMENT // Diagnose C2u's offline rpm-ostree transaction and preserve installer and two reboot gates  
BASE // main 5c1faab33836388175038c59d52231fad6c921e5 (C2u #1356 merged)  
PERMISSIONS // GitHub draft branch, disposable Fedora CI only; no workstation changes or production activation  

## IMPLEMENTATION

Merged [C2u #1356](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1356) is *not* accepted as passing: the final implementation head `581b1f21ac15aeb5196c16a6e198e90eb04dd609` had 2/3 CI checks pass, with [run 42188690468](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42188690468) failing in the real Silverblue guest. The run **verified** the official Fedora 44 Silverblue ISO checksum, a real unattended installation, booted Fedora 44 OSTree/Silverblue identity, SELinux Enforcing, offline network state and clean base state. It did **not** show an `rpm-ostree` install exit, a successful pending layer, or booted rollback. The host timed out its guest loop while the guest had reported `C2U_PASS // NO_REMOTE_RPM_REPOSITORIES_ENABLED_IN_OFFLINE_GUEST`.

C2v forks only this experiment's GitHub CI harness into `tests/connections/c2v_silverblue/` and reuses the same independently pinned official installer ISO, offline inert C2t package, guest storage, unchanged production deny-only flags and strict two-reboot checks. No changes to the already merged C2u source, TASKS editor or shared Connections production service.

The first-boot test now bounds the actual `rpm-ostree install --cache-only <local RPM>` invocation with a **480-second timeout** that terminates a stuck transaction instead of allowing systemd or the host to time out silently. A 30-second guest heartbeat records the current install log, rpm-ostree/rpm-ostreed process state and disk usage. On failure it records the transaction exit code, last install lines, `rpm-ostreed` journal, service status and disk space. The outer GitHub runner also streams serial progress approximately every 40 seconds, without needing network, SSH, authentication, or direct access to the user machine. Crucially, the **full** test still requires: installed Silverblue boot, a pending `rpm-ostree` layer, first reboot with the package in *booted* `/usr` and rpmdb, and second reboot after rollback with package absent.

## HOW TO USE

No local actions or applications. The new bounded diagnostic executes in GitHub Actions on operator-owned repository sources. CPU++ Connections still has `hostAuthenticated: false` and `credentialActionsEnabled: false`. C2t's signer is disposable and not a release identity.

## VERIFY

Observe the exact-head `silverblue-offline-ostree-diagnostic` GitHub CI job. It must verify the official ISO checksum, installer completion, actual Silverblue boot, enforcing SELinux, guest no-network state, a completed (not hung) local RPM layer command, actual pending deployment, first booted package and second rollback boot. A `C2V_INSTALL_FAILED_EXIT` or `C2V_BLOCKED` marker means failure even if repository-wide validate checks pass.

## WATCH OUT FOR

`rpm-ostree install --cache-only` may need metadata that the isolated machine does not have; it can also be CPU/disk constrained during OSTree composition. The first aim of C2v is **attributable diagnosis**. We must not weaken SELinux, enable internet, use the real desktop or pretend a Fedora Cloud ordinary RPM transaction is an immutable Silverblue deployment.

Do not interpret a new merged PR as permission to activate service identity, grant access to NASA, issue TASKS recovery consent, or install anything on the operator's desktop. This test package is still inert data with a disposable self-signed CI key.

## CHECKLIST

- [x] Read current Syntagma/Hospital protocols, verify C2u merged and no active competing Connections PR
- [x] Independently recover exact C2u failure from latest GitHub logs
- [x] Add guest-side bounded RPM transaction, heartbeat and failure-state diagnostics
- [x] Preserve real Silverblue ISO, SELinux and both reboot assertions
- [ ] Verify CI transaction result, then resolve only the observed blocker
- [ ] Confirm both booted layer and booted rollback on exact-head successful CI
- [ ] Independent security review; operator final acceptance

## NEXT

Investigate output of `C2V_INSTALL_FAILED_EXIT`, `rpm-ostreed` journal and disk space if the transaction fails; consider an offline, locally staged RPM metadata source only if evidence demonstrates it is required. No success claim without two completed boot-state checks.

## DECISIONS

Draft/CI only. No merge, workstation writes, service activation, credentials, production key, real task data, API calls, or live Hospital registration.
