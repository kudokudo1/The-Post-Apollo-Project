# FinanceW Simple M3b // Dormant Categorized Expense Writer

## IMPLEMENTATION

**State: SOURCE-ONLY / NOT MOUNTED / DISABLED BY DEFAULT.**

M3a category-preview PR #2347 is merged. M3b introduces a separate, guarded creation path for one **new categorized negative expense**. It does not alter the existing transaction editor, uncategorized writer, Quickshell root, permissions, or a real budget.

The project pins Actual API **26.10.0** in scripts/finance/package.json. The official Actual API reference says Transaction create/read accepts the **category** ID field, and addTransactions can create a transaction with this category in one operation. FinanceW's D9 implementation previously observed "ok" instead of a documented returned ID array on this version. M3b accepts only "ok" or an exact one-ID acknowledgment and then mandates category readback.

Source:
- scripts/finance/categorized_expense_guard.mjs: strict 13-field command, source/ID/category/month/account/amount preflight, duplicate protection, single create containing category, sync, exact ID/category readback.
- scripts/finance/write_categorized_expense.mjs: dormant operator-permitted CLI with the shared finance write lock and ATTEMPTED / COMMITTED durable journal; no automatic retry or recovery cleanup.
- New isolated fictional policy and CLI tests, denial/authority source contracts and CI.

## MECHANISM

Command fields are action, requestId, sourceKey, accountId, month, date, description, amountCents, categoryId, expectedCategoryBudgetedCents, expectedCategoryAvailableCents, expectedCategorySpentCents, expectedToBudgetCents.

All money is integer cents; amountCents must be negative. Account must uniquely identify an active on-budget account. Category must uniquely identify a visible expense category, never an income category. Category budgeted, available, spent and total To Budget must still match a *fresh* Actual read before write. An existing same-day/same-amount transaction refuses to avoid duplicates.

The single addTransactions operation includes category: categoryId from the outset. No second updateTransaction operation is issued. After sync, a new read must show exactly the expected transaction ID, category ID, account, date, negative amount and imported ID. A further budget-month read must confirm that category still resolves. Actual owns the authoritative resulting balance; M3b does not invent a new To Budget amount.

**One API call is not an atomic transaction across network sync and the local journal.** A crash, unknown acknowledgement, sync failure or readback mismatch after ATTEMPTED is **UNCERTAIN**, and cannot be automatically retried.

## PERMISSION AND RECOVERY: HARD HOLD

A separate operator-owned private file would be required in the future:
- Path: ~/.config/financew/categorized-expense-writes-enabled
- Exact value: FINANCEW_CATEGORIZED_EXPENSE_WRITES_APPROVED

**Do not create it, modify a local machine or activate it as part of this PR.** The existing transaction permit does not authorize categorized creation. Source merge is not activation or financial acceptance.

Before the first Actual mutation, the CLI holds the shared FinanceW lock, checks sourceKey and exact localhost Actual source, refuses all unresolved journals and reused request IDs, and durably fsyncs its ATTEMPTED file **and the directory**. A failed post-attempt operation leaves that journal in place to block this and other FinanceW writers pending explicit manual investigation. Never delete a recovery marker or automatically retry merely to resume.

## VERIFY

The tests run a stub Actual module and fictional ledger in disposable CI HOME. They test preflight refusal, wrong category on readback, duplicate imports, permit permissions, attempted journal durability, abandoned lock, interrupted add/sync and cross-writer fail-closed behavior. There is no real user's Actual server or account in the CI.

**Remaining verification:** independently reviewed security boundary and disposable real Actual API 26.10.0 integration proof. Official API documentation does not by itself prove that the pinned runtime has passed a real write rehearsal.

## NEXT

After independent review and disposable real-API verification, a separate M3c UI PR may attach category selection to a protected expense Save path. That UI must prove that a saved category ID persists, handle invalidation and restore the source faithfully. Real financial write activation needs explicit operator approval. M2b envelope-move writer remains a separate independent security HOLD.

Rollback before activation: revert the source PR. No real records or local permissions have been changed by this milestone.
