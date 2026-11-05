# 🏥💜 Universal Connections // C2q read-only host inside SELinux-enforcing Fedora VM

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
STAFF // External Hospital-compatible Doctor; provider OPEN AI // CHATGPT  
ASSIGNMENT // Test C2o fake read-only service + C2n D-Bus policy under C2p real SELinux enforcing Fedora kernel  
BASE // main 5ea3499de3ccb960d1e2e86dfbaa9dced84b7e49  
PERMISSIONS // GitHub branch, CI, docs only; no operator local machine installation  

## IMPLEMENTATION

C2p PR #1329 is merged. Its Fedora 44 Cloud VM with a separate guest kernel reported SELinux Enforcing and /sys/fs/selinux/enforce=1. C2q is the follow-up **service-inside-enforcing-guest** experiment, not production deployment.

Two isolated files under tests/connections/c2q_enforcing_vm stage the existing C2o fake-only host executable, C2o read-only D-Bus client and C2n static systemd service and restrictive bus policy into a freshly booted Fedora 44 Cloud VM. The guest is networkless and disposable. It creates separate test service/reader/outsider accounts **only inside the guest**, uses a pinned offline dbus-next wheel and applies root ownership and normal SELinux file labels.

The test requires real Fedora SELinux Enforcing before installing the fake fixtures. It checks actual `systemd-analyze verify`, explicit service start (no automatic enablement), systemd process UID, NoNewPrivileges, process SELinux context from /proc, allowed group GetStatus, denied outsider GetStatus/Approve and name ownership, and release of the bus name on explicit stop. Every reply is OBSERVED_UNVERIFIED, with no credential permissions.

The runner downloads only the official Fedora Cloud Base Generic 44-1.7 image and dbus-next 0.2.3 wheel, verifying exact published SHA-256 digests before booting. The VM has `-nic none`. The files come from the version-controlled repository and the pinned wheel; no guest network access is used. CI will be the source of verification, and failures remain blockers until corrected.

## HOW TO USE

No new application or menu. Existing CPU++ → SETTINGS → CONNECTIONS → NASA FIRMS → VIEW REQUEST STATUS → INSPECT LOCAL HOST remains the same user-socket read-only unverified inspector. The C2q host exists only inside a throwaway Fedora VM in GitHub Actions.

## VERIFY

GitHub CI must show real guest kernel Enforcing, the dedicated service UID, root-owned files and SELinux process context, permitted GetStatus, rejected name takeover/unknown method and denied outsider access, clean shutdown, and deny-only CPU++ checks. A green VM job is not evidence of a real production host installation.

## WATCH OUT FOR

**Enforcing mode is not proof of a dedicated confined domain.** Read the actual SELinux service process context. The default Fedora policy may run the fake Python host in a general systemd service domain rather than a custom `postapollo_connections_t` domain. C2q intentionally does not add or load a custom SELinux policy, change SELinux enforcement, or assert process-specific confinement. Any AVC denial is a test failure to investigate, not a reason to use permissive mode.

An unsigned Python script and repo-supplied tests in a disposable VM are **not signed package provenance**. The owner/group D-Bus policy controls transport, not application identity or user consent. The static service is status-only and denies network access, so it cannot fetch NASA data. Production API and credential handling remain explicitly unavailable.

## CHECKLIST

- [x] Recheck C2p merged, Syntagma protocols, main and open competing Connections PRs
- [x] Add fully disposable C2q guest test and runner workflow
- [x] Reuse C2n unit and bus policy, C2o fake host/client, C2p Fedora image hash
- [x] Pin offline dbus-next wheel hash
- [ ] Verify exact-head CI Fedora guest with enforcing service startup
- [ ] Review SELinux service context and access denials
- [ ] Independent code/security review and operator merge decision
- [ ] Custom SELinux domain, signed install, approval/revocation, service identity
- [ ] Production CPU++ host activation and actual NASA provider

## NEXT

If the enforcing VM accepts the service, record its observed SELinux context and split future work into a separate minimal custom SELinux domain policy and package-signing/provenance gate. Never infer the real user's Fedora Silverblue installation is ready merely because disposable VM tests pass.

## DECISIONS

External Hospital-compatible work only. C2q is a draft test milestone, without live Hospital registration or operator workstation writes. No local virtual machine, installation, systemd or D-Bus changes, Quickshell restart, credential use, API grant, NASA traffic, or PR merge.
