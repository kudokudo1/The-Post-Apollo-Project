# Trash++ // V2u pidfd-to-systemd unit contract (fixture only)

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle
PROVIDER // OPEN AI // CHATGPT
STAFF ROLE // External DOC-compatible development, not verified live Hospital-registered
ASSIGNMENT // Verify deny-only PIDFD-to-unit/invocation contract and bind synthetic manager response at test capture commit
PERMISSIONS // GitHub branch, draft PR, tests/docs in Trash++ only. No real Weather/research/MACHINE/Connections modifications, local host writes, signing keys, PR merge, systemd service installation, live Archive capture, Restore or Burn.

## IMPLEMENTATION

- Added `archive_v2_systemd_manager_fixture.py` with an explicitly **TEST_FIXTURE_ONLY** provider modelling the documented systemd `org.freedesktop.systemd1.Manager.GetUnitByPIDFD` API. A real Linux PIDFD comes from the original V2p SO_PEERCRED peer, not a client-supplied or potentially reused integer PID.
- An independently supplied test policy pins existing allowlisted source owner, UID/GID, exact service unit ID, **invocation ID** (distinguishes restarts of the same named service), systemd unit object path, cgroup v2 path, unit fragment pathname and V2q unit SHA-256. A fake manager result must match all of them, report `loadState=loaded`, `activeState=active`, and agree with the existing V2t kernel cgroup and V2q service-file evidence.
- The fixture adapter only checks an open PIDFD and returns prearranged test data. It **never communicates with a live D-Bus bus**, spawns `systemctl`, installs a service, owns a private key, or trusts an untrusted socket packet's claimed process fields. It does **not** establish authenticated systemd origin and always returns `systemdUnitVerified=false`, `sourceServiceVerified=false` and `productionAllowed=false`.
- V2o's synthetic broker requires the V2u manager fixture, policy, V2t cgroup witness and V2q pinned file policy together. It checks the manager's unit/invocation during initial admission and again in the V2p PIDFD/V2m SQLite precommit guard. If the manager's response changes, the nonce and synthetic copy roll back together.
- V2m's **test-only** copy row and V2n's canonical request binding now include `manager_witness_sha256`. Query-only recovery reports only the digest. Older fixture rows remain explicitly empty and never gain retroactive manager attestation.
- Existing actual ArchiveStore, V2i unsigned provenance, V2j VERIFY CHAIN, real capacity bar, Quickshell SAVE SNAPSHOT, Camera/GIO and Burn behavior remain unchanged. All synthetic results keep `archiveCopyAuthorized=false`, `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false`, and `burnAllowed=false`.

## HOW TO USE

There is no new desktop button or host installation. GitHub synthetic CI creates a temporary Unix socket, test-only SQLite, ephemeral owner/root/release signing keys and a fake manager response; it uses a real Linux PIDFD for the original test-client process. The expected unit, cgroup and invocation are supplied by the test harness, not by the client request.

## VERIFY

New synthetic tests cover:
- Fixed unit ID, invocation ID, unit object path, active/loaded state, cgroup, fragment file and unit checksum
- Real pidfd evidence and receipt linkage through the existing V2t signed checkpoint + V2s release floor
- Wrong unit, invocation, cgroup, fragment file, UID, signing/file policy, fake manager response type or absent components
- No arbitrary client-supplied manager fields
- Manager invocation change at final precommit check, with zero nonce/copy committed
- Unsupported PIDFD/manager refusal
- Old V2t rows without manager metadata
- No D-Bus service start/stop, private keys, real ArchiveStore or Quickshell code paths

Full Trash Python, 40 JS Camera/snapshot/capacity/chain/Burn, Meta Apollo Grammar workflow and independent security review are mandatory before declaring verified.

## WATCH OUT FOR

- **The manager adapter is simulated.** It does not authenticate the real system D-Bus sender or PID1, call `GetUnitByPIDFD` on a live system, establish a dedicated service UID, or prove that an interpreter executed the pinned script. A privileged process or same-UID test worker can produce an internally matching fake result. No production authorization may depend on this module.
- systemd exposes the read-only `GetUnitByPIDFD` API on modern releases. A future real adapter requires source-owner/Connections approval, authenticated system bus identity, UNIX_FD passing, strict method/reply validation, cgroup and invocation consistency, and explicit refusal on unsupported hosts. Do not fall back to numeric `GetUnitByPID` automatically.
- The configured unit fragment's bytes may change after measurement; a matching fragment path and unit name do not prove the service manager actually loaded those exact bytes or that its imports/dependencies are immutable. Genuine protected units need trusted package/release provenance and unit manager verification.
- The V2s release ledger and V2m test snapshot SQLite remain separately controlled by the same unprivileged test user. V2t's second signature is another **ephemeral test key**, not a protected externally anchored monotonic release history or trusted time source. The final precommit manager check can race postcheck changes; no kernel/filesystem/SQLite atomicity.
- Production source keys, protected service-manager D-Bus trust, real ArchiveStore quotas, signed V2i receipt migration and authorized Restore/Burn remain future cross-Room work. Weather/research, MACHINE and Connections ownership has not been transferred.

## CHECKLIST

- [x] Latest `main`, AGENTS/Hospital, ownership and V2t code/CI state checked
- [x] Strict synthetic PIDFD-to-unit/invocation service-manager contract
- [x] Connect to V2t/V2q evidence and V2m atomic test copy with final guard
- [x] Durable test-only manager hash, read-only recovery and legacy empty evidence
- [x] Add adversarial and rollback tests
- [ ] Full GitHub CI and any corrections
- [ ] Real authenticated D-Bus adapter, service-owner approval and independent security review
- [ ] Operator acceptance and authorized merge/host activation

## NEXT // V2v Implementation

**Real read-only systemd manager adapter and protected external release authority design**, contingent on explicit Weather/research + MACHINE/Connections handoff: authenticate `org.freedesktop.systemd1` system-bus service, pass original pidfd via `GetUnitByPIDFD`, inspect actual unit/invocation/cgroup and fully pinned package release with a dedicated UID, then secure off-UID monotonic release history and trusted time. Only thereafter design and review real ArchiveStore quota/nonce/snapshot/provenance admission. Keep all generated fixture code deny-only. Restore/Burn require separate authorization.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2u-pidfd-manager-contract-20261111
BASE // main 605b2b4ed256ae55172db1e6cc7fdf58f813b019
STATE // GitHub-only development, no live Hospital registration
ROLLBACK // Revert V2u fake manager adapter, optional broker checks, added test-only witness field, tests and this document. The user's actual Archive SQLite and all recorded snapshots remain untouched; no host service, key, D-Bus configuration or protected source changed.
