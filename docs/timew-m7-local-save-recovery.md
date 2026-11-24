# TimeW M7 // Read-only local two-database Save recovery reference

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE · Scope A  
**ROLE //** TimeW owner DOC, external Hospital-compatible; no verified live registration  
**STATE //** Source/CI-only, not wired to Save or Restore  
**PRODUCTION RESTORE // HOLD**

## Mechanism

The existing Save writes integer-only V1/V2 checkpoint data. M6 separately admits a complete caller-supplied exact CURRENT window set to the local v3 database. These files do not share a transaction.

M7 adds a read-only reference API to observe the outcome without attempting another Save. Before an explicit M6 call, the caller can prepare an immutable LocalSaveBinding from the already persisted V1/V2 pair and an explicit full exact CURRENT candidate set. The binding contains checkpoint UUID, SHA256 of canonical summary/legacy/geometry, and SHA256 of sorted window metadata and exact binary64 words. The full candidate set must match the saved window key/app/output/workspace set. Read the pair twice to detect observed changes. There is no durable attempt journal; a future integration must preserve the original binding and candidate set before dispatch and must not recreate them from later data.

Inspect the original binding with the original candidate set. The observer checks the legacy pair before and after reading the scoped v3 rows. Outcomes:

| Status | Meaning |
| --- | --- |
| BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED | Matching ordinary local records observed, not a successful-attempt receipt |
| LEGACY_MATCH_LOCAL_EXACT_ABSENT | No v3 rows seen at read, not proof of failed attempt |
| CANDIDATE_CONFLICT_HOLD | Candidate fingerprint changed |
| CHECKPOINT_CHANGED_HOLD | Observed checkpoint differs from original binding |
| LOCAL_EXACT_CONFLICT_HOLD | Partial or different v3 set |
| LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD | Unavailable, invalid or disappearing checkpoint/read |

No writer, automatic retry, repair, migration, deletion, native action or protected receipt. No source authentication or native capture freshness. No cross-database atomicity. Same-user edits, hidden ABA, concurrent writes and rollback can escape sequential observations. Matching rows do not prove when, how, or by whom the values were captured. Absent rows do not authorize another write.

## VERIFY

Disposable tests use actual V1/V2 and v3 SQLite owners. Exercise absent v3 without file creation; lost M6 reply after actual commit; one-ULP and order-independent readback; failed second insert with original checkpoint preserved; partial/conflicting rows; changed checkpoint; deletion between reads; unavailable DB; malformed and changed candidates; generic errors and no actions. Old Save/QML remain unchanged. Require independent exact-head review.

## NEXT

Define a separately reviewed actual fractional observer input contract with SwayPX owner. An eventual explicit Save orchestration must retain original identity and binding durably, report partial/uncertain outcomes honestly and never blindly replay. The M7 reference does not implement durable attempt custody or any producer. Existing UI is sufficient; polish deferred. Protected SwayPX settlement and Connections custody remain separate.

**DECISIONS //** Local ordinary data now, independently protected hardware/NAS later. Production Restore HOLD.
