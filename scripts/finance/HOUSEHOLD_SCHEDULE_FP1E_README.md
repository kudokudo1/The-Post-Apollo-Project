# FinanceW FP1e // Bill due days and one-time purchases

## Scope and operator path

After code review, approved merge and separate operator-authorized desktop
update:

Finance → STRATEGIES → PLANS → choose local context → SCHEDULE.

To schedule a recurring bill, first add it in MONTHLY COSTS. Return to
SCHEDULE → BILL DUE DAY, select the existing expense, set day 1-31, then
SAVE BILL DUE DAY. Only one bill-day record is allowed per expense.
The bill schedule holds no copy of the amount: its reference points at
the cost already included once in monthly projections.

For a one-time purchase, select ONE-TIME PURCHASE, enter its description,
exact YYYY-MM-DD date and planned amount. Choose either NEW CASH or one of
the existing savings goals as a funding source, then SAVE PLANNED PURCHASE.
For deletion, click DELETE and then CONFIRM. Editing a schedule is not yet
supported; delete the schedule and create a replacement.

Open TIMELINE to see the scheduled bill days, projected one-time payments
and funding split in each 6/12/24 month scenario. Days 29-31 are shown as
the final day of shorter months; this is a documented *planning rule*,
not a claim about a creditor's actual due-date policy.

## Financial semantics

Monthly expenses remain monthly, regardless of whether they have a due
date; due-day annotations NEVER add the expense again. The timeline
subtracts one-time planned purchases from NEW CASH in their scheduled month
unless the user explicitly linked a goal. For a linked goal, model
contributions accumulated from previously entered manual figures are
used once; any excess purchase amount is a new-cash shortfall. After the
modeled purchase, contributions toward that one-time goal stop.

A savings-goal deadline is still just a milestone, NOT a payment.
A planned purchase is a hypothetical scenario, NOT an actual card charge,
bank transfer, completed purchase or cash balance. These calculations
never synchronize accounts or move funds. Starting cash, taxes, debt,
uncertain fees, irregular income, inflation and unknown bills are omitted.
A past purchase date is shown as a past *planned* item and never marked paid.

The UI does not guarantee a linked goal actually has the money available.
These forecasts are operator assumptions, not financial advice or verified
affordability.

## Storage, ownership, recovery

The original FP1b/FP1c household plan records remain unchanged in
XDG_DATA_HOME/post-apollo/finance/household-plans/<context>.json.

New schedule metadata is stored in the SAME FinanceW domain in
XDG_DATA_HOME/post-apollo/finance/household-schedules/<context>.json.
This is not a bank account database, another Identity Center, or another
copy of transactions. Directory 0700, file 0600, per-context revision and
nonblocking lock, symlink and permission rejection, bounded schema,
atomic replace and fsync apply. A read does not create a record.

All five contexts remain *labels for one Unix user*, not independently
authenticated family members. The schedule store does not contain financial
credentials, Actual Budget data, providers or permission grants.
Deleting an expense or goal referenced by a schedule is not silently
repaired; the timeline refuses to calculate until the orphan schedule
is deleted or the referenced plan record restored. This is deliberate.

## Verification

python3 tests/finance/test_household_schedule_store_fp1e.py
node tests/finance/test_household_schedule_timeline_fp1e.mjs
python3 tests/finance/test_household_schedule_fp1e_contracts.py

Earlier FP1a/b/c/d and Actual/Market regression tests also apply.
Native Qt/Wayland compact/fullscreen, keyboard input, and local data
durability acceptance remain pending. Do not merge or activate without
the operator's required authorization.
