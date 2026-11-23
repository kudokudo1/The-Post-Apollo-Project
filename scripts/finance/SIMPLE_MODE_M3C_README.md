# FinanceW Simple M3c // Read-only category preview in transaction editor

## IMPLEMENTATION

**M3c UI only. This milestone DOES NOT ENABLE CATEGORY SAVES.**

M3b [PR #2356](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2356)
is merged at source level. It has not received independent Nurse 2 security
review and has not been tested against a disposable real Actual 26.10.0
server. **Production financial-write activation remains HARD HOLD.**

M3c mounts the existing M3a `FinanceExpenseCategoryPreviewPane.qml`
**once**, directly below the existing transaction draft editor in the
`Finance → Budget → SIMPLE → TRANSACTIONS` section. It uses the same
read-only `financeBudget.snapshot`, account and month that the
existing editor reads. No new financial accounts or services are created.

The new category action appears only for a valid **new expense**, never
for income or editing a saved transaction. It offers a category selector
and **estimated envelope available after spending**, including a clear
overspending warning, plus CANCEL.

## HOW TO USE (after merge and reload)

1. Open **Finance → Budget → SIMPLE → TRANSACTIONS → NEW DRAFT**.
2. Enter a valid date, description and expense amount.
3. Select **CATEGORY // PREVIEW ONLY**.
4. Pick an envelope, then choose **PREVIEW** to review the estimated
   remaining funds. This is **not saved** and has no effect on the
   actual account or budget.
5. To leave the categorized plan and return to the old transaction
   workflow, choose **DISCARD CATEGORY PLAN // UNCATEGORIZED**.
   Only then is the original category-free **PREVIEW → CONFIRM SAVE**
   control available again.

**Important:** the original transaction Save path remains intentionally
**uncategorized**. It does not read the chosen category ID. It must never
appear to save one.

## SAFETY MECHANISM

The existing draft now has a separate `categoryPreviewRequested`
signal and a `categoryPreviewArmed` flag. The parent launches only
when FinanceW is in Simple/Transactions with a ready authenticated
Actual snapshot and a matching sourceKey/month.

When preview launches, `categoryPreviewArmed` becomes true and the
existing financial **CONFIRM SAVE** and local draft Save are both
disabled. Even directly invoking the draft's `requestCommit()` or
its old `onSaveRequested` handler cannot silently save an
uncategorized transaction while a category plan is active.

CANCEL in the category preview closes the preview, **but intentionally
does not** clear the Save block. Only an explicit
`DISCARD CATEGORY PLAN` action can clear the flag. This prevents
an accidental ordinary Save that the user believes included a category.
The flag is also reset when the draft is discarded/cleared.

Changing date, payee, amount, account, direction or editing state
closes an open preview. Changing source snapshot/selected month
invalidates the preview. Closing FinanceW or navigating away clears
the preview. If an old draft remains open after navigation, its
category Save block remains fail-closed until explicitly discarded.

There is **no invocation of write_categorized_expense.mjs**, no
new permit, no extra financial journal, and no changed API command.

## VERIFY

- Source contract `tests/finance/test_finance_simple_m3c_view_contracts.py`
  validates one root mounting, same sourceKey/month, preview-only
  candidate, no writer bridge, explicit Save guards and invalidation.
- Existing draft action-count and M3a source contracts updated
  (five original buttons, plus two new preview/discard actions).
- Real offscreen Qt component integration
  `tests/finance/test_finance_simple_m3c_qt_runtime.py` loads the
  actual transaction editor and category preview against a fictional
  budget. It checks incomplete-draft refusal, candidate selection,
  non-persistence, direct Save refusal during a preview, CANCEL not
  weakening the block, input-change invalidation, explicit discard,
  resulting uncategorized legacy Save payload, income refusal, and
  source-refresh/month invalidation.
- Existing FinanceW contracts and Budget Qt workflow run these tests.
  These source/fictional checks are not Silverblue native acceptance.

## WATCH OUT FOR / NEXT

M3c requires a root integration review, exact-head CI and operator
merge approval. An operator desktop visual check after merge is
separate from this PR's source and offscreen UI tests.

The next later milestone (M3d) could connect a **separately approved,
Nurse 2-reviewed** categorized Save bridge, but only after the
M3b writer passes disposable real-Actual integration and recovery
verification. Do not provide, provision or reuse any financial
permission on the user's host merely because the GUI works.

No user host, Actual budget, credential, bank record, live permit or
financial journal was modified by this work. Rollback is a source
PR revert; nothing in the new UI can write categorized transactions.
