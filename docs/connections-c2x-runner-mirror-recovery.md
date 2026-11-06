# 🏥💜 Connections // C2x Official Ubuntu Runner Mirror Recovery

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Universal Connections · CPU++ SETTINGS
STAFF ROLE // External Hospital-compatible Doctor, OPEN AI // CHATGPT, not live registered
ASSIGNMENT // Restore temporary GitHub runner QEMU provisioning and rerun real offline Silverblue 44 rpm-ostree
BASE // main f8d02b5df10aac877a42d67cc5820121883d0cb7, merged C2w #1374
PERMISSIONS // Repository draft PR and disposable CI only; no workstation writes

## IMPLEMENTATION

Merged C2w #1374 corrected the Silverblue guest media label but its GitHub run 42263641915 failed before Fedora boot: the Ubuntu runner's Azure apt mirror stalled fetching qemu-system-common and qemu-system-x86, hitting its 360-second C2V_BLOCKED // RUNNER_APT_INSTALL timeout. Both repository validation checks passed. Actual booted RPM layering and rollback remained unverified.

C2x adds a new dedicated GitHub Actions workflow without changing the merged C2v/C2w guest scripts. The only behavioral change is temporary Ubuntu runner dependency provisioning: instead of the slow Azure-specific mirror, a private per-run apt source list pins package reads to official archive.ubuntu.com (noble, noble-updates) and security.ubuntu.com (noble-security) with existing ubuntu-archive-keyring.gpg verification. Apt operations have explicit 150-second refresh and 690-second installation limits; their failures are reported separately. It checks QEMU, qemu-img, xorriso, genisoimage before attempting to install Fedora.

Fedora's official Silverblue 44 SHA256-pinned installer, offline QEMU/KVM, the C2VCI media label matching preflight, inert signed CI-only RPM, SELinux Enforcing and true two-reboot rollback gate are all inherited unchanged.

## HOW TO USE

No desktop action. GitHub CI runs automatically for a pull request that changes the new workflow or this documentation. CPU++ Connections remains a read-only status interface.

## VERIFY

First require C2X_PASS // SIGNED_OFFICIAL_QEMU_SETUP_COMPLETE. This alone is NOT acceptance. Full C2u/C2v acceptance still requires an installed, booted Fedora Silverblue 44 OS; offline rpm-ostree install of inert local RPM; first reboot with package in booted /usr and rpmdb; rpm-ostree rollback --reboot; and a second reboot showing the package absent. All exact-head CI checks must succeed, with no skipped guest proof.

## WATCH OUT FOR

Bypassing the failing Ubuntu runner mirror is not the same as solving potential offline rpm-ostree metadata/cache, OSTree composition, disk or boot issues. Do not interpret an inert test RPM or ephemeral signing identity as a real protected Connections service, release key, authenticated consent, or a live workstation installation. Guest network access remains disabled. Existing production broker authentication and credential grants remain closed.

## CHECKLIST

- [x] Confirm #1374 merged and recover latest exact runner failure
- [x] New isolated workflow using only signed official Ubuntu apt archives
- [x] Preserve Silverblue ISO digest and real two-reboot test gates
- [ ] Verify CI provisioning and full Silverblue behavior
- [ ] Identify next actual guest blocker if any
- [ ] Independent review and operator acceptance

## NEXT

Inspect the official-mirror CI run and only then diagnose the guest's bounded rpm-ostree logs. A second follow-up change is needed if the Silverblue layering or rollback checks fail.

## DECISIONS

Draft GitHub work only. No merge, local machine edits, credentials, keyring entries, provider calls, TASKS changes, production permission changes or live Hospital registration.
