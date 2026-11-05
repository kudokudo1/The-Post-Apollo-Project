# 🏥💜 Universal Connections // C2o disposable Fedora service integration

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
DOCTOR // Connections successor · external Hospital-compatible worker  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE (not live registered)  
ASSIGNMENT // Test C2n unit, D-Bus service ownership and access policy together under Fedora systemd  
PHASE // Repository-isolated CI only  
BASE // main 31a595d2c72cb3005a5fc925757394dd4338456e  

## IMPLEMENTATION

C2n PR #1315 has been merged, with 5/5 GitHub checks. C2n established a static service UID and narrow system bus policy in a **noninstalled template**, and verified cross-UID policy on an Ubuntu test bus. C2o extends that work to a disposable Fedora 44 container with actual systemd service startup and a distro-provided system bus. Production code, existing CPU++ controls and the user machine are untouched.

- tests/connections/c2o_fedora/FakeStatusHost.py is a CI-only executable stub implementing the already-proposed read-only GetStatus D-Bus method. It returns only IDLE, does not contact NASA or read credentials, and does not issue grants.
- tests/connections/c2o_fedora/BusPolicyClient.py inspects the actual Fedora system bus through dbus-next. The status remains OBSERVED_UNVERIFIED. Unknown Approve methods must fail.
- tests/connections/c2o_fedora/Dockerfile stages the exact reviewed C2n service unit and bus policy and builds a temporary Fedora 44 image. It creates three fake accounts: the service principal, a permitted read-only group member, and an outsider. The executable, service unit and policy are root-owned within the image.
- tests/connections/c2o_fedora/test_inside.sh checks real systemd-analyze verify, a static service with no autostart, explicit systemctl start and stop, process UID and NoNewPrivileges, bus ownership, allowed GetStatus, denied Approve, denied outsider requests and name cleanup.
- The workflow builds with a limited staged context containing only six fixed test inputs, no checkout or token mounts. It then boots Fedora systemd in a disposable privileged Docker container on an ephemeral GitHub-hosted runner, with runtime network disabled. This is deliberately constrained to PRs originating in the owning repository. Privileged CI is **not an isolation or production security proof**.

## HOW TO USE

No change to the operator's desktop. CPU++ → SETTINGS → CONNECTIONS → NASA FIRMS → VIEW REQUEST STATUS → INSPECT LOCAL HOST still uses C2i's read-only unverified same-UID inspector. No new button, local packages, system account or D-Bus service on the user's Fedora desktop.

## VERIFY

CI must prove real Fedora systemd and D-Bus integration, privileged test account separation, service shutdown and fail-closed application policy, in addition to C2n's unit contract. Merely copying a protected-looking unit file is not sufficient.

SELinux enforcement is a **distinct gate**. The Fedora image can contain SELinux userspace packages and report getenforce, but an Ubuntu GitHub-hosted kernel with a privileged Docker container generally cannot prove Fedora SELinux policy enforcing on real Fedora Silverblue. The test emits C2O_SELINUX_NOT_VERIFIED when not enforcing, never claims PASS on that boundary. A Fedora VM or separately approved Fedora system with actual enforcing SELinux is required.

## WATCH OUT FOR

The image runs a fake stub with a root-owned test filesystem; it is not a signed, installed or operator-approved Post-Apollo host. Read-only OS group membership does not authenticate CPU++ application identity. A root-owned service does not itself prove the status payload. A future host must include a reviewed trusted code package, controlled updates, OS-enforced peer verification, consent and revocation and separate credential broker.

Full systemd-in-container tests require elevated runner privileges. They do not provide isolation guarantees against malicious container code and should not be enabled for untrusted fork PRs. The CI workflow gates fork PRs, uses contents:read, disables checkout credential persistence, stages only explicit files, and runs the container without a network.

The status-only service intentionally uses AF_UNIX and IPAddressDeny=any; it cannot fetch NASA traffic. This is a feature separation, not a missing API key. Real NASA requests must be done by a separately reviewed, authorized provider component.

## CHECKLIST

- [x] Verify C2n merged and current main/PR ownership
- [x] Stage Fedora 44 image with exact C2n service and D-Bus policy
- [x] Implement fake read-only host and restricted OS client fixture
- [x] Add explicit systemctl and cross-UID policy test script
- [x] Add CI workflow with no local workstation changes
- [ ] Final CI exact-head completion and any needed CI corrections
- [ ] Independent review and operator merge/acceptance
- [ ] SELinux enforcing Fedora host or virtual machine verification
- [ ] Root-managed signed/verified service package and rollback
- [ ] Production consent, secrets isolation and provider integration

## NEXT

If Fedora CI passes, preserve C2o as the last disposable unit/bus implementation checkpoint. Next separate gate: real SELinux-enforcing Fedora VM with root-owned immutable service files and a protected client identity contract, then operator-authorized desktop staging. Any actual NASA operation remains a later explicit consent milestone.

## DECISIONS

No merge, local installation, Quickshell restart, desktop systemd changes, production D-Bus access, personal account creation, keyring operations, user data or real NASA network requests. CI-only proof-of-concept; failure is to be reported rather than described as production readiness.
