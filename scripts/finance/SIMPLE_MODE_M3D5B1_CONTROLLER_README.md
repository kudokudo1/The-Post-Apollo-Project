# FinanceW Simple/Budget // M3d5b1 protected categorized Save controller

**PATIENT:** The-Post-Apollo-Project
**ROOM:** FinanceW Simple/Budget · assigned successor DOC (developer)
**PROVIDER:** OPEN AI // CHATGPT · Hospital-compatible external, not registered
**REVIEW BASELINE:** M3d5a #2611 independently SCOPED PASS, review #6052443457
**STATUS:** SOURCE-ONLY PRE-DISPATCH CONTROLLER. NOT AN INSTALLED SAVE BUTTON.
**PRODUCTION FINANCIAL WRITES:** HARD HOLD.

## IMPLEMENTATION

M3d5b1 is a non-activated, single-session state machine in scripts/finance/simple_m3d5b_protected_controller.mjs. It is separate from the Actual M3b writer, the FinanceW QML editor, and all other FinanceW worker lanes.

- **M3d2 read-only recheck:** Requires the selected category and parent group to be explicitly visible, non-income, with matched expense/account/month/date/budget/amount data. The preview remains read-only and cannot grant financial authority.
- **Explicit source identity:** Opens private actual-server-url and actual-sync-id through the descriptor-anchored M3b Linux filesystem helper, requires the pinned protected writer endpoint http://127.0.0.1:5006 and re-derives SHA-256(URL + NUL + Sync ID) to match the reader snapshot sourceKey. The read-side default 5007 is rejected instead of silently redirected. This establishes source-key consistency, not a fresh authenticated server preflight.
- **Read-only recovery observation:** Examines the existing private shared finance journal. Any write lock, uncommitted, malformed, symlinked or unrecognized entry refuses; no journal is created or cleared. M3b must still separately acquire its shared lock and verify all journals before any eventual write.
- **Two separate actions:** stage verifies the review/source/journal and returns a cryptographically random one-use confirmation challenge. confirm requires the exact phrase, re-evaluates the current snapshot (including nested in-place changes), and rechecks source and journal. Wrong phrase, stale data, lock, cancel and concurrent calls fail closed.
- **One-use operation identity:** On successful confirmation, crypto.randomBytes(16) creates a 32-hex requestId in memory and validates the full 13-field M3b command shape. The executable command/requestId is immediately discarded. Only a SHA-256 fingerprint and the state confirmed-but-dispatch-disabled are returned; both canSave and writeAllowed remain false.
- **No actuation:** dispatch always refuses. No writer, Process, Actual API, file mutation, permission creation, network call or UI connection exists. A valid staged review cannot save money.

## HOW TO USE

There is **no new operator action on the installed FinanceW desktop**. The existing read-only flow stays:

Finance → Budget → SIMPLE → TRANSACTIONS → NEW DRAFT → CATEGORY // PREVIEW ONLY → PREVIEW → CHECK CATEGORY SAVE READINESS.

M3d5b1 is tested against fictional isolated data and is not mounted.

## VERIFY

The dedicated CI checks: no-write source isolation, exact confirmed two-step flow and double/concurrent refusal, cancel races, reader 5007 vs writer 5006 refusal, source-key and symlink/permissions violations, cross-writer lock and attempted journal refusal, and in-place changes to visibility/identity/budget/amount/month. It reruns the earlier M3d2 and M3d5a read-only tests.

No real Actual server, live financial permit, personal budget, desktop, or operator machine is involved.

## WATCH OUT FOR

- This is **pre-dispatch only**. The cryptographic request identity is deliberately discarded and cannot be used to drive a real writer. One-use behavior across process restarts is NOT proven. That belongs to a future, separately reviewed protected writer bridge preserving M3b's durable journal.
- The default 5007 vs protected 5006 mismatch is deliberately refused. Aligning source endpoints would require explicit operator-approved setup, rather than a silent port swap.
- The current source-key inspection is not an authoritative fresh Actual read. M3b remains responsible for a locked, fresh preflight, source identity, duplicate protection, durability and uncertain-outcome recovery.
- M3b's SCOPED PASS does not certify this new controller; Nurse 2's independent M3d5b review remains mandatory.
- Categories, Banking and other worker-owned sources are unchanged. The existing Categories string-assertion failure remains separate integration debt.

## CHECKLIST // NEXT

1. Verify exact-head GitHub CI and raw logs.
2. Obtain independent Nurse 2 M3d5b1 source/security review.
3. Agree on canonical read/write source and port with Budget source owner before connecting a real service.
4. Separately implement and review protected writer transport, real confirmation UI, request identity custody, and uncertain-result display. Enforce M3b permissions, lock/journal and fresh Actual readback.
5. Verify disposable real Actual 26.10.0 end-to-end flow, native operator acceptance, and explicit final authorization before financial activation.

## DECISIONS // ROLLBACK

Narrow source-only pre-dispatch work is within the approved Simple/Budget assignment, not permission for production Save. Reverting this PR deletes its new source, tests, workflow and README without changing any installed widget, Actual source, existing finance journal, permission or account.
