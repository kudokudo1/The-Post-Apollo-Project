# 🏥💜 Universal Connections // C2p Fedora kernel SELinux VM gate

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
WORKER // external Hospital-compatible Doctor · OPEN AI // CHATGPT  
ASSIGNMENT // Verify SELinux is enforcing inside a **real Fedora guest kernel**  
PHASE // isolated GitHub CI prototype only; no Hospital live registration  
BASE // main 48057329c4407c8c5ac556436a228b358d860a4a  

## IMPLEMENTATION

C2o PR #1318 is merged, and its Fedora 44 *container* showed real systemd and read-only system bus behavior with SELinux disabled. C2p is intentionally a **new guest-kernel verification gate**. It does not deploy C2o's service to a VM yet. It verifies the missing prerequisite first, before claiming a protected service has passed.

The workflow uses a GitHub-hosted Ubuntu runner, checks whether /dev/kvm is available, then installs QEMU only in that ephemeral runner. It downloads the exact official Fedora Cloud Base Generic 44-1.7 x86_64 qcow2 from the Fedora Project and checks the SHA-256 provided by Fedora before using it. No unverified image is booted.

The runner uses cloud-init NoCloud to inject a single **read-only** SELinux probe, boots Fedora under QEMU/KVM with its own guest kernel and no network interface, and reads the probe's result from the serial console. The probe reports Fedora version, kernel, systemd, getenforce, the kernel's /sys/fs/selinux/enforce state and representative process contexts. It fails unless both kernel enforcement and getenforce confirm Enforcing. A container or a permissive/disabled VM can never count as a success. QEMU and VM disk files are discarded after the job.

The script does not create users, install programs inside the guest, start Post-Apollo's service, modify the guest's SELinux mode, or access real NASA credentials. Quickshell and the production broker are unchanged.

## HOW TO USE

The normal desktop CPU++ → SETTINGS → CONNECTIONS → NASA FIRMS → VIEW REQUEST STATUS → INSPECT LOCAL HOST path remains C2i's same-user unverified observer. There is no new local program, application, service or widget. The C2p workflow runs only inside GitHub Actions.

## VERIFY

1. GitHub runner exposes a usable /dev/kvm. If it does not, the workflow must fail with C2P_BLOCKED rather than silently falling back to an unrepresentative container.
2. The Fedora qcow2's exact SHA256 matches the official Fedora project's published hash; mismatches fail.
3. A Fedora 44 guest actually boots its independent kernel, cloud-init runs, and the serial console reports C2P_PASS for both getenforce=Enforcing and kernel /sys/fs/selinux/enforce=1.
4. Existing CPU++ authentication and credential permission flags stay false.

Official Fedora Cloud 44 source: https://www.fedoraproject.org/cloud/download/  
Official cloud-init QEMU/NoCloud reference: https://docs.cloud-init.io/en/latest/howto/launch_qemu.html

Exact verified head: 1b237f12f5a660d6de497be93e0e65d87bc485e0; GitHub initial CI 3/3 checks passed. Guest SELinux process contexts include system_u:system_r:cloud_init_t:s0 for the probe, but no Post-Apollo service-specific confined domain has been implemented or validated.

## WATCH OUT FOR

Hosted runners may not provide KVM; that is an environmental blocker, not a successful SELinux verification. A full Fedora VM cannot be simulated with a Docker container when the question is guest-kernel SELinux. A fallback to QEMU TCG is not enabled because it may be prohibitively slow; a supported KVM-equipped runner would be required for this milestone.

Even a successful Enforcing guest probe does **not** establish that our future service runs in a dedicated SELinux domain, that its executable is root-owned, that D-Bus policies integrate under SELinux, or that it can be safely installed on Fedora Silverblue. Those are separate C2p service-in-guest / signed package acceptance gates.

GitHub Actions is authorized to provision ephemeral runner utilities only; the user's personal computer is never contacted. There are no keys, credentials, SSH passwords, host-device mounts, provider calls or production activation. Source only from the owning repo operator: privileged runner operations are guarded.

## CHECKLIST

- [x] Confirm C2o merged and check concurrent ownership and current main
- [x] Add hash-pinned official Fedora 44 image test with NoCloud serial output
- [x] Add fail-closed /dev/kvm preflight
- [x] Add read-only enforcing SELinux probe
- [x] CI run 42048451030: KVM available, official Fedora 44 image SHA256 matched, VM kernel 6.19.10-300.fc44.x86_64 booted, SELinux Enforcing and /sys/fs/selinux/enforce=1
- [ ] Separately prove service startup inside enforcing guest
- [ ] Independently review SELinux process domain and AVC outcomes
- [ ] Production package integrity, consent/revocation and operator acceptance

## NEXT

If KVM is available and the VM passes, extend the disposable guest test to C2o's static service and D-Bus policy while retaining SELinux enforcing. If KVM is unavailable, report the blocker and identify a suitable isolated GitHub runner alternative; never report the previous container as an enforcing SELinux VM.

## DECISIONS

Draft PR only. No merge, desktop writes, local installation, local VM, system configuration, credentials, NASA calls, service authorization or production permission changes.
