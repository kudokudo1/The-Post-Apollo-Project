# Trash++ V2m // Atomic Signed Capture Admission (Fixture Only)

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Archive Lifecycle
STAFF ROLE // External DOC-compatible development; no verified live Hospital registration
ASSIGNMENT // Crash-safe nonce/snapshot admission proof, within Trash++ owned test seam
PERMISSIONS // GitHub draft PR/tests/docs only. No local host writes, source-owner key custody, native services, merge, activation, Restore or Burn.

## IMPLEMENTATION

- Extends existing V2l private synthetic trust history with a fixture-only test_copies table. Signed public-key enrollment and current generation remain under the same test-ledger trust policy.
- New archive_v2_atomic_admission.py verifies the existing test-root signed owner enrollment and Ed25519 source-claim signature before attempting storage. It checks the exact in-memory payload SHA-256 and original source timestamp. It does not read Weather/demo source files, accept arbitrary paths, or load keys from disk.
- TestOwnerTrustHistory.admit_test_copy validates the current enrolled key generation and revocation, then consumes the nonce and writes a synthetic immutable copy **within one SQLite BEGIN IMMEDIATE transaction**. Both modifications commit together. Exceptions before commit roll back both. No ArchiveStore, production SQLite or Quickshell path is touched.
- A read-only inspect_test_admission lookup resolves the nonce after a lost reply: NOT_ADMITTED if both writes rolled back, COPY_COMMITTED if both committed, or NONCE_WITHOUT_COPY for older V2l test-only nonce records that were never actual snapshots. It returns only fixed metadata and digests, never payload bytes.
- Fault hooks model exceptions and actual process exits after nonce insertion, after synthetic copy insertion, and immediately after commit. Recovery uses a newly opened SQLite connection to prove that crashes cannot create a committed nonce without its new V2m test copy or permit replay of a committed request.
- Results stay strictly TEST_*_DENY_ONLY, with captureAllowed, sourceAuthorityVerified, trustedTimeVerified, humanConsentVerified, restoreAllowed, burnAllowed and productionAllowed all false.
- The existing ArchiveStore, UI capacity bar, SAVE SNAPSHOT/CONFIRM COPY, VERIFY CHAIN, V2i unsigned receipts, Camera, GIO and Burn paths remain unmodified.

## HOW TO USE

There is NO new operator button or production capture service in V2m. This implementation runs only in synthetic GitHub CI fixtures. Existing Trash++ UI behavior remains unchanged.

The fixture admission caller validates an in-memory owner-signed claim against an independently pinned synthetic trust root and an enrolled key; it then atomically saves a synthetic copy and consumes the nonce in a private test SQLite ledger. The recovery lookup distinguishes interrupted uncommitted work from committed work whose reply was lost.

## VERIFY

Tests cover:
- Valid test authority and signed source claim still DENY real capture
- Exact payload checksum, source timestamp and source identity binding
- Nonce replay refusal across independent ledger reopen
- Exception rollback after nonce and after copy insertion
- Real abrupt subprocess exit (os._exit) at both stages and immediately after commit
- Receipt loss after commit: durable copy and nonce survive, retry is refused, read-only witness recovers ID
- Invalid signature / revoked or stale enrolled key refusing before any test copy is written
- Older V2l nonce never reported as a stored test copy
- No live Archive DB, source file, Quickshell process, Restore or Burn code path
- Existing full Trash Python, JavaScript, and Meta Apollo Grammar regressions must pass.

## WATCH OUT FOR

- **The prototype is not actual protected source signing**. The source owner is simulated using ephemeral test keys. There is no running Weather/demo signer, verified process identity, trusted clock, production trust root, human consent or real owner authorization.
- This solves atomic nonce + payload inside **one test SQLite database only**. The actual ArchiveStore and V2l test ledger are separate; no cross-database atomicity is claimed. Never wire this fixture into a real capture to bypass source-owner approval or existing V2a quota/write protections.
- A real production broker must enforce dedicated OS service identities, secured signer/key custody, installed crypto dependencies and authority-pinned trust history. Only a separately authorized design can choose a shared transactional database/ledger, brokered commit or recoverable two-phase protocol for the live Archive.
- The recovery witness is not evidence of off-host backup, signed Archive payload provenance or restored source functionality. A same-UID attacker and database replacement remain outside this synthetic test assurance.
- A test-only database may already include consumed nonces from older V2l fixtures without snapshot rows; the new lookup labels them NONCE_WITHOUT_COPY and never treats them as captured files.
- No merge, native deployment or production activation has been authorized by this session. Source owners retain their separate file/room ownership.

## CHECKLIST

- [x] V2l merged, main/current ownership and canonical Hospital protocols checked
- [x] Test-only atomic nonce + synthetic copy under one private SQLite transaction
- [x] Exact signed claim/source revision/payload and enrolled key validation
- [x] Crash-recovery lookup for lost reply vs uncommitted work
- [x] Synthetic fault injection and real subprocess hard-exit tests
- [ ] GitHub CI final green and any corrections
- [ ] Independent security review and source-owner approval
- [ ] Operator-authorized merge, host deployment and eventual production design

## NEXT // V2n Implementation

Design and implement the **source-owned service handoff** after explicit Weather/demo owner approval: a dedicated signer with externally enrolled public key, protected key custody and verified host process identity, followed by a separately approved Archive broker that uses this atomic admission contract for real data. Integrate quotas, signed receipt provenance and crash recovery without allowing direct Quickshell/Brave or ordinary desktop processes access to protected credentials. Restore and Burn remain separate future assignments.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-atomic-capture-admission-v2m-20261111
STATE // Test-only deny gate; no live source, authorization or data changes
ROLLBACK // Revert only V2m test ledger addition, orchestrator, tests and docs. Existing V2l fixture trust rows, production V2 Archive, stored snapshots, V2i receipts and current GIO/V1 Burn functions remain unchanged. Do not delete users' snapshots.
