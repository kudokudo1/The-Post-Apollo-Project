# FinanceW Simple M3d0 // read-only categorized expense handoff inspection

**State:** implementation preparation only; no permitted categorized Save, no operator acceptance.

## IMPLEMENTATION
A pure, unused compatibility inspector compares the currently selected new expense and its M3c read-only estimate against one authenticated budget snapshot. It refuses mismatched source/month, invalid dates/amounts, ambiguous account/category/group identities, stale category balances, changed estimates, hidden categories, and income groups. It emits a *partial witness*, not a writer command: it deliberately lacks action and requestId. It has no Process, Actual API, filesystem, credentials, permission file or UI integration.

## VERIFIED BLOCKER
The current `normalizeSnapshot` in `scripts/finance/actual_readonly.mjs` excludes income groups but does not expose the Actual `hidden` flag for categories/groups or the group `is_income` status in its compact projection. M3b's independent preflight requires those checks. Therefore the existing M3c GUI snapshot cannot by itself prove writer eligibility. Missing visibility metadata is an explicit `category-visibility-unverified` refusal, **not** implicit permission.

Also, writers restrict the local Actual endpoint to `http://127.0.0.1:5006`, while read-only source selection defaults to `http://127.0.0.1:5007`. This is a deliberate safety distinction until verified with the operator's actual configured source; never silently change production endpoint policy to make a test pass.

## VERIFY
`node --test tests/finance/test_finance_simple_m3d0_handoff.mjs`
`python3 -B tests/finance/test_finance_simple_m3d0_hold_contracts.py`
CI runs both on this isolated change. All fixtures are fictional, and success cannot establish a real Actual server integration, permission, independent review or native Quickshell acceptance.

## WATCH OUT FOR
No code in FinanceW, the real transaction editor, M3c preview, existing D9 transaction writer, M3b protected writer or shared read service is changed. The inspector is not imported by a UI. Existing category preview still blocks ordinary Save until explicit DISCARD CATEGORY PLAN. M2b Move Money remains separately held.

## NEXT
1. Operator-native M3c click/visual acceptance.
2. Independent Nurse 2 M3b write-security and recovery review, and disposable real Actual 26.10.0 test on an isolated budget.
3. Coordinate schema/visibility evidence with the read-only Budget source owner before changing the shared projection.
4. Only then propose an M3d live bridge under separate authorization. Retain write HOLD and no automatic retry.

Recovery: delete/revert this isolated source-only branch/PR; no live account or desktop state was changed.
