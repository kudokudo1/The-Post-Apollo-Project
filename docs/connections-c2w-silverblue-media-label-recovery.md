# 🏥💜 Connections // C2w Offline Media Label Recovery

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ Settings  
STAFF ROLE // External Hospital-compatible Doctor (not live Hospital-registered)  
ASSIGNMENT // Restore C2v guest RPM media discovery and complete Silverblue immutable RPM deployment test  
BASE // b8d3e83fdfe180691253988e098385ae30312cff (C2v merged through #1371)  
PERMISSIONS // GitHub draft branch and disposable CI only

## IMPLEMENTATION

C2v #1371 merged, but its real [GitHub job 128033605691](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42258975584) failed. Official Fedora 44 Silverblue installation and first boot succeeded. The new diagnostic log revealed a copy/rename error: the C2v host ISO is labeled `C2VCI` while the forked guest script still tried to mount `/dev/disk/by-label/C2UCI`. The resulting `C2V_FAIL // OFFLINE_RPM_MEDIA_MISSING` is a **test harness mismatch**, not evidence about rpm-ostree layering, SELinux confinement or immutable rollback.

C2w changes only the C2v guest test path in the **GitHub-only VM** to mount `C2VCI`. It logs guest `/dev/disk/by-label` and `blkid` on each attempt for reproducible diagnosis. The existing C2v CI workflow adds a fast, deterministic preflight comparing the host ISO volume label with the literal guest media label before incurring a 3.2 GB Silverblue ISO download and full Anaconda install. The intentionally isolated VM, pinned official ISO checksum, test-only signed inert C2t RPM, SELinux Enforcing, no network, bounded rpm-ostree transaction/diagnostics, pending layer, first reboot and second reboot/rollback checks are preserved.

## HOW TO USE

No desktop steps. The GitHub CI check `silverblue-offline-ostree-diagnostic` will run for this draft. The CPU++ Connections settings inspector remains observational and all production authentication and credential paths remain disabled.

## VERIFY

Require `C2V_PASS // OFFLINE_MEDIA_LABELS_MATCH` in the preflight and `C2V_PASS // REAL_SILVERBLUE_FIRST_BOOT_BASELINE` after actual ISO installation. These are **not** enough to accept C2w. The full acceptance gate remains: `C2V_INSTALL_RETURNED_SUCCESS`, a pending immutable deployment, a real reboot with layered package in rpmdb and `/usr`, `rpm-ostree rollback --reboot`, and a second boot with package absent. Final exact-head GitHub checks must pass. Any remaining installer, cached RPM metadata, deployment composition or boot failure must be treated as a blocker and logged, not assumed away.

## WATCH OUT FOR

A local RPM with no RPM-level dependencies does not guarantee `rpm-ostree install --cache-only` will compose an offline deployment without a seeded rpm-md cache. C2w deliberately **does not** change dependency-resolution behavior until its actual output proves the requirement. Never substitute a Fedora Cloud package-manager test or disable SELinux to create a green check. CI uses an ephemeral self-signed test key, **not** production release provenance. No real application authentication, TASKS recovery consent, provider keys or NASA API traffic.

## CHECKLIST

- [x] Verify C2v merged and current main; no competing Connections PRs
- [x] Recover failed exact-head CI guest serial output
- [x] Fix mismatched C2v ISO/guest volume label
- [x] Add fast static CI contract to catch future media label drift
- [ ] Run exact-head Silverblue GitHub CI
- [ ] Confirm offline package installation and booted rollback or record next blocker
- [ ] Independent review and operator acceptance

## NEXT

Inspect C2w's install/daemon logs if rpm-ostree still fails. Address only observed blockers in a separately reviewable change while preserving offline VM and unchanged desktop. An eventually passing test validates **inert** RPM staging only, not a production Connections service or full Silverblue upgrade safety.

## DECISIONS

Draft, unmerged, read-only production state. No workstation changes, no OS keyring, real credentials, provider calls, TASKS edits, production authentication grants or live Hospital registration.
