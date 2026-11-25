# FinanceW Simple M3d5a // guarded categorized Save UI readiness (HOLD)

**PATIENT:** The-Post-Apollo-Project
**ROOM:** FinanceW Simple/Budget · successor DOC
**REVIEW BASELINE:** M3b security corrective PR #2555, independent review #6051716149 SCOPED PASS
**STATUS:** UI review staging, not a protected writer connection
**PRODUCTION FINANCIAL WRITES:** HARD HOLD

## IMPLEMENTATION

The new FinanceCategorizedSaveReview.js is a pure Qt JavaScript mirror of the merged M3d0 and M3d2 read-only handoff validators. It checks account and category identities, hidden/income eligibility, source/month/date/amount, group, available/budgeted/spent cents, current budget and the selection's consistency with the prior preview.

FinanceExpenseCategoryPreviewPane.qml gains a working **CHECK CATEGORY SAVE READINESS** control after a valid category estimate. It recomputes the 11 preview-only financial fields from the current snapshot, checks the result against the same current inputs, and shows a clearly labeled **REVIEW MATCHED // CATEGORY SAVE DISABLED** state only when valid. A selection/source/field change invalidates the review. Refusal displays an error; no financial mutation occurs.

The reviewed result deliberately has NO action, NO request ID, NO authorization, NO Process, NO executable command, NO network access and NO writer call. The prior transaction editor and FinanceW root are unchanged. Old uncategorized CONFIRM SAVE remains blocked whenever the category plan is armed and the user must explicitly discard the plan to return to uncategorized flow.

## HOW TO USE

In compatible staged FinanceW: Budget > SIMPLE > TRANSACTIONS > NEW DRAFT > fill valid expense > CATEGORY // PREVIEW ONLY > pick envelope > PREVIEW > CHECK CATEGORY SAVE READINESS. The display will either refuse stale/hidden/unknown conditions or report a review match. **Neither outcome saves a transaction.**

## VERIFY

Dedicated CI asserts an unaltered M3c/D9 Save hold, no writer integration, and QML-vs-M3d2 exact return-object parity across valid, stale and malformed fictional snapshots. Offscreen Qt loads the real transaction editor/category pane and checks the new review against a fictional budget, including the old Save block. No live Actual credentials, server or host files are touched.

## WATCH OUT FOR

- This is the **first guarded UI integration seam**, not the final activated Save. A separately reviewed writer service/controller, input-specific request-ID authority, explicit UI confirmation, native protected disposable end-to-end tests and operator production authorization remain outstanding.
- The desktop's read-only budget source can default to port 5007 while protected M3b writer permits 5006 only. Do not bypass source identity, convert port silently or create a second source selection.
- Qt JavaScript duplicates the Node-only pure validators because Qt cannot import Node ES modules directly. Parity tests are required if the canonical Node validators change.
- M3b scoped security approval does not certify this new UI nor activate financial writes.
- Category preview may remain unreviewable if Actual supplies unknown visibility; that is a safe refusal.

## CHECKLIST / NEXT

1. Require exact-head CI PASS and native Qt fixture PASS.
2. Independent UI/security review of the new M3d5a seam.
3. Coordinate read-only source/writer endpoint and shared root ownership before implementing the next protected controller.
4. Separately stage guarded service/command confirmation and disposable Actual testing; never bypass original category hold until explicitly authorized.
5. Obtain operator acceptance before any live write permit creation or activation.

## DECISIONS

This draft introduces no production capability, no host mutation, no merge or deployment authorization. Rollback reverts eight scoped read-only widget, test, workflow and documentation changes.
