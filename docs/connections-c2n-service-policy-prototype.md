# 🏥💜 Universal Connections // C2n protected service/package and D-Bus policy proposal

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
DOCTOR // Successor Connections worker  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE  
ASSIGNMENT // Noninstalled protected-service unit and system-bus policy prototype  
PHASE // GitHub isolated review; not desktop deployment  
BASE // main 009af387b403716dc7aa8ea4a791d8db633b5b5a  

## IMPLEMENTATION

C2m PR #1314 is merged. C2m proved that a separate Python process can exchange read-only status over a disposable private D-Bus daemon, but neither its session bus nor name ownership establishes a trusted desktop service.

C2n adds a **noninstalled package candidate** under services/connections/experiments/c2n_package. It does not replace C2i/C2j, mutate CPU++, install a systemd service, create an account on the operator workstation, or enable any provider capability.

- postapollo-connections-status.service.template is a static-UID service proposal for postapollo-connections, using Type=dbus and BusName=org.postapollo.ConnectionsStatus1. Its ExecStart names a deliberately absent protected executable path, /usr/libexec/post-apollo/connections-status-host --read-only. There is no [Install] section, activation alias, or automatic start. It is **not runnable on the current desktop**.
- The unit proposes NoNewPrivileges, read-only system/homes, restricted capabilities, user-space socket family AF_UNIX, IPAddressDeny=any, PrivateDevices/PrivateTmp and other systemd sandbox flags. This is a status-only host, intentionally without network capability. An eventual NASA fetcher must be a **separately scoped and approved service**, not a covert expansion of this status daemon.
- org.postapollo.ConnectionsStatus1.conf.template denies all clients from claiming or calling the service name by default, grants name ownership only to the dedicated static service UID, and permits only GetStatus on its exact object/interface to members of the proposed postapollo-status-readers group.
- org.postapollo.ConnectionsStatus1.xml describes one read-only GetStatus method returning a bounded status string. No approval, keyring, token, write or NASA API methods are defined.
- A static contract test checks exact unit options, no installation/credential interface and no production imports. A disposable GitHub-runner test starts a real custom dbus-daemon with this proposed policy and uses three *temporary Ubuntu test accounts* to check ownership refusal and group-restricted GetStatus/Approve behavior.
- No system-bus service is installed or contacted. Disposable CI creates its test principals on the runner only, which is destroyed after the job.

## HOW TO USE

There is no new Post-Apollo UI control. The existing CPU++ → SETTINGS → CONNECTIONS → NASA FIRMS → VIEW REQUEST STATUS → INSPECT LOCAL HOST remains a strictly read-only *unverified* same-user-socket observer. The protected-service candidate is only inside the repository and GitHub CI.

## VERIFY

CI must pass the new static package checks, actual owner/reader/outsider test-bus policy, earlier C2m/C2l/C2k/C2j/C2i regression tests, and CPU++ broker denial assertions. Report exact-head check results separately. Real Fedora systemd service startup, SELinux compatibility, protected binary provenance, and official system-bus configuration are not tested by this milestone.

The official D-Bus policy model is based on dbus-daemon's documented per-user own and send_destination rules, and systemd's static service user and sandboxing concepts. Actual policy composition with Fedora's installed system-bus configuration must be verified before any installation.

## WATCH OUT FOR

**This is not a trusted production host.** A template in a user-editable checkout is not root-owned deployment evidence. Group membership is a machine-level read-only access policy and does NOT identify the CPU++ executable or prove operator consent. Existing system-bus policies can interact with this fragment, so integration must review rule ordering, other installed fragments, and actual SELinux policy. The D-Bus status payload remains unverified, and no real credentials should cross this interface.

A changing DynamicUser identity is intentionally not used because the proposed D-Bus policy needs a stable service identity. The static account and reader group are *candidates*, not created on the operator's Fedora machine. The prototype unit's missing ExecStart and absent [Install] section are deliberate installation barriers. Do not copy any template to /etc or /usr manually.

## CHECKLIST

- [x] Verify C2m merged and latest Patient main/ownership
- [x] Add isolated noninstallable static-UID systemd unit proposal
- [x] Add narrow GetStatus D-Bus policy and one-method interface
- [x] Add static unit/XML security contracts
- [x] Add runner-only cross-UID policy smoke and prior regressions
- [ ] Exact final HEAD CI completed successfully
- [ ] Independent review and operator merge approval
- [ ] Validate real Fedora system-bus composition and SELinux in approved disposable target
- [ ] Approve protected executable provenance, installation plan and rollback
- [ ] Implement trusted service identity and consent/revocation before credential access

## NEXT

C2o should first review policy composition and root-managed artifact integrity in a disposable installed environment with real systemd, D-Bus and SELinux. A dedicated service executable, controlled package signatures, trusted naming/peer checks and explicit operator consent should remain separate acceptance gates. Only after those can CPU++ show authenticated status, and real NASA data access requires its own permitted broker.

## DECISIONS

Proposal only; no local workstation changes, production service activation, system group creation, Quickshell restart, keyring access, NASA traffic, credential grants or merge. Preserve C2i's existing same-user read-only observer unchanged.
