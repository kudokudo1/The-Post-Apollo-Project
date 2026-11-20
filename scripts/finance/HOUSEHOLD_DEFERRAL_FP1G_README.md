# FinanceW FP1g // Explicit one-occurrence bill deferral

## Parent and ownership

This FP1g branch is **stacked on FP1f PR #2092**, not application main.
Do not merge, cherry-pick, or activate FP1g before FP1f has passed its
independent review and been operator-approved. Neither this document
nor a green CI run grants merge or production authorization.

## Operator path after authorized merge and a separate host update

Finance → STRATEGIES → PLANS → SCHEDULE → DEFER ONE BILL TO A LATER DATE.
Choose an already-scheduled monthly expense, enter the ORIGINAL BILL
MONTH as YYYY-MM, and the NEW MODELED PAYMENT DATE as YYYY-MM-DD in a
strictly later calendar month. Save, then open TIMELINE.

For the source month, the bill is no longer subtracted from the manual
monthly costs. For the payment month, that deferred bill is subtracted
as a *second modeled bill payment*, in addition to the ordinary recurring
bill for the new month. Both entries show source and target dates.

This differs from FP1f's ONE-MONTH BILL EXCLUSION: an exclusion omits a
month without modeling repayment. A deferral explicitly models later
repayment. No same-expense/source-month exclusion and deferral may coexist.

Operators may EDIT a deferral to move its model date, retaining its ID,
or DELETE (then CONFIRM) to return to the ordinary monthly plan.
The parent bill cannot be deleted or linked to a different expense
until its deferrals have been removed. A duplicate deferral of the
same bill/source month is refused, as is an invalid/leap date.

A payment scheduled after the selected 6-, 12- or 24-month window
appears as a moved-out source entry without a payment card in that
visible horizon. Check a longer horizon before interpreting the
cumulative change. A source date before the visible start may still
have a future target payment in the timeline.

## Monetary and evidence limitations

The moved amount comes from the *current manual monthly expense amount*,
NOT a frozen statement, bank invoice, or legal debt schedule. If that
expense amount is edited, both simulated source and target calculations
change accordingly. The UI makes no claim about actual creditor
consent, delinquency fees, penalties, or paid/unpaid status. No account
is contacted, no funds move, and no payment is authorized.

For quarterly/annual bills, the household plan store still treats
each expense as recurring monthly. Frequencies must not be added as
mere visual date labels: FP1h requires separate ledger semantics to
avoid continuing to debit an annual invoice every month.

## Data and rollback

Schedule documents v1/v2 are read and validated without a write.
The first explicit deferral command upgrades that context to v3,
adding empty sourceMonth fields to existing rows while retaining IDs,
old values and the revision guard. The same 0700/0600 local privacy,
nofollow, advisory lock, atomic replace and fsync stay in effect.

Old FP1e/f code cannot read a version 3 document and should refuse it,
not reset it. Before reverting the application, retain a protected
backup and arrange a reviewed migration for any v3 files. Do not
downgrade or delete unknown version records automatically. These are
plaintext local records, and all five context labels are accessible
to the same Linux user, not separately authenticated family accounts.

## Verification

python3 tests/finance/test_household_schedule_fp1g.py
node tests/finance/test_household_deferral_fp1g.mjs
python3 tests/finance/test_household_deferral_fp1g_contracts.py

All inherited FinanceW FP1a–f, Actual/Market and repository contract
checks must remain green. Native QML layout/interaction and operator
acceptance are still pending. No Hospital live registration asserted.
