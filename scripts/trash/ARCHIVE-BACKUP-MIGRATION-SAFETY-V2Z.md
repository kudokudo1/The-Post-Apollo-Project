# Trash++ // V2z Verified Backup & Migration Rollback Rehearsal

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External DOC-compatible GitHub developer; no verified live Hospital registration  
ASSIGNMENT // Stage a legacy-preserving ArchiveStore migration from a verified backup and rehearse rollback without touching the source  
SCOPE // GitHub scripts/trash + tests/trash + documentation, private disposable test directories only. No host writes, production ArchiveStore migration, source service, key activation, PR merge, Restore, retention or Burn expansion.

## IMPLEMENTATION

- New `scripts/trash/archive_v2z_backup_migration_rehearsal.py` implements `TestMigrationSafetyV2z`, accepting only a pre-existing `ArchiveStore` in a private 0700 `trashpp-v2z-fixture-*` source directory containing a private fixed-content `trashpp-v2z-fixture-only.marker`. The independently precreated 0700 `trashpp-v2z-backups-*` workspace must be a **separate sibling directory**. No CLI/daemon/widget import; no production roots accepted.
- `seal_backup()` performs a **read-only preflight** on the source SQLite database: full `PRAGMA integrity_check` and `foreign_key_check`, exact existing baseline tables/columns and unique indexes/FKs, schema version, source payload SHA-256, V2i legacy or unsigned-local provenance and chain consistency, revision/accounting totals. Unknown tables, damaged bytes, broken receipt links or unsupported schema refuse before backup.
- Uses the Python SQLite **online backup API** to copy a consistent SQLite database snapshot into a new private filename without overwriting an existing file. Audits the resulting database independently and rechecks the source snapshot digest/revision to refuse concurrent source changes. Only after these agree does it write a private, fsynced canonical JSON manifest containing backup file SHA-256, verified row/content digest, schema version, revision, snapshot count, payload size and backup byte size. The manifest holds no user payload. An incomplete backup without its manifest is not treated as sealed.
- `verify_backup()` rereads the manifest and database, verifies exact artifact ownership/private permissions, raw SHA-256 and full content/relational audit. Manifest/backup replacement, corruption or schema drift refuses.
- `rehearse_schema()` creates a **third** explicitly named private test directory, copies the sealed baseline via SQLite backup, then constructs regular ArchiveStore and the existing V2y **fixture-only** schema bridge there. Validates that new test-only admission tables/constraints were installed while all prior snapshot bytes, hashes, receipts, legacy unattested flags, revision/counters and content fingerprint remain unchanged. The original source and sealed backup are untouched.
- `rehearse_recovery()` creates a **fourth** independent private test directory, restores from the sealed backup, audits all records and counters, and leaves both original and potentially failed staged database untouched. No destructive rollback or overwriting live files.
- All result states are explicitly test-only and return `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false`, `burnAllowed=false`. No source-authority claim, cryptographic signing keys, production Archive migration, service start or actual user Archive mutation.

## HOW TO USE

No new desktop control and no user terminal command. GitHub CI alone creates private disposable original/workspace directories, initializes a synthetic existing ArchiveStore with separate owner records, seals/validates a backup, migrates a stage copy and recovers a separate copy. Existing SAVE SNAPSHOT, capacity bar, VERIFY CHAIN, Camera/GIO and Burn remain unchanged.

## VERIFY

Tests cover two-owner backup sealing, staged additive migration, independent recovery after damaged stage, legacy pre-V2i unreceipted snapshots, interrupted backup before sealing, source change during online backup, staged migration crash, corrupted backup bytes and altered manifest, unknown schema, corrupt payload/receipt, missing marker, symlink/root permissions, repeated staging/backup refusal and deny-only outcome. Complete Trash Python, 40 JavaScript regressions and Meta Apollo Grammar workflow required.

## WATCH OUT FOR

- This is **not a production migration command** and provides no path for installing or applying a migration to the real Archive directory. The marker is a scoped fixture guard, not a production security credential; same-UID attackers can still modify all test files. All tests are on disposable directories under CI.
- Backup manifests contain **unkeyed SHA-256**, not owner-signed or off-host authenticated evidence. A same-UID attacker able to replace both backup and manifest could forge consistency. Production backup custody requires an independent trusted destination, atomic retention, versioning, access controls and operator-approved restoration.
- A consistent SQLite online backup does not prove that every external source released/revoked a grant at the same point in time. The V2w external floor file, V2s test release history, systemd identity and ArchiveStore SQLite are still separate. No trusted clock, protected private keys, source-owner approvals or production nonce signing policy.
- The preflight deliberately **refuses unknown schema extensions**, instead of guessing how to migrate them. Real deployment needs a separately approved compatibility matrix, protected preflight, signed migration contract and exact rollback/switchover plan, including handling concurrent Archive writers without losing new snapshots.
- The V2y signed admissions remain synthetic `fixture_signed_admissions`; local V2i receipts remain unsigned. Rehearsing V2y from a verified backup does not create real signed source authentication or authorize capture.
- A real rollback cannot simply overwrite a database while other writers run. This test demonstrates isolated backup restoration only, never a live hot-swap, restore, retention or Burn. Native Silverblue filesystem/SELinux and storage-failure tests and independent security review remain required.
- Weather/research, MACHINE and Connections/Identity owners are unchanged. This session did not access their service keys, real data or host services.

## CHECKLIST

- [x] Latest main/V2y status, Syntagma AGENTS/OPERATE and concurrent ownership inspected
- [x] Private source/workspace and marker guards
- [x] Full preflight integrity/foreign-key/schema/accounting/provenance audit
- [x] SQLite online backup with content digest, stable-source check and sealed manifest
- [x] Independent staged V2y additive migration and separate non-destructive recovery
- [x] Failure injection / corruption / legacy preservation regression tests
- [ ] GitHub CI result and correction if needed
- [ ] Independent production backup/security and source-owner review
- [ ] Operator decision on PR merge, any actual host migration and system activation

## NEXT // V3a Planned

**Source-owner authorization and real production migration readiness.** Obtain explicit Weather/research, MACHINE/Connections and operator approvals for a dedicated source identity, protected signing key, remotely anchored monotonic release/nonce ledger and trusted time. Design a signed migration manifest, actual externally protected backup with cutover/freeze semantics, and a reviewed rollback that never discards concurrent writes. Only then implement real ArchiveStore nonce/signed receipt/quotas and UI activation. Restore/retention/Burn remain separate.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2z-migration-backup-rollback-fixture-20261111  
BASE // main 7d3d214e87eab93ca24fb77dbcf38467eb212766  
STATE // GitHub-only disposable migration rehearsal; no verified live Hospital Worker attachment  
ROLLBACK // Revert only V2z module, tests and this document. No actual ArchiveStore, user snapshot, source-owned key/service or Quickshell file was changed.
