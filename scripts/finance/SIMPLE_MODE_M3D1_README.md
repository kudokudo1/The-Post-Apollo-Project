# FinanceW Simple M3d1 // observed category visibility, read-only projection

**PATIENT:** The-Post-Apollo-Project
**ROOM:** FinanceW Simple/Budget (successor external Hospital-compatible DOC)
**STATUS:** Draft source-only compatibility improvement, not final operator acceptance
**PRODUCTION FINANCIAL WRITES:** HARD HOLD

## IMPLEMENTATION

The existing `scripts/finance/actual_readonly.mjs` normalization now carries three **read-only** fields from its existing `getBudgetMonth` result:

- `categoryGroups[].hidden`: `true`, `false`, or `null` if missing/malformed
- `categoryGroups[].isIncome`: `true`, `false`, or `null` if missing/malformed (income groups remain omitted from the expense list)
- `categories[].hidden`: `true`, `false`, or `null` if missing/malformed

Unknown is **never converted to visible**. The existing M3d0 handoff inspector requires concrete boolean evidence, rejects hidden categories/groups and income groups, and **always returns `canSave:false`** even on a valid read-only witness.

No additional API getter, server connection, financial permission, request ID, transaction writer, process, budget mutation, QML Save connection or user-host change is introduced.

## HOW TO USE

No new user control. Existing **Finance → Budget → SIMPLE → TRANSACTIONS → CATEGORY // PREVIEW ONLY** remains preview-only. Native visual PASS reported by operator for M3c on 2026-11-24. The source modification only preserves metadata for later authorized guard review.

## VERIFY

The dedicated CI runs the existing Actual read-only tests, new fictional real-projection → M3d0 compatibility tests, previous M3d0 guard tests, and Python writer-isolation contract. New tests verify visible/hidden/unknown/income states and that even a consistent witness has no Save authority. These are synthetic tests, **not disposable real Actual 26.10.0** proof or a live Quickshell test.

## WATCH OUT FOR

- This is a **shared read-only budget snapshot seam**. Independent Budget/source-owner and Nurse 2 review are requested before merge. Do not assume a merge grants shared ownership.
- The Actual 26.10.0 runtime might omit `hidden` flags on certain objects. When absent, this implementation exposes `null`, preserves budgeting preview display and **blocks M3d0 eligibility** rather than inventing a false value. Real disposable Actual shape verification is still needed.
- M3b dormant writer has **no independent Nurse 2 financial-write security review** and has not passed isolated real Actual 26.10.0 writer integration.
- Existing readonly source selector default port 5007 and writer 5006 requirement are unchanged. The current host's actual configuration is unverified.
- Category group writer owned by the separate Categories worker is untouched. M2b Move Money remains a separate HOLD.

## CHECKLIST / NEXT

1. Exact-head CI and source review.
2. Budget/source-owner collision and independent Nurse 2 review on this shared read-only schema change.
3. Disposable real Actual version 26.10.0 sample proves booleans (or unknown) on an isolated test budget.
4. After distinct M3b write-security review, consider separately authorized M3d2 guarded bridge. No automatic retry or financial activation.

## DECISIONS

Keep current UI, permits, journal/lock and writers untouched. Revert this narrow PR to roll back the additive snapshot metadata; no live budget state to recover.
