# FinanceW Simple/Budget // M3d5b4 disposable confirmed identity custody

**PATIENT:** The-Post-Apollo-Project
**ROLE / ROOM:** Simple/Budget DOC, not independent Nurse 2 · FinanceW Simple/Budget
**BASELINE:** M3d5b3 PR #2669 merged, independently reviewed SCOPED PASS #6057546250
**HOSPITAL CONNECTION:** external and compatible, no live registration verified
**PRODUCTION FINANCIAL WRITES:** HARD HOLD

## IMPLEMENTATION

A separate disposable custody fixture shows how a confirmed private transaction ID can survive restarts without releasing an executable transaction to the UI. Existing M3d5b1, M3d5b3, M3b and FinanceW GUI remain unchanged.

- **Stage:** After a valid current M3d2 review and matching, caller-supplied source witnesses, generate an independent 128-bit public receipt handle, a private 128-bit M3b request ID and a one-time confirmation phrase. Staging makes no filesystem change.
- **Confirm:** Consume the one-time phrase, recompute the financial review and source witness, validate the complete M3b command *in memory*, then store only version, confirmed-held state, receipt handle, private request ID and command digest. Use descriptor-anchored private directory access, exclusive record creation, exclusive lock and file/directory fsync before acknowledging. There is no executable command persisted or returned. Failed/unknown operations keep the recovery stop.
- **Inspect:** In a new Node process, an unprivileged UI-like caller supplies only the public receipt handle and a freshly reviewed view. The private record is reopened safely and internally verified against the same sealed request ID and current financial fields, but the ID never leaves the fixture. Inspection never authorizes dispatch or retry.
- **Repeated purchases:** Separate genuinely confirmed intents with the same date, amount and details are allowed. A receipt handle identifies one particular operation; the earlier disposable global body-fingerprint ban is NOT production policy.
- **Hard no-write:** Requires FINANCEW_DISPOSABLE_TEST=yes, an exact private test HOME and a specially named top-level temporary directory. It never opens production FinanceW journals, invokes M3b, uses Actual, reads credentials or generates permits. The dispatch method unconditionally refuses.

## HOW TO USE

There is no new installed desktop action. Finance -> Budget -> SIMPLE -> TRANSACTIONS -> CATEGORY // PREVIEW ONLY -> CHECK CATEGORY SAVE READINESS still cannot save an expense. Only isolated CI may run this fixture.

## VERIFY

Dedicated GitHub CI uses fictional accounts and real separate Node child processes to check normal restart, simulated post-fsync/pre-ack death, concurrent confirmation, canceled or incorrect phrases, changed category/amount/budget/source, 5007 versus protected 5006 endpoint mismatch, symlink/writable custody paths, hostile or malformed receipts and stale locks. It reruns the independently reviewed M3d5b1, M3d5b2b and M3d5b3 tests, plus a source-level no-production-activation check.

## WATCH OUT FOR

- The private request ID is still NOT connected to the real M3b writer. This fixture does not prove a live end-to-end handoff and does not change M3d5b1's reviewed discard behavior. A later, separately reviewed protected adapter must preserve the same ID under M3b's permit, shared exclusive lock, ATTEMPTED journal, fresh Actual preflight and non-retryable uncertainty.
- Reader default port 5007 versus protected writer 5006 remains an explicit Budget/source owner integration decision. Caller-supplied endpoint witnesses are not authenticated evidence.
- A sealed fixture receipt is NOT proof of a real Actual commit. The simulated crash is not power-loss or native desktop acceptance, and private same-UID process compromise is outside this test threat model.
- No merge authorization, local machine changes or production permit creation is implied.

## CHECKLIST / NEXT

1. Verify exact-head CI and raw logs.
2. Obtain independent Nurse 2 M3d5b4 custody and security review.
3. Coordinate trusted reader/writer source attestation without automatic port substitution.
4. Separately implement and review a non-activated transport retaining the same durable ID, not a new one; then test disposable Actual interrupted operations and native desktop flow.
5. Obtain explicit operator approval before any real financial write or deployment.

## DECISIONS / ROLLBACK

This patch is isolated to new fixture source/tests/workflow/documentation. Reverting it cannot change the existing installed FinanceW widget, M3b writer, real journal, permit or financial data.
