# FinanceW Simple M3a // Proposed Category for a New Expense

## IMPLEMENTATION

This is the first bounded step toward completing Simple Mode's **record
categorized spending** workflow. It is an **isolated, dormant,
read-only prototype**. There is no new control in the running FinanceW
Budget screen yet.

Current `FinanceTransactionDraftPane.qml` creates a transaction
payload containing account, date, description and signed amount, but
**does not include a category ID**. The existing
`scripts/finance/transaction_guard.mjs` explicitly rejects
unexpected fields and calls Actual's `addTransactions` with no
category ID. Merely adding a selector to the live editor could
mislead users into believing their expense is categorized when it
would actually save uncategorized. **This PR deliberately avoids that.**

New components:

- `services/finance/FinanceExpenseCategoryPreview.js`:
  a pure read-only policy requiring an authenticated read-only Actual
  source, stable sourceKey/month, a **new negative expense**
  transaction candidate, a uniquely identified active account,
  a uniquely identified expense envelope and one associated group.
  Stale drafts, income, editing, invalid dates, missing/duplicate
  category IDs, and unsafe financial figures refuse.
- `widgets/FinanceExpenseCategoryPreviewPane.qml`:
  dormant QML view with category selection, proposed expense,
  estimated available-after balance and overspending warning.
  Changing category or source invalidates its preview. It offers
  **no Save, Confirm, request signal or writer activation**.
- Fictional Node and real offscreen Qt/QML tests, plus source-only
  no-writer/permission contract.

## MECHANISM

When the draft contains a **negative** $12.50 expense and Groceries has
$75 available, the preview estimates **$62.50 available afterward**.
It is a calculation against the current snapshot, **not** a saved
transaction or a guarantee of the eventual Actual result.

Only the selected expense category's available and spent estimates
are calculated. The result never invents a new TO BUDGET amount and
expressly states that Actual must recompute its authoritative values
after any future valid, reviewed transaction save.

The preview carries exact account/source/month/category IDs for
future independently reviewed writer planning. It does not create
an account, transfer money, change a budget amount, or modify any
bank/account transaction.

## VERIFY

Automated tests use fictional money/account/category data and run:

```bash
node --test tests/finance/test_finance_expense_category_preview_m3a.mjs
python3 -B tests/finance/test_finance_expense_category_m3a_contracts.py
python3 tests/finance/test_finance_expense_category_m3a_qt_runtime.py
```

Node policy and source authority checks are integrated with the
existing `financew-actual-probe.yml` GitHub workflow. Real component
offscreen Qt is exercised by the existing Budget Qt workflow. It
does not start a Quickshell session or connect to a real Actual
server or financial writer.

## WATCH OUT FOR

This is NOT a new categorization writer, not a local install, not an
Actual budget mutation and not authorization to enable transaction
writes. The M2b two-envelope paired writer remains independently
held pending Nurse 2 security review; that boundary is distinct
from M3 categorized transaction writing.

Before mounting this selector beside a live transaction
**CONFIRM SAVE** control, a separate M3b change must:

1. Decide whether the Actual API supports setting a category on
   new transactions using the installed pinned Actual API version.
2. Strictly bind the expense category ID to one actual expense
   group, authenticated source/month, account, and a fresh amount,
   not merely its human-readable category name.
3. Keep the existing duplicate-prevention, one-use request ID,
   private operator permission, shared journal/lock and
   no-retry/uncertain recovery behavior.
4. Persist a categorized expense in a **single protected
   transaction operation** and re-read the actual persisted
   category after sync; a successful API response alone is not
   enough.
5. Independently review the new write path and its real-Actual
   disposable fictional-budget tests.
6. Only afterward mount the category selection into the existing
   transaction editor, keeping drafts, updates, income and
   old uncategorized behavior coherent.

**Do not mount a fake category selector that appears to save.**

## OWNER / HANDOFF

Patient: `The-Post-Apollo-Project`. This source-only branch changes
only new independent preview policy/QML/test files and the two
existing FinanceW test workflows. It does not touch
`widgets/FinanceW.qml`, transaction draft/guard/writer, any local
permit, journal, credential, account or Actual data.

M2c [PR #2328](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2328)
is now merged, and the operator reported that the Move Money
preview works on their desktop. That is a scoped M2c visual PASS,
not a financial-write acceptance. M3a remains separate.
