# TimeW M8 // Durable local fractional attempt journal

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE / Scope A  
**ROLE //** TimeW owner DOC, external Hospital-compatible; live registration unverified  
**STATE //** Source/CI-only, no live Save integration  
**PRODUCTION RESTORE // HOLD**

## IMPLEMENTATION

M8 extends the merged M7 read-only outcome observer. The original ordinary V1/V2 checkpoint must already exist. The separate private SQLite file v3-local-fractional-attempts.db retains an original local fractional admission attempt: generated v4 UUID, M7 checkpoint fingerprint, canonical candidate fingerprint, complete sorted window metadata and exact CURRENT binary64 words. A single transaction persists PREPARED_HOLD before any future dispatch; the journal itself never dispatches.

The only phase transition is PREPARED_HOLD to DISPATCH_MARKED_UNKNOWN_HOLD. The explicit marker operation rechecks the original checkpoint/candidates against M7, requires observed absence of v3 rows, compares the original retained row inside a write transaction and commits the phase change exactly once. This is a record of a marker, not evidence that a write executed or authorization to execute one. There is no marker-to-writer bridge, reset, automatic retry, deletion or undo. The caller must still implement a separately reviewed freshness and dispatch contract.

Ordinary local durability: SQLite rollback-journal mode, synchronous FULL, private directory/file preflight, exact schema check, bounded payload, canonical record digest, unique checkpoint/attempt keys, maximum 64 retained attempts. No silent eviction at capacity. The canonical digest detects accidental payload inconsistency, not malicious same-user editing. The phase is mutable local metadata, not authenticated history. No claim of hardware rollback resistance, power-loss acceptance or atomic coordination across the three databases.

## HOW TO USE

Development API only. With an already saved checkpoint and explicit complete exact candidate set, instantiate LocalFractionalAttemptJournal(suggested_path()), call prepare(checkpoint_id=..., observations=..., store=...), retain the returned ID or discover it with list_ids() if the response was lost, and inspect get(id). record_dispatch_marker(id, store=...) records only a local marker. recover(id, store=...) observes both original stores using the retained original binding and candidate values, rechecks journal row consistency, never changes the phase and always requires manual review. No existing widget button calls this API.

Every outcome remains ordinary local data with automatic retry, source authentication, verified attempt/dispatch, C5, native receipts and Restore authority false. Matching rows with a PREPARED marker may be a different writer's work. Absence after DISPATCH_MARKED does not prove no write happened. No action is authorized by any readback.

## VERIFY

Real disposable SQLite integration and child processes abruptly exiting with os._exit after durable preparation, after marker commit before any write, and after a separate test-only M6 commit whose response is discarded. Check recovery of original UUID and bits, duplicate/refused marker, changed checkpoint, pre-existing matching or partial external writes, no replay, unchanged prior databases, context isolation, unsafe permissions, schema/payload refusal and bounded capacity. These are abrupt process-exit tests at explicit post-commit boundaries, not power-loss tests or interruption mid-transaction.

Require independent Nurse 2 exact-head review before operator merge. Existing M7/M6/M3/M4/M5 and V2 storage/journal regressions must remain green.

## WATCH OUT FOR

This does not solve loss of the initial V1/V2 Save response: the older writer generates the checkpoint UUID at commit time. A future original Save-attempt correlation must establish a preallocated attempt/checkpoint identity or same-database atomic association before that write. Nor does M8 supply genuine native fractional observations. M7's independently read local stores cannot prove an atomic snapshot, and same-user mutable files cannot prove original native observation, protected consent or source authenticity.

## NEXT / DECISIONS

Next separately reviewed boundaries: initial V1/V2 Save identity/correlation and genuine fractional source contract with SwayPX; then explicit Save orchestration and truthful partial-result display. No host installation, UI polish, protected Restore, or other workers' code changes. Local ordinary storage now, protected independent hardware/NAS later.
