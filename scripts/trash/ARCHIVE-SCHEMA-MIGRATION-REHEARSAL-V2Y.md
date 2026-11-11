# Trash++ // V2y Actual ArchiveStore Schema Migration Rehearsal

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External DOC-compatible GitHub worker; not verified live Hospital registered  
ASSIGNMENT // Rehearse atomic signed admission against actual ArchiveStore SQLite schema without enabling production access  
SCOPE // scripts/trash, tests/trash, documentation; GitHub-only draft PR. No host file write, live Archive migration, source signer, key activation, protected source reads, Restore, retention or Burn permission.

## IMPLEMENTATION

- New `scripts/trash/archive_v2y_archive_schema_rehearsal.py` with `TestArchiveStoreAdmissionV2y` accepts only an exact `ArchiveStore` instance in a separately created, private `0700` directory named `trashpp-v2y-fixture-*` with an existing private fixed-content `trashpp-v2y-fixture-only.marker`. It neither creates that marker nor provides a CLI, daemon or Quickshell integration. It uses the **actual** `trashpp-archive-v2.sqlite3` and existing `archive_meta`, `snapshots`, `snapshot_receipts` schema, but **only inside the test fixture directory**.
- A schema migration transaction adds **only a fixture-only** `fixture_signed_admissions` table linking a snapshot ID to one-time owner/key/nonce, source proof digest, signed receipt digest, signed claim, signature and V2w floor hash. `fixture_admission_meta` declares its own test-only migration schema; existing rows are left untouched and never backfilled as signed. Repeated rehearsal requires the exact same schema and fails closed on incompatible columns/versions.
- The admission method verifies a signed V2k `TEST_FIXTURE_ONLY` source claim and a separate signed V2x receipt under an independently provided test key, binding owner, source revision, SHA-256 payload, snapshot ID, one-use nonce, source proof, display label, timestamps, prior V2i local receipt, and current V2w signed release floor. It refuses any production policy origin or proof claiming capture authority.
- One `BEGIN IMMEDIATE` transaction, using the real `ArchiveStore._connect()` and quota model, checks actual existing payload counters/disk pages and chain predecessor, then inserts a new record into `snapshots`, its normal **UNSIGNED_LOCAL** V2i receipt into `snapshot_receipts`, the fixture-only signed admission/nonce row, and updates real `archive_meta` revision/payload bytes. The V2w floor is checked at preflight and just before COMMIT. A refusal anywhere before commit rolls every new row and counter back; no existing copy is removed or modified.
- Read-only recovery `inspect(owner,key,nonce,receiptKey)` verifies stored payload hash, V2i local receipt, signed V2x fixture receipt and all owner/source/nonce/floor bindings without exposing payload bytes. An already-consumed nonce cannot be replayed after reopening even if the response was lost after COMMIT. Missing underlying snapshot/receipt for an existing signed nonce is corruption, not an ordinary absent snapshot.
- All success remains `sourceAuthorityVerified=false`, `archiveCopyAuthorized=false`, `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false`, `burnAllowed=false`. The existing user-facing `ArchiveStore.save()`, capture CLI, camera, capacity bar, VERIFY CHAIN, Restore and Burn remain unmodified.

## HOW TO USE

No new desktop button, install or local migration. CI alone creates a named private disposable root and a marker, initializes a normal ArchiveStore, stores an older unsigned-local fixture snapshot, and rehearses additional signed-test admissions in that very same database. The existing regular `ArchiveStore.read_verified()` and status queries must still read both old and new records. All private Ed25519 signing keys and signed owner release floor material are ephemeral fixtures.

## VERIFY

Automated tests cover preservation and readable status of legacy V2i receipts; no retroactive signed-attestation flag on older records; atomic real-schema signed copy+nonce+receipt+counter; replay refusal; fault injection after each transaction stage; lost postcommit reply and reopening; payload/disk quotas including existing records; floor revocation during precommit guard; signed label/payload mismatch; source revision uniqueness; corrupted signed receipt/payload and orphaned nonce; required private named marker and unsafe root rejection; incorrect preexisting migration table version; absence of CLI/live owner access. Full Trash Python, 40 JS Camera/snapshot/capacity/chain/Burn and Meta Apollo Grammar CI required.

## WATCH OUT FOR

- **Not a production migration.** The new table name is explicitly `fixture_signed_admissions`. The adapter refuses ordinary Archive directories lacking the test-only marker and is never imported by the live CLI/widget. These safeguards limit accidental use, but the marker is not itself a cryptographic privilege boundary; production authorization still requires owner-approved protected identities and independent policy.
- Existing ArchiveStore V2i receipts are **unsigned local SHA-256 provenance**, including receipts inserted by V2y into the real-schema fixture. The separately signed V2x test receipt is stored only in the fixture extension and signed by a test key. The current Archive UI VERIFY CHAIN must not be described as verifying cryptographic source authority.
- SQLite atomicity applies to the copied bytes, nonce, receipt and counters in **that one database**. V2w's signed floor file and V2s release history remain external to this transaction, so a release could be revoked after the final read. No protected monotonic authority, signed production consent, trusted clock or cross-system atomicity has been established.
- The fixture tests use test keys, a test-owned floor and a simulated client. They do not authenticate a live Weather/research source service, dedicated UID or protected signer. No genuine data-owner authority or human consent is proven.
- A proper production migration needs an operator-approved schema version/backups/checkpoints, real owner scopes, verified source authority, quarantined invalid rows, safe deployment and rollback, signed receipt-chain migration policy and actual host tests. Do not copy V2y's fixture table into production merely because CI passes.
- No local host files or actual user snapshots were changed; Weather/research, MACHINE, Connections/Identity remain separately owned.

## CHECKLIST

- [x] Rechecked current main, merged V2x, Syntagma AGENTS/Hospital and concurrent ownership
- [x] Implemented test-only extension of existing ArchiveStore schema with one-use nonce and signed receipt link
- [x] Combined real-schema snapshot, V2i receipt, signed fixture admission and quota counters in one transaction
- [x] Added legacy-preservation, crash/lost-reply, quota, replay, corrupt DB and marker safety tests
- [ ] Full GitHub CI green and corrections
- [ ] Independent security review, source owner approval and production migration authorization
- [ ] Operator final acceptance, merge/deployment decisions

## NEXT // V2z Implementation

**Source-authorized production migration gate and rollback review.** Coordinate Weather/research + MACHINE/Connections/Identity owners to approve dedicated signer identities, protected release and revocation authority, trusted time, target schema, backup and crash recovery. Then implement a separately approved live migration that binds actual source receipts, one-use nonces, quota, provenance and copy in a single ArchiveStore transaction with denial on missing owner authority. No real local deployment, Restore, retention or Burn without separate permission.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2y-archivestore-schema-rehearsal-20261111  
BASE // main at branch creation 1639a39ea92a0c2f5ed7617072885179e12e69c3  
STATE // GitHub-only synthetic schema rehearsal; no verified live Hospital worker registration  
ROLLBACK // Revert only new V2y fixture adapter, tests and document. Existing production ArchiveStore schema, all existing user snapshots, UI buttons, protected source services and keys remain unchanged.
