# Trash++ // V2v Real Read-Only System-Bus PIDFD Probe

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External DOC-compatible GitHub development; live Hospital registration not verified  
ASSIGNMENT // Implement the real read-only Linux system D-Bus query for systemd unit origin without granting production access  
SCOPE // scripts/trash, tests/trash and the already-owned Trash CI workflow; no source-owner service, keys, local desktop, production ArchiveStore, merge, Restore or Burn permissions

## IMPLEMENTATION

- Added `archive_v2_systemd_bus_readonly.py` with async `read_only_systemd_unit_by_pidfd(pidfd, expected_policy)`. It uses the actual `dbus-next` system-bus transport (lazy import) with UNIX_FD negotiation. There is no `systemctl` subprocess, shell parsing, service activation or numeric-PID fallback.
- Before contacting the bus, verifies the caller-supplied FD is an actual Linux pidfd by examining `/proc/self/fd/<fd>` and bounded `fdinfo`. Policy is a fixed set of expected unit ID, invocation ID, cgroup and fragment pathname. The application must independently supply that expectation; a client request cannot invent one.
- Resolves `org.freedesktop.systemd1` through `org.freedesktop.DBus.GetNameOwner`, requires a unique name, and asks the system bus for that connection's Unix UID and PID. Requires UID 0 and PID 1, refusing guest/user/rootless managers or unsupported proxies.
- Sends exactly `org.freedesktop.systemd1.Manager.GetUnitByPIDFD` to the **resolved unique bus owner** using signature `h`, body `[0]` and Unix FD array containing the original caller-owned pidfd. Expects exact `osay` response (unit object path, unit ID and 16-byte invocation ID), validates the reply's unique sender, then calls `org.freedesktop.DBus.Properties.GetAll` on that unit for `org.freedesktop.systemd1.Unit`. Requires Id, ControlGroup, FragmentPath, LoadState=loaded, ActiveState=active to match an independently supplied policy.
- Rechecks the well-known bus owner and the original pidfd after reading the properties. A lost owner, wrong UID/PID, changed invocation, incorrect property, malformed signature, unsupported library/host, bus error or timeout refuses with a stable code. The caller owns and closes its original pidfd; the probe only disconnects its own bus.
- Returns a bounded evidence digest and `systemdUnitVerified=false`, `sourceServiceVerified=false`, `sourceAuthorityVerified=false`, `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false` and `burnAllowed=false` even when read-only transport checks pass.
- The current V2u fixture manager and V2m test broker are **not** replaced or connected to this probe. Source-owner policy, approved distinct UID, script/package integrity, protected release floors and true Archive authorization have not yet been established.
- CI workflow installs the pinned `dbus-next==0.2.3` version only in the runner for these Python tests. No package is installed on the operator's machine by this PR.

## HOW TO USE

No new UI or desktop action. The standalone async read-only API requires a supported Linux system D-Bus and an already-open original process pidfd. It intentionally has **no CLI, no daemon, no public socket service and no production broker integration**.

All V2v tests use a fake system-bus transport and the real `dbus-next` typed `Message` / `Variant` objects; they do not connect to a real PID 1 manager. The library fails closed if `dbus-next` is missing and will not install it itself.

## VERIFY

- Validates the real D-Bus message contract: resolving an owner, obtaining Unix credentials, passing an actual pidfd in UNIX_FD index 0, reading `osay` unit/invocation and `a{sv}` properties, and checking exact sender and expected policy.
- Adversarial tests exercise wrong UID/PID1, changed unique name, forged response sender/signature, unit/invocation/state/cgroup/fragment drift, non-pidfd FD, missing or extra policy keys, bus timeout/error and no ArchiveStore access.
- Full Trash Python + 40 JS regression suites and Meta Apollo Grammar must pass before a technical CI checkpoint can be recorded. Independent **live, read-only host verification**, service-owner integration, D-Bus security review and operator acceptance are separate.

## WATCH OUT FOR

- A read-only D-Bus observation of a service's origin is **not** proof that Weather or research authorized that service to copy data. A valid systemd unit alone does not prove an immutable script tree, package release floor, protected signer key, application consent or data-owner scope.
- The API intentionally checks PID 1 and root for the system-bus service. A legitimate user systemd manager or unusual non-PID1 proxy refuses; do not add automatic fallback to `GetUnitByPID` or user bus.
- The low-level D-Bus call verifies the bus owner at both ends of the query, but unit state may still change between observations or after returning. This read-only probe never issues a capture permit.
- CI uses simulated D-Bus responses. The real system bus, libdbus transport, Flatpak/SELinux policy and actual Fedora Silverblue systemd version have **not** been exercised on the operator's machine. No live claims from these mocks.
- No trusted time, durable off-UID authorization anchor or atomic coupling of the external release floor to ArchiveStore exists. V2s/V2t identities remain isolated synthetic fixtures, not approved service-owner authority.
- All existing Trash++ UI and archive data are unchanged. Nothing grants Restore or Burn permissions.

## CHECKLIST

- [x] Re-read current Syntagma AGENTS/Hospital, V2u merge/main head, and concurrent ownership
- [x] Verify upstream systemd GetUnitByPIDFD and dbus-next UNIX_FD APIs
- [x] Implement strict real read-only D-Bus client with unique owner + PID1 credential checks
- [x] Add 10 mocked-transport / actual Linux pidfd regression tests
- [x] Pin CI-only dbus-next test dependency
- [ ] CI green, any needed corrections and independent security review
- [ ] Source-owner/MACHINE/Connections approval for actual host probing, trusted policy and real broker integration
- [ ] Operator authorization for merge, local runtime setup or production activation

## NEXT // V2w Implementation

Protected service trust integration and independently anchored release history. Coordinate with source owners before pinning a dedicated UID, service unit/script/package hash, external trust source, true systemd invocation and trusted clock. After approval, design an atomic/recoverable **real ArchiveStore** quota, signed provenance and nonce transaction. Preserve deny-only until every authority gate is satisfied. Restore, retention and Burn remain separately owned.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2v-readonly-systemd-bus-20261111  
BASE // verified main before V2v  
STATE // GitHub-only implementation; no live Hospital registration or desktop change  
ROLLBACK // Revert the standalone probe, tests, documentation and CI-only dependency. No actual Archive SQLite, snapshots, systemd services, keys, cgroups or source data have been altered.
