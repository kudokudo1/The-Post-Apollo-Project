# Trash++ // V2p Original-Peer Lifetime Lease (Deny-Only)

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
PROVIDER // OPEN AI // CHATGPT  
STAFF ROLE // External DOC-compatible developer; no live Hospital connection verified  
ASSIGNMENT // Tie V2o signed fixture broker requests to the original connected Linux peer's lifetime until the synthetic nonce+copy commit gate  
PERMISSIONS // Bounded GitHub branch/draft PR, scripts/trash + tests/trash + docs. No owner source/service edits, live host writes, PR merge, signing key provisioning, production activation, Restore or Burn.

## IMPLEMENTATION

- Introduces `archive_v2_peer_lifecycle.py`: acquires a Linux kernel pidfd for the original SO_PEERCRED process identified in V2n's signed fixture broker. The lease compares socket PID/UID/GID, original /proc/PID process start ticks before and after pidfd_open, system boot identity and actual /proc/PID/exe digest. It then polls the pidfd for exit and rechecks start ticks, boot ID and executable before allowing progress. Missing pidfd support, exited/replaced/re-executed peer, wrong socket evidence or unavailable process information refuse; **no polling-only fallback**.
- V2o's single-request synthetic socket handler now obtains the lease **after** parsing the bounded request, and retains it while verifying the source's existing test-only signed claim and writing the isolated fixture. The broker rechecks that the V2n witness matches the initial pinned witness.
- V2m's test-only SQLite `admit_test_copy` now accepts a callback invoked **inside BEGIN IMMEDIATE, after inserting both test nonce and synthetic copy but before COMMIT**. The pinned pidfd lease supplies that callback. If the peer exited or changed, an exception rolls both test rows back. The same harness maintains its existing crash, replay, and lost-reply semantics.
- The lease is closed deterministically even on denial. A successful fixture IPC response can state `peerLifetimeCheckedBeforeCommit=true`, but retains `sourceProcessVerified=false`, `archiveCopyAuthorized=false`, `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false`, and `burnAllowed=false`.
- Adds real child-process exit tests using temporary Unix sockets, plus synthetic commit-point exit checks. The implementation is entirely test-only and never starts a background broker or reads Weather/research source files.

## HOW TO USE

There is no new widget control and no service installation. Existing Trash++ Archive SAVED SNAPSHOT/CONFIRM COPY, VERIFY CHAIN and capacity UI retain their semantics. CI tests use ephemeral signing keys and private synthetic test SQLite directories. On a failed lifetime check the test broker replies with a bounded refusal; a successful test receipt still is not a production permission.

## VERIFY

- Live Linux pidfd checks on the test client: PID/UID/GID and process start ticks anchored to the original socket; closed lease refusal, changed start tick and binary digest refusal, missing pidfd refusal.
- An actual child process exits while its accepted socket remains open: lease must detect exit. Another child sends a complete signed fixture request then exits: broker must refuse, leaving zero consumed nonces and zero copies.
- Commit-boundary injection triggers a simulated peer exit after both SQLite INSERTs but before COMMIT: both rows must rollback and the nonce remain usable.
- Positive signed IPC fixture still returns only DENY_ONLY and preserves existing V2m-V2o crash/replay and payload checksum contracts.
- Full Trash Python, all 40 JS Camera/snapshot/capacity/chain/Burn contracts and Meta Apollo Grammar CI must pass. Independent security/production acceptance remains separate.

## WATCH OUT FOR

- **pidfd is a process-lifetime reference, not source authorization.** Even combined with kernel UID/GID and executable digest, it does not prove a Python script, unit file, source owner, held signing key, human consent, or immutable file contents. `sourceProcessVerified` therefore remains false. A process may change script data without execve; this check would not notice.
- The final pidfd check occurs immediately *before* the test transaction commit; a process can still exit between this check and COMMIT. This is not an atomic kernel+SQLite transaction and does not guarantee the source remains alive after commit. A real protected service needs a separately reviewed authority/lease and loss-recovery protocol.
- The test's peer and root policy are explicit fixtures under the CI user, not independently enrolled live Weather/research authorities. There is still no source-owned signing daemon, dedicated system UID/socket owner, trusted clock, signed unit/script digest, real ArchiveStore atomic receipt or production quota integration.
- No implicit reuse of TimeW MACHINE broker code or Identity Center keys. Those are separately owned protected trust boundaries. No new source owners, Restore, retention or Burn rights.

## CHECKLIST

- [x] Verify V2o merged main, Syntagma AGENTS/Hospital and no competing Trash PR
- [x] Kernel pidfd + incarnation/exec+boot rechecks for original socket peer
- [x] V2o signed fixture handler holds peer lease
- [x] Commit-time lease guard within V2m nonce+copy SQLite transaction
- [x] Real child-exit and fault-injected rollback tests added
- [ ] Green GitHub CI and fixes
- [ ] Independent security review and source-owner handoff
- [ ] Operator merge/installation/production decisions

## NEXT // V2q Implementation

**Protected service identity and signed source-unit provenance contract.** After explicit Weather/research and MACHINE coordination, design and verify a source-owned service with a separate Linux UID, protected socket permissions, pinned service-unit/script/executable integrity, independently enrolled signer key and revocation policy, trusted clock and a crash-safe real ArchiveStore commit. Until those authority gates are satisfied, retain the test-only deny behavior. Do not expand Restore/Burn.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2p-peer-lifecycle-lease-20261111  
STATE // GitHub draft, no verified live Hospital registration or host mutation  
ROLLBACK // Revert V2p lifecycle class, optional test commit guard and tests/docs. The actual V2 Archive schema and all user snapshots remain unchanged. Keep existing V2o wire protocol and V2m independent synthetic tests intact.
