# FinanceW FP1h // Quarterly and annual bill recurrence

## Status and dependency

Draft source-only work based on the existing FP1g code in the
\`feature/financew-schedule-edits-exceptions-fp1f-20261119\` branch.
FP1f PR #2092 merged to main; FP1g PR #2095 merged into the FP1f
feature branch, **not directly to application main**. Review and
integrate all dependent code in the correct order before FP1h
activation. Do not confuse a merged feature-branch PR with deployment.

## How to use after approval, merge and separate desktop installation

Finance → STRATEGIES → PLANS → add the bill under MONTHLY COSTS, then
SCHEDULE → BILL DUE DAY and select that expense/due day.
Next choose QUARTERLY / ANNUAL BILL FREQUENCY, select the existing
scheduled bill, select QUARTERLY (every 3 months) or ANNUAL (every
12 months), enter the FIRST PLANNED CHARGE MONTH as YYYY-MM, and save.

The expense's previously entered \`monthlyCents\` amount is now treated
as the **amount per occurrence** for this scheduled bill, not divided
across months. If the bill amount is $120 and its anchor is 2026-11
with annual frequency, the timeline models $120 in November 2026
and November 2027, not $10 or $120 every month. Months before the
anchor are not automatically charged. In a short month, the existing
due day is clamped to the last day of that month for planning only.

Other unscheduled expenses remain monthly. Other scheduled monthly
bills with no frequency row remain monthly. Income and goals retain
their existing assumptions. The option is specific to one selected
bill, not a global mode switch.

EDIT the frequency entry to change the anchor or the interval. Delete
the frequency entry using existing DELETE → CONFIRM to return that
expense to monthly recurrence. The original bill due-day entry and
expense amount remain unchanged. Deleting/relinking the base bill is
refused while frequency, skip or deferred-payment dependencies exist.

### Interaction with exceptions and deferred payments

A skip or deferral must refer to a real scheduled charge month. For
example, a quarterly bill anchored 2026-11 may be skipped or deferred
in 2027-02, but not in 2026-12. Changes invalidating existing skips
or deferrals refuse atomically until the operator explicitly reconciles
them. Deferred bills move their full manual per-occurrence amount to
the later target month, *in addition to* any normally due charge in
that target month. No bank transfer or creditor authorization occurs.

TIMELINE calculates occurrence-aware monthly costs and marks due items
as MONTHLY, QUARTERLY or ANNUAL. The older long-range FORECAST mode is
blocked while cadence records are active, because its fixed-monthly
calculator would otherwise misstate costs. Use the occurrence-aware
6/12/24-month TIMELINE instead.

## Financial and data safety

This is manual forward planning only. There is no accrual accounting,
proration, bank balance, creditor payment verification, deposit
guarantee, interest, fee, tax or exchange-rate assumption. An annual
charge may require saving money monthly outside this model. A higher
projected amount between charge months is **not automatically money
available to spend**. All unlisted expenses are unknown.

The local per-user schedule file remains in the existing FinanceW
path. v1/v2/v3 records are read without an implicit migration.
The first explicit ADD/UPDATE frequency action writes schedule schema
v4 with an explicit bill_cadence record, preserving all existing row
IDs/values, including sourceMonth on v3 deferrals. The new record holds
a reference to the existing expense, a 3/12-month interval and anchor
month; it never duplicates the amount. Later v4 edits remain v4.

The owner-only directory (0700), file (0600), non-following reads,
per-context locks, revision guards, atomic replace and file/directory
fsync are preserved. Unknown newer schema and invalid occurrence
relationships refuse without resetting data.

**Rollback**: FP1e/f/g code cannot read v4 schedule records. Protect a
backup and plan a separately reviewed migration before downgrading
after saving a cadence. Do not delete/reset unknown version files.
Five household context names are labels for one Linux user, not
independently authenticated family accounts.

## Verification

python3 tests/finance/test_household_schedule_fp1h.py
node tests/finance/test_household_recurrence_fp1h.mjs
python3 tests/finance/test_household_recurrence_fp1h_contracts.py

Inherited FP1a–g FinanceW, Market, Budget and protected Actual tests
must also pass at exact head. Native Qt/Wayland UI, scrolling, file
persistence, desktop acceptance and merge authority are separate.
No Hospital live registration is claimed.
