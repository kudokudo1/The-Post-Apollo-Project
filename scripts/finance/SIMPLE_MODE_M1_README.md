# FinanceW // Simple Mode M1 · Budget Experience Switch

## Scope

This is **stage 1 of Simple Mode**, not the final envelope app. It changes
FinanceW's Budget **presentation**, not budget calculations or the financial
writer trust model.

**Finance → Budget → Budget** defaults to **SIMPLE**. The upper Budget
controls provide **SIMPLE** and **ADVANCED** buttons.

- SIMPLE keeps the existing envelope grid, month navigation, account and
  category views, Add Money and transaction drafts. It hides the optional
  expanded funding-review/funding-setup details.
- ADVANCED shows the **same** underlying budget, the **same** categories
  and the **same** guarded transaction/allocation/funding writers, plus
  the additional funding-review tools previously opened via the
  single "ADVANCED" disclosure button.
- The two buttons use the shared Post-Apollo ActionButton selected
  style and keyboard activation. Both choices operate inside the
  existing one-panel FinanceW interface.
- The selection starts in SIMPLE when the Quickshell process creates
  FinanceW and is retained in process memory during that session.
  It is **not stored durably across shell restarts**.

The switch is disabled while any transaction, quick-add, guided-funding,
allocation, category or group editor is open, while local drafts are
being written, or while any corresponding financial writer is PENDING
or UNCERTAIN. Close or finish active editors first. Switching resets
the read-only funding-review expansion only; no financial data is touched.

## Not yet in this milestone

- No direct money movement between envelope categories.
- No expense category selector in transaction creation.
- No new budgeting method, future-income tracking mode, or separate database.
- No changes to Actual API, bank accounts, permits, writer journals,
  production activation, or local machine configuration.
- No claim that every current tab has been stripped down to its eventual
  Simple daily-driver form. They remain accessible to prevent capability
  regressions during staged delivery.

## Verification and acceptance

The dedicated source contract verifies mutually selected controls,
default mode, non-mutating mode changes, active-editor and pending/uncertain
writer guards, and reuse of the existing Budget service/editor instances.
It also reruns existing Budget section and read-only feed contracts.
GitHub CI proves source contracts, not actual Silverblue desktop rendering
or permission for real financial writes.

**Ownership boundary:** this stage necessarily modifies the shared
`widgets/FinanceW.qml` navigation seam. Keep the PR in DRAFT for the
FinanceW integration owner and operator to review. It does not alter
Categories M6's money-writing security boundary or bypass that separate
independent review.

## Next stages

Complete the Simple-dayflow actions in order:
(1) envelope-to-envelope allocation transfer; (2) categorized expense
entry; (3) month rollover and reuse; (4) safe envelope organization;
(5) comprehensive real-data acceptance and recovery review.
