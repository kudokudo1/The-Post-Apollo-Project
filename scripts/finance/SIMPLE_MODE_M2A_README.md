# FinanceW Simple // M2a Envelope Move Preview

## What this is

The first source-only piece of Simple Mode's **Move Money** workflow.
It stages a read-only, two-envelope proposal before any finance writer is
designed or activated. It intentionally does not appear in the running
Budget menu until the shared-root M1 integration is accepted.

**Not a bank transfer:** It would adjust two category allocations within
the same month of the same Actual budget. Account balances, bank account
ownership, spending transactions, and total **TO BUDGET** should be unchanged.

The new `FinanceEnvelopeMovePlan.js` checks a schema-v1 authenticated,
read-only Actual snapshot, stable sourceKey/month, two **distinct uniquely
identified expense categories**, positive USD cents and safe numeric
ranges. It computes:

| Field | From envelope | To envelope |
| --- | --- | --- |
| Monthly assigned | decreases by move amount | increases by same amount |
| Available balance | decreases by move amount | increases by same amount |
| Total unassigned | unchanged | unchanged |

The first-stage policy refuses moving more than the source envelope's
available balance **or this month's assigned amount**. This is a
deliberately conservative initial limitation because the current
single-category writer disallows a negative monthly target allocation.
It may be revisited for full Actual rollover parity only after the
two-category writer is independently reviewed.

The destination may remain overspent after a smaller partial move. The
preview labels this explicitly. The source may **not** become negative.

## GUI state

`FinanceEnvelopeMovePreviewPane.qml` is an **unmounted, dormant** form.
It can cycle through source and destination envelopes, edit a move
amount, and preview the amount and before/after available balances.
**PREVIEW MOVE** never saves, confirms, retries, executes, or emits an
action to a writer. Input or snapshot changes invalidate the old
preview. No Actual credentials or bank connections are accessed.

The component deliberately displays:

- `BUDGET ALLOCATIONS ONLY // NOT A BANK TRANSFER`
- `NOT SAVED // ATOMIC FINANCIAL WRITER NOT IMPLEMENTED`

It is validated in a disposable offscreen Qt fixture with fictional
numbers, not with the user's own budget.

## Financial-write security blocker

`write_allocation.mjs` and `allocation_guard.mjs` implement one
category's `setBudgetAmount` mutation under their own permit/lock/journal.
**Do not call that writer twice to simulate an atomic envelope move.**

A correct M2b writer needs a single operator-authorized command binding
sourceKey, month, both category IDs, old budgeted/available amounts,
expected TO BUDGET, and a unique request ID. It must reread Actual
under the shared global finance lock, persist an ATTEMPTED journal
before the first mutation, refuse automatic retries, perform two
assignments and sync, and verify both post-commit category amounts and
unchanged unallocated funds from a fresh read. Any crash/failure after
attempted mutation must stay **UNKNOWN/UNCERTAIN**, with explicit
operator reconciliation, never an automatic second attempt. A
two-category API database transaction would be preferable if Actual
supports one; do not assert atomicity of two API calls.

The writer API/security design, independent Nurse 2 review, integration
into `FinanceW.qml`, final operator acceptance, and live desktop
verification are future authorized steps. **No permit is provisioned**.

## Tests

- `node --test tests/finance/test_finance_envelope_move_plan_m2a.mjs`
- `python3 -B tests/finance/test_finance_envelope_move_m2a_contracts.py`
- `python tests/finance/test_finance_envelope_move_m2a_qt_runtime.py`
  with PySide6 and QT_QPA_PLATFORM=offscreen

All tests are fictional-data/no-writer tests. Their CI results should
be recorded at the exact source head.

## Scope and continuity

M1 [PR #2305](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2305)
remains operator-owned for merge and native visual acceptance. M2a changes
only new service policy, new isolated pane, fictional test files,
dedicated workflow, and this README. It does **not** modify the shared
FinanceW root, existing allocation writer, Banking, Research, Market,
Household, host, or actual budget.
