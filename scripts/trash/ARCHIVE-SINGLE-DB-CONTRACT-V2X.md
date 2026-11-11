# Trash++ // V2x Single-Database Signed Capture Commit Contract

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External DOC-compatible GitHub development; not verified live Hospital registered  
ASSIGNMENT // Model a recoverable, quota-limited one-use signed capture commit in a single disposable SQLite database  
PERMISSIONS // scripts/trash + tests/trash + docs; bounded GitHub draft. No local host mutations, protected source changes, production keys, PR merges, real ArchiveStore writes, Restore or Burn.

## IMPLEMENTATION

- Added `archive_v2_single_db_fixture.py`, a **test-only** SQLite writer confined to an explicitly caller-owned private `0700` directory whose name begins `trashpp-v2x-fixture-`. Its database filename is always `trashpp-v2x-test-archive.sqlite3`, **not** the real `trashpp-archive-v2.sqlite3`. It refuses fixture roots containing the real archive DB. No CLI, Quickshell import, source file reader, service daemon or real ArchiveStore import is provided.
- Strictly checks an Ed25519 signed V2k **TEST_FIXTURE_ONLY** source-capture claim and an independently signed V2x test receipt. Both signatures use externally supplied ephemeral test public keys (enforced distinct), and the signed receipt binds: snapshot ID; owner/resource/revision; source/archive timestamps; display label; payload SHA-256; source key/nonce/proof SHA-256; the V2w external release floor SHA-256; and the preceding local V2i receipt SHA-256. No signing operations are performed in the writer.
- Requires a real `ReadOnlyExternalFloor` object in TEST_FIXTURE_ONLY mode and a V2s `TestServiceReleaseHistory`, with independently pinned test root. It calls V2w `require_current` **before** admission and **inside** the database transaction immediately before commit. A missing/revoked/stale/replaced/changed checkpoint refuses.
- Within one `BEGIN IMMEDIATE` SQLite transaction, checks one-use nonce, source revision uniqueness and payload quota; inserts the nonce, immutable synthetic payload, local V2i SHA-256 provenance receipt, separately signed test receipt, and updated revision/payload counters. Uses DELETE rollback journaling, `synchronous=FULL`, database page cap and physical main-file/journal charging for disk budget. A refusal at any injected precommit stage rolls all records and quota accounting back.
- Supports a deliberately injected failure *after* `COMMIT` (lost response). Read-only `inspect(owner,key,nonce,pinned_test_receipt_key)` verifies the persisted payload digest, recomputed local V2i receipt, signed receipt and exact identity bindings without returning payload bytes. A replay of that consumed nonce is refused. Missing receipt/copy for an existing nonce is **corrupt**, not mistaken for a clean absence.
- No actual source authority, authentic trusted time, independently controlled protected nonce store, production receipt signing key or atomic coupling between the V2w external file and SQLite has been established. Every result remains `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false`, `burnAllowed=false`. Synthetic signatures prove a *test* contract, not a right to copy live owner resources.
- Existing real `ArchiveStore.save()` already implements payload, disk and unsigned V2i receipt writes in one transaction; V2x mirrors its general accounting contract without modifying any real ArchiveStore schema or the user-facing pilot.

## HOW TO USE

No new Trash++ widget control or desktop installation. GitHub CI creates an isolated temporary V2w signed-floor fixture, ephemeral owner and receipt Ed25519 signers and a separate V2x private test SQLite file. Tests inject failures before/after commit and reopen the database to simulate lost replies. Existing Archive SAVE SNAPSHOT, capacity bar, VERIFY CHAIN, Camera/GIO and Burn are unaffected.

## VERIFY

Adversarial tests cover initial signed single-db commit and payload-free recovery, consumed nonce rejection, exceptions after nonce/copy/receipt/accounting writes, lost reply after commit and idempotent recovery after reopening, payload and disk quotas, forged source and receipt signatures, altered label, expired/revoked/changed external floor at initial and final guard, immutable local receipt chain and wrong predecessor, corruption of stored payload/signed receipt, missing receipt for consumed nonce and real Archive DB isolation. Full Trash Python, 40 JS Camera/snapshot/capacity/chain/Burn and Meta Apollo Grammar CI required.

## WATCH OUT FOR

- **Not production code:** only ephemeral CI-owned fixture files and keys. V2x accepts signed TEST_FIXTURE_ONLY evidence and a same-user TEST floor, not real source service policy, owner consent or protected production public keys. No production copy permission is exposed.
- The V2w authority floor is in a **separate file** and the V2s release DB remains separate. Final precommit rechecks can still race an external authority change after the check; one SQLite transaction cannot atomically commit remote/other-filesystem authority. A production integration needs signed acceptance tokens with explicit leases, revocation handling, and a separately reviewed recovery protocol.
- `ArchiveStore` uses its own production schema, display/UI and actual disk accounting. This fixture demonstrates nonce/receipt/quota atomicity but does **not** migrate the user's Archive schema, provision signed provenance or guarantee compatibility until a separately authorized integration review.
- The synthetic signed receipt's public key is supplied by the test harness. There is no approved source-owner authority, secure key lifecycle, trusted clock, protected service identity or human consent. Its cryptographic validity does not make a real capture legitimate.
- Physical disk checks are conservative precommit checks, not reservations against unrelated host writes. The test database's journal/disk budget is not a final production storage-limit implementation.
- No source-owner files/services or GitHub workflows owned by MACHINE/Weather/research/Connections are modified. No Restore, retention or Burn permissions are expanded.

## CHECKLIST

- [x] Reconcile current main/V2w merge, Hospital AGENTS/OPERATE and active ownership
- [x] Separate test-only SQLite schema with atomic nonce/payload/local+signed receipts/quota
- [x] V2k fixture claim verification and independent test receipt signature
- [x] V2w signed floor preflight and final precommit recheck
- [x] Crash-window, replay, quota, chain, recovery and corruption tests
- [ ] CI green and any corrections
- [ ] Independent security/source-owner/Connections review
- [ ] Operator final acceptance and any explicit production/host authorization

## NEXT // V2y Implementation

**Production admission prerequisites and owner handoff.** With explicit Weather/research, MACHINE/Connections and operator approval, define a source-owned signing service with trusted time and protected policy release/nonce authority, an authenticated unit/process identity and a separately protected append-only release floor. Then make an authorized `ArchiveStore` schema migration that puts actual nonce, snapshot, quota, signed provenance and revocation/recovery semantics in one reviewed database transaction, with launch/rollback plan and native UI verification. Keep Restore/Burn separately gated.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2x-single-db-commit-fixture-20261111  
BASE // main `5556ae87068066014e369b075633f908666a155b`  
STATE // GitHub-only fixture development, no verified live Hospital attachment/production rights  
ROLLBACK // Revert V2x standalone fixture writer, its tests and this document. The actual `ArchiveStore` SQLite schema, every user snapshot, current Weather/research source and Trash++ UI remain unchanged.
