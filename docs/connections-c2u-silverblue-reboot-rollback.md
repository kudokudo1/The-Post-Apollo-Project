# 🏥💜 Universal Connections // C2u real Fedora Silverblue reboot / rollback gate

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
STAFF // External Hospital-compatible doctor, provider OPEN AI // CHATGPT (not live Hospital-registered)  
ASSIGNMENT // Test real Silverblue 44 OSTree installation, package layering after reboot, and rollback after second reboot  
BASE // 1d7b4fc1daf78ab5799fc41e3ccca4c5db695b60, C2t implementation merged; C2t verification docs PR #1353 remains separate  
PERMISSION // GitHub ephemeral runner/KVM/ISO only; no workstation changes or production activation  

## IMPLEMENTATION

C2t #1350 successfully tested **native Fedora RPM** signatures/transaction rollback, but Fedora Cloud uses ordinary package management. It did **not** test Fedora Silverblue's immutable rpm-ostree deployments. C2u adds a separate **real Silverblue** test rather than relabeling that Cloud test.

The CI runner downloads the exact **official Fedora Silverblue 44 x86_64 OSTree installer ISO** `Fedora-Silverblue-ostree-x86_64-44-1.7.iso` and checks Fedora's published SHA256 `9ccec9b075a0a4358a7209b2667156aaeeec3a6a3c8d71cada45b57fca9b4682` before ever booting it. This image is about 3.1 GB, not a preinstalled Cloud qcow2. It extracts the installer's original kernel and initrd, stages a separate read-only Kickstart/fixture ISO and a clean sparse 40 GB virtual disk, and boots Anaconda headlessly in QEMU/KVM with **no network interface**. Kickstart uses the ISO's OSTree repository as the source; this is not a Docker container. Only the VM disk is targeted by `ignoredisk`/`clearpart`.

Kickstart includes a one-use first-boot systemd verification unit inside **the guest only**, with no password or SSH login. It requires an actual booted OSTree system with the Silverblue ref, Fedora 44, SELinux Enforcing and no network device. It then asks `rpm-ostree install` to stage the already-tested signed, **inert C2t RPM** from the separate read-only ISO. It must prove a pending deployment, reboot, observe that the booted OS has the layered package, issue `rpm-ostree rollback --reboot`, then prove after the second reboot that the package is missing from both rpmdb and `/usr`. The resulting image and CI signing key are discarded. This test does not install the Connections service or credentials.

## HOW TO USE

No local app, shell commands or desktop changes. The test runs only through GitHub Actions for operator-owned repository PRs. Read-only CPU++ Connections remains unchanged.

## VERIFY

Require an official ISO SHA256 match, actual installer completion (not merely a successful QEMU launch), a separate Silverblue guest boot, booted OSTree/Silverblue identity, SELinux Enforcing, offline local RPM layering, a first reboot with the package **present in booted `/usr` and rpmdb**, and a second reboot after rollback with the same package **absent**. All steps must be evidenced by serial-console `C2U_PASS` markers and passing CI on the **exact head**.

## WATCH OUT FOR

**No result is a success until the full CI job passes.** The 3 GB official ISO, Fedora 44 installer behavior and actual OSTree package dependency resolution are new environmental factors. Anaconda may reject the kickstart bootloader/storage or local OSTree URL, the hosted runner may have insufficient disk/time, or `rpm-ostree install` may require metadata unavailable in the networkless guest. All such outcomes are blockers, **not reasons to fall back to ordinary Fedora Cloud or to claim Silverblue compatibility**. Fail closed and capture guest serial/install logs. A runner KVM preflight is not itself a real Silverblue deployment test.

Fedora publishes only an installer ISO for this Silverblue release, not a ready-to-boot official Silverblue qcow2 in that download section. If the unattended installation proves infeasible inside hosted GitHub CI, keep this milestone blocked and seek an authorized suitable disposable KVM runner or a separately verified osbuild Silverblue qcow2. Do **not** run this test on the operator's Fedora Silverblue machine.

Even a fully passing cycle tests only **one inert RPM** under one official Silverblue version and not a protected service package or release signing authority. The signed RPM comes from a temporary CI self-signed key; it is not authenticated as a production release. No keyring, NASA provider, Tasks recovery or desktop activation path exists in this PR.

Upstream installation references: https://fedoraproject.org/atomic-desktops/silverblue/download/ ; https://anaconda-installer.readthedocs.io/en/latest/user-guide/boot-options.html ; https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html .

## CHECKLIST

- [x] Recheck current Syntagma/Hospital and C2s/C2t merged code; no colliding Connections PR
- [x] Add official Silverblue x86_64 ISO digest gate
- [x] Add isolated guest-only Kickstart installer/bootstrap and offline read-only RPM media
- [x] Add booted OSTree layer, reboot and rollback assertions
- [ ] Run and debug exact-head GitHub Actions Silverblue installation
- [ ] Confirm rpm-ostree package appears only after first reboot and disappears after second
- [ ] Independent security review and operator acceptance
- [ ] Production-signed service package, official key distribution and native deployment activation

## NEXT

If green, independently review immutable OSTree layering/rollback evidence before considering a separately signed, least-privilege service RPM. If blocked, preserve the precise first failure and recovery pointer. Do not conflate a simulated OSTree state, Fedora Cloud VM, or regular rpm downgrade with an actual Silverblue reboot.

## DECISIONS

GitHub draft PR only. No merge by external doctor, workstation writes, running service, real credentials, NASA calls, TASKS source access, persistent release key, operator consent, or production authorization.
