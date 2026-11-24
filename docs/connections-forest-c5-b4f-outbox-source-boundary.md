# 🏥💜 DOC 3 // Forest B4f local outbox ↔ C5 V1 source boundary

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Forest C5  
**STAFF ROLE:** DOC 3 · external Hospital-compatible; no live Hospital registration established  
**STATE:** CI-only Connections comparison; source of actual event is still the Forest-owned untrusted SQLite writer  
**PRODUCTION:** Forest, Sign-In, TimeW HOLD

## IMPLEMENTATION // Actual data mechanism

Forest B4f [#2277](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2277), reviewed and merged, added an opt-in **local** outbox event inserted in the same SQLite transaction as the B3 attempt status and assistant reply. The real B4f source generates a unique event ID and saves original attempt/owner/Tree/session/user-turn/model/revision/terminal state in local SQLite. A B4f read-only inspector returns the original attempt/session, local state, local event ID/status and permanently false C5 authority claims. It does NOT return the whole original scope, a protected grant, a human consent proof, an enrolled key, an independent current head, or a native signed terminal receipt.

DOC 3 V1 [#2239](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2239) can validate the complete intent/session/attempt against three test signatures; all keys and journal claims are caller-controlled. DOC 3 #2267 compares an actual disposable B4e SQLite attempt observation with those V1 claims. Its result always denies C5 settlement.

This PR adds a **B4f-specific** input adapter. It:
- Requires exact B4f inspector fields (no private body, injected grant, extra field or optimistic authority bit).
- Requires a locally recorded event ID to be an e_-prefixed 32-lowercase-hex UUID shape. This checks only formatting, not writer origin or signing.
- Requires a reported LOCAL_COMMITTED or LOCAL_ABORTED event to match the local FOREST_COMMITTED or FOREST_ABORTED state. Rejects a claimed terminal event against RESERVED.
- Requires LOCAL_EVENT_NOT_OBSERVED to have no event ID, then classifies it as **ambiguous**, not confirmed legacy status, corruption or rollback.
- Reuses the existing DOC 3 #2267 strict V1 original session/attempt comparison rather than inventing a second weaker signature path.
- Returns only diagnostic reason and coarse local state/claim with safeActions=[], no original attempt/session/user/Tree, no private text, no retry/revocation release and every protected flag permanently false.

**No new authority.** This is deliberately not a C5 issuer, native writer receipt, original peer credential proof, protected journal reader or production reconciliation endpoint. Even a matching locally generated event and an exact V1 signed fixture can be forged or rolled back together.

## HOW TO USE // Disposable tests only

    python3 -B -I -m unittest discover -s tests/connections -p 'test_connections_forest_c5_b4f_outbox_comparison.py' -v

The test builds a genuine disposable B1/B3/B4f SQLite database, opts in to the Forest-owned B4f outbox, reserves an attempt, commits or aborts it in actual test SQLite, and uses the real Forest outbox inspector. Separate V1 fixture signer keys are generated in-process only. No installed Forest database or model is touched.

The negative cases explicitly demonstrate:
- A local event and signed fixture both claiming COMMIT still do not settle C5.
- ABORTED plus a signed ROLLBACK remains UNKNOWN_HOLD.
- Contradictory ABORTED/COMMIT or COMMITTED/ROLLBACK is refused, not trusted.
- A corrupted/missing outbox event on a locally committed attempt returns LOCAL_EVENT_NOT_OBSERVED; **B4f cannot tell whether the attempt predates instrumentation or lost an expected event**. A separate durable marker, protected provenance and original writer identity would be required.
- An uninstrumented legacy commit can produce the *same* missing-event observation. That ambiguity must never become a permission to regenerate or release revocation.
- Restoring the original local database snapshot can roll back both reply and event atomically while an independently fabricated V1 signed claim still says COMMIT. The outbox is NOT antirollback custody.

## VERIFY // Review target

- 20 new adversarial B4f/C5 cases, with actual local SQLite writes only in disposable tests.
- Inherited 24 Forest B4f tests, 21 B4e, 18 B4d, 20 DOC 3 V1, 20 DOC 3 B4e/V1 and 15 B4c = **138 expected focused tests**.
- Dedicated CI and static absence-of-actuation gate.
- Independent Nurse 2 exact-head review **before merge** required, even if all workflows green.

## WATCH OUT FOR // Remaining production blockers

- Forest local outbox still cannot attest to a **current** independently enrolled signer, original native process/seat/release, genuine on-disk transaction history protected against whole-file restore or current C5 grant/revocation.
- No real protected terminal delivery/ACK idempotence channel, no live host control, and no stable installed root. A caller-selected permit ID must not be inserted into original writer evidence.
- Forest owns B3/B4f original writer and any future per-attempt instrumentation marker or protected outbox export. DOC 1/DOC 2 own genuine native identity and independent custodian history. DOC 3 owns C5 one-use grant, revoke and terminal verification. The ForestW UI is separately owned.
- A local COMMITTED event alone cannot settle an absent/conflicting protected receipt. A local ABORTED event is **not** independent ROLLBACK_CONFIRMED.
- Provisional model DELTA streaming may disclose content before final commit. That requires a separate Forest-owner + operator policy and consent boundary.

## CHECKLIST / NEXT

- [x] B4f source and Nurse 2 review inspected; Syntagma AGENTS / Hospital protocols previously read.
- [x] Source-only Connections adapter reuses DOC 3's existing C5 V1 comparison.
- [x] Real disposable B4f outbox + V1 signatures adversarial tests written.
- [ ] Exact-head dedicated CI and raw logs verified.
- [ ] Nurse 2 independent pre-merge review.
- [ ] Cross-owner native protected writer event interface, independent enrollment and issuer grant/settlement.
- [ ] Native crash/revoke/streaming validation; operator production acceptance.

## DECISIONS

**Development only.** V1 wire, Forest B4f DB/schema/code, original C3e/C4b trust, Hospital, TimeW and live desktop untouched. All C5 protected operations remain HOLD. This work is evidence of unresolved native custody, not a substitute for it.

## B4e/B4f recovery-input hardening follow-up

After DOC 3 #2431 and #2440, the existing B4e and B4f recovery comparison entrypoints now require exact plain dictionary keys and field cardinality before set equality, and exact scalar types before comparing schema, status, settlement or terminal claims. A nonempty safeActions list is refused without inspecting its elements. Fixed public recovery refusals are raised after leaving nested V1/B4e exception handlers. Six new test methods (three per comparator) exercise hostile Python keys/values, excess fields and malformed original intent refusal chains, using the existing disposable SQLite test harnesses. This is a narrow source-level input-safety correction, not a production incident or erasure of traceback locals. Existing valid diagnostic shape, original-attempt correlation, conflict classification and UNKNOWN_HOLD remain unchanged. No receipt settlement, retry, new signer, source enrollment or protected recovery authority. DOC 1 F1–F6 and the Core-owned protected original effect interface remain pending. #2431 and #2440 are independent PRs and must not be modified by this work.
