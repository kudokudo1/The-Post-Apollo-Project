# TimeW M9 // Original local Save identity

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE / Scope A  
**ROLE //** TimeW owner DOC, external Hospital-compatible; live registration unverified  
**STATE //** Development API only, no active Save wiring  
**PRODUCTION RESTORE // HOLD**

## IMPLEMENTATION

The existing ordinary Save allocates its checkpoint UUID inside save_pair. Loss of the response after commit can leave the caller unable to distinguish the original checkpoint from another Save. M9 adds an explicit alternative local transaction API, not a change to the active Save bridge.

The caller allocates a v4 UUID (also the intended checkpoint primary key), retains it before prepare and supplies the validated V1/V2 pair. prepare persists that identity and a digest binding the exact canonical serialized pair in an additive table machine_original_save_attempts_v1 inside machine.db. It does not create a checkpoint row. The digest binds the input and ID, not authenticated provenance. The original pair remains the caller's responsibility; M9 stores fingerprints, not a duplicate of the full capture payload.

An explicit dispatch_once requires the same original input and a PREPARED_HOLD reservation with neither checkpoint row present. It first commits DISPATCH_MARKED_UNKNOWN_HOLD. Only the same invocation may then attempt the pair transaction. That transaction rechecks the retained phase, digest and row absence, inserts V1 and V2 using the original shared insertion code and commits LOCAL_PAIR_COMMITTED and its saved timestamp in the same transaction. Any failure after the marker leaves an unresolved attempt; no automatic re-entry, reset, repair or replay. The ordinary save_pair signature, UUID allocation, SQL, return and stage hooks remain unchanged; the existing insertion statements are extracted into a private shared helper.

inspect uses one read transaction on machine.db and the original UUID. It checks the local association, both complete rows, canonical data, digests and summary metadata. Matching rows report LOCAL_ORIGINAL_PAIR_OBSERVED_UNTRUSTED, missing or contradictory rows report HOLD. No search by label, timestamp or nearest checkpoint. A lost prepare reply is recoverable only if the caller retains the original UUID. Absent or marked states never establish permission to repeat a Save.

M9 uses existing local storage owner and WAL/FULL writer behavior. The new path checks private parent/file permissions, existing sidecar files and its additive table schema; legacy user_version remains 1. Maximum 128 original-attempt rows, refusal at capacity, no automatic eviction. No protected history or tamper/rollback claim. Same-user mutation, hidden replacement and storage failures remain outside the trusted boundary.

## HOW TO USE

Developer-only API on an isolated disposable checkout. new_identity(), retain UUID, prepare(identity=..., v1_document=..., geometry_document=...), then explicit dispatch_once with the same pair. inspect(identity) is read-only observation. It does not invoke dispatch. No existing widget or CLI calls these functions; the UI and current Save path remain unchanged.

## VERIFY

Disposable real SQLite tests abruptly exit child processes after prepare, marker, first row insertion, second insertion, association update (before commit), and successful commit with discarded response. Verify all pre-commit failures leave zero checkpoint rows and a retained marked attempt; committed response loss resolves by original identity; duplicate and altered inputs refuse; competing existing row and removed/changed records HOLD; legacy Save and existing readers continue to work. This is process interruption, not hardware power-loss testing. Run M8/M7/M6 and existing storage/journal regressions. Independent exact-head Nurse 2 review before operator-controlled merge.

## WATCH OUT FOR

The original UUID and fingerprint are local bookkeeping. M9 does not supply actual native capture freshness, source enrollment, C5 consent, a signed receipt or native Restore. It binds the already captured ordinary pair, not an entire pre-capture request. Durable caller ownership of the UUID and original input, unresolved attempt retention policy, genuine fractional source correlation and explicit M9→M8 orchestration are still required before wiring Save. The M9 association is atomic with V1/V2 rows only, not across the separate fractional database or M8 journal.

## NEXT / DECISIONS

Keep existing UI sufficient for development. Coordinate genuine fractional observation with SwayPX and keep independently protected Connections/native Restore gates separate. No workstation changes, installation, merge or activation authorized by this milestone.
