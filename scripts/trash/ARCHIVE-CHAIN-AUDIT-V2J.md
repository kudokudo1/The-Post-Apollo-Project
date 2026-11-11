# Trash++ // V2j Full Read-Only Provenance Chain Audit

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle
STAFF ROLE // External DOC-compatible development; no verified live Hospital registration
ASSIGNMENT // Database-wide V2i receipt-chain audit and signed-owner authorization boundary plan
PERMISSIONS // GitHub branch/draft PR/tests/docs only. No local writes, merge, production activation, signing, Restore or Burn authority.

## IMPLEMENTATION

- Adds scripts/trash/archive_v2_chain_audit.py with exactly one read-only CLI verb, audit. Uses the same strict private Archive location selector as V2i; SQLite mode=ro&cache=private, PRAGMA query_only=ON, and one pinned read transaction. No original source files or payload bytes are read or returned.
- Scans all current stored snapshot metadata in insertion order, limited to 100,000 rows. It verifies each receipt against stored metadata, compares every previousReceiptHash with the immediately previous V2i receipt in the same owner/resource history, rejects orphan/missing/different-source links, metadata tampering, duplicate receipts and unexpected legacy records after local receipt history began. Excess records result in refusal, never a partial success.
- Supports a pristine V2a database without modification, counting existing legacy records separately from newer receipts. A partial schema migration fails closed.
- Returns snapshot, receipt, legacy, and source counts alongside explicit UNSIGNED_LOCAL, DATABASE_LOCAL_ONLY and payloadVerified=false status. A consistent chain is not a source signature or payload verification.
- Adds an on-demand VERIFY CHAIN button within ARCHIVE beside REFRESH, with a status line below the real capacity bar. The scan is never automatic on every search, never opens a new window and never grants deletion or restore permissions. Refreshing the Archive index resets the previous audit result to NOT AUDITED.
- Keeps Camera, GIO, V1 managed Burn and original Weather/demo source writers unchanged.

## HOW TO USE

After authorized merge/host deployment: Trash++ > ARCHIVE > VERIFY CHAIN. The resulting status distinguishes LOCAL CHAIN CONSISTENT // UNSIGNED, LEGACY ONLY, NO ARCHIVE DATABASE or explicit FAILED error. The counts cover the entire V2 store, not just the current filtered page. REFRESH invalidates previous audit results. A successful full-chain result never implies payload bytes were verified.

## VERIFY

Synthetic Python tests cover multi-source predecessor and cross-source links, missing/orphan receipts, recomputed-but-skipped predecessors, malformed metadata, preexisting V2a database nonmutation, legacy-after-receipt gaps, bounded refusal, isolated Python execution and no destructive verbs. JavaScript tests execute real QML audit request/response functions, check read-only-only invocation, falsified response refusal, legacy handling and status placement. Full existing Trash Python/JS and grammar CI must pass; native four-size visual testing and independent security review remain separate.

## WATCH OUT FOR

- SHA-256 receipts are UNSIGNED LOCAL evidence, not authenticated or tamper-proof. A program able to rewrite SQLite can recalculate them; deletion of an entire source chain or a consistently rewritten database cannot be detected without an external trust anchor.
- This checks consistency among records in a single local database transaction. It never fetches payload bytes, proves source consent, authenticates process identity, or certifies Restore readiness.
- The source chain uses SQLite insertion order, matching the existing V2i writer. It is not an independently signed sequence or external event log. Source-specific signed authorization remains a separate design and approval gate.
- The operation refuses to claim success beyond 100,000 records. It never automatically deletes, vacuums, migrates, or rewrites a store.
- No original Weather/demo source mutation, protected Hospital/Identity ownership, new Restore or Burn controls. No claim of desktop installation from GitHub source alone.

## CHECKLIST

- [x] Current V2i merged main and competing Trash ownership verified
- [x] Full read-only chain audit in bounded SQLite transaction
- [x] Legacy no-receipt semantics and fail-closed errors
- [x] Separate on-demand VERIFY CHAIN and honest status label
- [x] Synthetic backend/UI tests and CI workflow wiring
- [ ] Final CI pass / corrections
- [ ] Independent security and native visual acceptance
- [ ] Operator-authorized merge/install

## NEXT

V2k // Signed Source-Owner Capture Authorization. Plan an owner-signed statement binding source identity, stable resource ID, normalized payload checksum and revision, authorized request scope, timestamp and replay-resistant challenge; the verifier must consult an authority-pinned key and durable replay/consumption record. Signing is not human consent. Integrate only after ownership/permissions and trust-floor review, then later establish separate controlled Restore, retention and Burn contracts. V2j does not generate keys or sign requests.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-provenance-chain-audit-v2j-20261111
STATE // GitHub draft, no verified Hospital registration, no host writes
ROLLBACK // Revert only the V2j CLI, UI, tests and docs; all V2i SQLite snapshots, receipts, capacity and source owners remain unchanged.
