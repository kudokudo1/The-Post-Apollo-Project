# Trash++ // V2i Snapshot Provenance & Integrity Metadata

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // DOC-compatible external development (live Hospital registration not verified)  
ASSIGNMENT // Source/capture evidence binding for future V2 snapshots, backward compatible with existing copies  
PERMISSIONS // GitHub branch + draft PR + tests only; no host mutation, merge, production activation or Restore/Burn expansion.

## IMPLEMENTATION

- Introduces a versioned, deterministic `archive_v2_provenance.py` receipt: snapshot ID, allowlisted owner identity, stable resource ID, source revision, **source timestamp** (when the owner observed the item), **Archive timestamp** (when this copy was stored), display label, SHA-256 payload checksum, and optional previous receipt digest for the *same* owner/resource. A canonical UTF-8 JSON encoding is hashed with SHA-256. Receipt schema: `post-apollo.trash-archive.receipt.v2i`.
- Adds `provenance_required` flag to the existing V2 SQLite snapshots table (defaults to 0 for old data), plus `snapshot_receipts` table. On each **new, explicitly confirmed** copy, the snapshot, receipt and quota accounting are committed in **one SQLite transaction**. Duplicate source revisions remain refused and historical V2 copies are never overwritten.
- Existing V2a database layout is migrated additively when the ArchiveStore writer opens it. Old saved snapshots retain `provenance_required=0`, remain payload-readable, and are displayed **LEGACY_UNATTESTED**. They are *not retroactively certified or fabricated*.
- New copies set `provenance_required=1`. If their receipt is absent, malformed, or its bound metadata has changed, the read-only index refuses to display an apparently healthy partial page. `read_verified` and full `verify` also check metadata provenance before validating payload SHA-256.
- V2c read-only Archive index understands both untouched V2a databases and new V2i databases. It verifies each receipt against listed metadata without reading payload bytes; UI details identify `RECEIPT ... // PAYLOAD NOT VERIFIED` or `LEGACY // NO RECEIPT`. Normal read-only Archive row permissions remain unchanged.
- A new snapshot's capture receipt returns provenance including the actual Archive time and previous receipt hash. Future same-resource snapshots link to the preceding V2i receipt; unrelated sources are not joined.
- No new service, timer, management button, migration wizard, source scanner or generalized owner adapter. Existing Weather/demo source witness checks, SQLite capacity limit, V1 managed copies, Camera/GIO Trash and Burn operations stay in their assigned lanes.

## HOW TO USE

After separately approved merge and desktop installation:
1. Trash++ > ARCHIVE > choose an approved Weather event or demo-research item > SAVE SNAPSHOT > CONFIRM COPY. A new V2 snapshot receives a provenance receipt atomically.
2. Under ALL/COPIES, new read-only snapshots show a short receipt indicator; older snapshots show LEGACY // NO RECEIPT. Archive list retrieval validates the receipt *metadata*.
3. The receipt records both the source-observed timestamp and actual saved-to-Archive timestamp. Copies with malformed/missing required receipts fail closed, not silently presented as verified.
4. Read-only Archive search remains global over V2 stored metadata. A listing never reads payload content or claims that an archive is restorable.

## VERIFY

Synthetic tests cover deterministic hashes; exact source/owner/label/sha/time binding; previous same-source digest lineage, no cross-source lineage; read-only receipt display and no payload leak; altered metadata/receipt and missing receipt refusal; explicitly corrupted payload remaining unverified at the index layer and rejected by `read_verified`; additive legacy V2a schema upgrade and old-copy readability; never backfilling a fake receipt into older records. Run full Trash Python, Camera, snapshot preview/confirm, real capacity gauge and Burn regression suites, plus Meta Apollo Grammar CI.

## WATCH OUT FOR

- **SHA-256 receipt is UNSIGNED LOCAL EVIDENCE, not authenticated provenance.** A malicious same-UID process or SQLite writer can rewrite database rows and recompute SHA-256. This does not prove who operated a source, who consented, that a protected original was authentic, or that a copy can be restored. Source-specific signed authority must be designed and authorized separately.
- The read-only index verifies metadata consistency; it never reads a snapshot payload. `verified:false` and PAYLOAD NOT VERIFIED remain accurate until an explicit full payload audit.
- Each `previousReceiptHash` is an informational same-source predecessor pointer. The index validates the current receipt hash but does **not** walk an entire chain or attest that no receipts were removed. No global signed append-only ledger is claimed.
- V2a schema migration occurs only when an ArchiveStore writer opens a DB. The read-only index can still list a pre-migration V2a store without mutating it.
- Records with missing or invalid `provenance_required=1` receipts fail closed; legacy `provenance_required=0` remains explicitly unattested. An attacker controlling the DB can also tamper with the flag; future signed authority is required for a stronger security boundary.
- No Restore, Trash, Burn, retention or automatic migration permissions are granted to V2 read-only copies. Capacity bar and quota limits still apply.
- Native Quickshell four-size visual acceptance and independent security review remain distinct from CI.

## CHECKLIST

- [x] Checked merged V2h capacity bar and current GitHub ownership
- [x] Canonical V2i receipt codec with explicit UNSIGNED_LOCAL status
- [x] Atomic receipt + snapshot and previous-source lineage pointer
- [x] Additive legacy schema transition with no retroactive receipts
- [x] Metadata read-only index validation and read_verified integrity checks
- [x] Synthetic tamper, legacy, source-linkage and payload tests
- [ ] GitHub CI and any corrections
- [ ] Independent security review and native four-size UI verification
- [ ] Operator-authorized merge / deployment / acceptance

## NEXT

**V2j // Provenance audit and signed-owner authorization planning**, including complete same-source lineage verification and owner-approved capture identities. This will remain read-only until each source's protected consent/verification contract exists. Later: controlled Restore, retention and Burn receipts under separate permissions.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-snapshot-provenance-v2i-20261111  
STATUS // Draft GitHub change only; no live host writes/merges.  
ROLLBACK // Revert the feature code, but do not delete any created snapshot or receipt rows. Because V2i evolves the schema additively, rollback of code does not undo the SQLite DDL; future readers must preserve these tables/flags or follow a separately approved migration strategy. Existing V2a payload data is preserved.
