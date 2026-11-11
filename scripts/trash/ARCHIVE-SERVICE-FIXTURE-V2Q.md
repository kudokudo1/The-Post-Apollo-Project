# Trash++ // V2q Source Service Files & Socket Integrity (Fixture Only)

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
PROVIDER // OPEN AI // CHATGPT  
STAFF ROLE // External DOC-compatible worker; no verified live Hospital registration  
ASSIGNMENT // Bind V2p's pidfd-protected synthetic capture to a trusted test manifest of service unit/script/socket files  
SCOPE // Only own scripts/trash and tests/trash; GitHub stacked draft PR. No host writes, real source service changes, key installation, protected owners, Merge, Restore or Burn rights.

## IMPLEMENTATION

- New `archive_v2_fixture_service_identity.py` accepts an **independently provided TEST_FIXTURE_ONLY** policy pinning an existing allowlisted demo/Weather owner, exact synthetic unit/script/socket basenames, current fixture UID/GID and expected SHA-256 for unit and script bytes. The root must be an explicit absolute caller-owned private `0700` directory. No path or trust key is taken from the on-wire copy request.
- Opens unit and script files using directory-relative `open` with `O_NOFOLLOW`, checks regular file/owner/group, private mode, single-link count and size ≤1 MiB, hashes the actual opened bytes and compares against policy. Checks the pathname still points to that inode. Records inode/dev/mode as well as digest, so even a same-content replacement is refused.
- Requires the Unix socket path to be an actual socket owned by the fixture process with no group/world access. A service check compares the accepted socket's kernel `getsockname()` pathname to the pinned socket path, then rechecks the socket inode/mode and both files.
- V2o's already-accepted single-request fixture handler optionally requires the pinned service-file witness. On an opted-in request it rechecks files/socket **before signed admission and again inside the V2p pidfd guard before the V2m SQLite COMMIT**. If changed, both the test nonce and test copy roll back.
- The service-file witness digest is included in the V2n request-binding hash and stored additively alongside V2m's synthetic test copy/nonce. Recovery validates the digest's shape and returns it without copying payload bytes. Old fixture copies retain an explicit empty service evidence field. No actual ArchiveStore schema/user snapshots are modified.
- Even a matching service-file witness leaves `sourceServiceVerified=false` (the policy is a test fixture), `sourceProcessVerified=false`, `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false`, and `burnAllowed=false`. No listener, signer, real host identity, Quickshell UI or protected source file reader is created.

## HOW TO USE

No new Trash++ controls. The test harness creates a private directory containing two synthetic files and a Unix socket, pins their expected bytes and owner, exchanges pre-signed ephemeral fixture claims and checks whether the broker atomically saves a **synthetic** copy. Existing Archive SAVE SNAPSHOT/CONFIRM COPY, capacity gauge, VERIFY CHAIN and managed Burn behavior are unchanged.

## VERIFY

Synthetic tests cover correct file/unit/socket match; real request binding and durable recovery; altered script bytes; same bytes but replaced inode; symlink and hardlink substitution; group/world-writable unit or socket; mismatched/untrusted owner UID/policy; wrong accepted socket; missing service evidence on old fixture copies; and modifying the script precisely at the final precommit service check. The latter must leave zero consumed nonces and zero test copies. Existing V2p pidfd exit tests and all Trash Python, JS and Meta Apollo Grammar checks remain required.

## WATCH OUT FOR

- **This is an isolated same-UID test fixture, not a protected source service.** Script/unit file hashes and a Unix socket pathname do not prove systemd launched that script or that it possesses a private signing key. A same-UID attacker can fabricate a new directory, choose its own policy and keys, and satisfy these tests. Real service authorization requires a distinct locked-down UID, externally controlled policy enrollment and service manager evidence.
- A path, mode or file digest can change after the last precommit check; there is no atomic kernel+filesystem+SQLite transaction. The script can also execute additional mutable imports/assets; checking two files does not attest an entire process image or package.
- The fixture uses private `0700` root and `0600` files/socket for narrow tests. This is **not** a universal systemd policy. Production socket activation, full service-unit content/cgroup identity, script/library measurement and immutable verified package release floors remain source-owner/security review work.
- The policy's expected UID/GID refers only to the CI fixture's user; **no dedicated Weather/research service UID is created**.
- The V2m private synthetic SQLite fixture is not the real ArchiveStore. The broker cannot write production snapshots, bypass quotas, sign archived provenance or grant any Restore/Burn rights.
- The V2p predecessor is an open draft PR. This V2q change is **stacked on V2p**, not an independent replacement. If V2p merges, retarget V2q only after checking current main and the exact diff. Do not merge either without the required operator authorization.
- MACHINE/Weather/research/Connections have separate Room authority. No keys, services or files in their ownership have been changed.

## CHECKLIST

- [x] V2p CI baseline, current main, Hospital protocol and concurrent ownership verified
- [x] Read-only unit/script/socket test policy; symlink/hardlink/inode/permission checks
- [x] Signed fixture peer and source-service digest bound into synthetic atomic receipt
- [x] Final precommit recheck of both pidfd and service-file evidence
- [x] Synthetic adversarial unit/socket/file and rollback tests
- [ ] Full CI and fixes
- [ ] Independent security review and Weather/research+MACHINE owner interface approval
- [ ] Operator merge/host deployment decision

## NEXT // V2r Implementation

**Source-owned protected service authorization handoff** with a separately authorized demo owner: independent service-manager/cgroup/unit measurement, distinct source UID, protected socket activation and key custody, trusted time and authority-pinned signer release history. Implement a separately reviewed real ArchiveStore quota/nonce/provenance transaction only after these ownership boundaries are verified. Do not create live keys, production services or Restore/Burn permissions from this test fixture.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2q-fixture-service-files-20261111  
BASE // V2p branch feat/trashpp-v2p-peer-lifecycle-lease-20261111 while PR #1897 is open  
STATE // GitHub stacked draft only, not live Hospital registered; no local host/Archive changes  
ROLLBACK // Revert V2q new fixture checker, optional service-file callback and additive *test-only* SQLite service witness field. Preserve existing V2p code, V2o socket fixture and all actual Archive snapshots and receipts.
