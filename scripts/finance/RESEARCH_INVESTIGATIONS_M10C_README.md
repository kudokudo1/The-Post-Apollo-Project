# FinanceW Research M10c // Durable operation-intent evidence in existing writer lock

**PATIENT:** The-Post-Apollo-Project  
**ROLE:** external Hospital-compatible Research DOC, not independent reviewer  
**SCOPE:** existing Research M2 store lock, pure intent contract and M10b read-only inspector  
**PRODUCTION RESEARCH SAVE:** HOLD · **FinanceW UI writer:** disconnected

## IMPLEMENTATION

Prior milestones:
- M10a #2646: the store keeps an exclusive file lock after an uncertain commit, instead of silently removing it and enabling another write.
- M10b #2657: the read-only inspector observes saved document, empty lock and abandoned files; independent scoped PASS applies only to that diagnostic.

M10c adds an operation-specific record to M2's **existing durable lock file**, without creating a new sidecar ledger or exposing a new operator control:

1. The writer creates the exclusive owner-private lock and fsyncs both the lock inode and containing directory, as in M10a.
2. After checking revision and preparing the complete proposed case document **in memory**, it generates a fresh random UUID and records only: schema version, random operation UUID, action (create, attach, remove), prior/proposed revision, and SHA-256 of canonical JSON for the prior and proposed documents.
3. The writer emits that small exact-field record as one newline-terminated JSON frame into its existing lock **and fsyncs the lock** before invoking the replacement rename.
4. On a known-good directory fsync, M10a's owner-lock release remains unchanged. On unknown rename/directory fsync/SIGKILL, M10a preserves the lock and its intent evidence.
5. M10b's **read-only** inspector now reads a bounded, O_NOFOLLOW and inode-matched lock record, with strict JSON framing. Empty legacy locks remain PRESENT but have intent state NONE. Malformed intent remains preserved and returns UNAVAILABLE / INVALID_INTENT.
6. If a valid lock record exists, the read-only inspector reports the current saved document as PRIOR_MATCH_OBSERVED, PROPOSED_MATCH_OBSERVED, DIFFERENT_DOCUMENT or UNAVAILABLE. **All these outcomes still leave canUnlock:false, canRetry:false, changesMade:false. A match is NOT a signed receipt or proof of durable completion.**

No confidential case text, SEC URLs or financial account details are written to the lock or printed by the inspector. The existing JSON investigation file still contains the Research notes, as it did before. This is not encrypted storage.

## HOW TO USE

No new desktop action. The live Research experience still has no connected permanent Save button. Do not restart Quickshell or reproduce scratch scenarios for this milestone.

An independent reviewer can use the **read-only** recovery inspector to observe metadata-only evidence on a disposable store. It does **not** support unlock, automatic retry, data restoration, or destructive cleanup.

## VERIFY

- tests/finance/test_research_m10c_write_intent.mjs uses only a fresh, private disposable store.
- Pure tests verify exact fields, UUID, canonical fingerprints, old/proposed classification, malformed/extra framing and no note-text leak.
- Writer tests inject rename and post-rename directory-fsync failures, ensuring the lock contains an intent whose observed prior/proposed digest matches without enabling retries.
- Real native child-process SIGKILL before and after rename verifies operation intent survives process termination, the lock still blocks writes, and the inspector never grants recovery authority.
- Malformed lock and a different observed document remain refusal/review states; normal durable save removes the lock without manufacturing a success receipt.
- Standard Research contracts and a Fedora 44 native workflow rerun the prior M2, M10a, and M10b regression matrix at exact PR head.
- Inspect exact-head workflow results and raw native logs before declaring implementation verified.

## WATCH OUT FOR / SECURITY REVIEW GATES

- The UUID and SHA-256 hashes are **diagnostic evidence, not cryptographic authentication, authorization, a completion receipt or operator permission**. A process with same-user filesystem write rights can forge metadata. The inspector must never use a digest match to clear a lock.
- The existing M2/M10a same-UID path replacement races remain; path-based ancestor checks do not supply a trusted Linux directory-fd walk. Independent reviewer must evaluate the threat model and OS-native hardening before production.
- An OS power failure, write reorder or filesystem-specific durability failure is not fully equivalent to SIGKILL. The native tests prove the stated process-level crash cases only.
- A crash after lock creation but before intent fsync can leave an **empty or malformed lock**, and therefore intentionally does not adjudicate the write. The recovery inspector recognizes these states and preserves the lock.
- A successful save deliberately removes the lock; M10c does **not** create a persistent log of all successful Research saves. If that is required, design a separately reviewed receipt ledger with explicit retention, privacy and crash semantics.
- Independent Nurse 2 security review, completion of recovery adjudication, protected writer permission integration, and express operator approval remain mandatory before enabling persistent FinanceW UI saves. The existing local store is **unencrypted**.

## CHECKLIST / DECISIONS

- [x] Durable metadata-only UUID and pre/post fingerprint inside the writer's existing lock.
- [x] Bounded inspector reports of operation identity and observed snapshot classification.
- [x] All matches remain no-unlock/no-retry; malformed and legacy locks handled conservatively.
- [x] Disposable M2/M10a/M10b/M10c regression and Fedora workflow added.
- [ ] Exact-head workflow verification, independent review, remaining race/power-loss safety.
- [ ] Separate operator authorization for merge, host changes and live persistent Save.

The scope is deliberately limited to Research-owned storage. It does not change other FinanceW owners' source files or shared widget layout.
