# FinanceW FP1d // Manual Household Budget Timeline

## Intent and operation

Finance → STRATEGIES → PLANS → TIMELINE (after independent review,
operator merge approval and separate desktop update).
Select a local planning context and a 6, 12 or 24-month horizon.
The view reads its existing manually entered income, monthly expenses,
savings goals and optional YYYY-MM goal deadlines. It does not read
Actual Budget or an external bank.

A month card displays its assumed income, listed recurring monthly costs,
planned goal contributions capped at their manual goal target, and a
cumulative projected CHANGE from the start month. This is not available
cash and does not imply the user can afford a purchase.

Goal deadlines are presented as milestones. A goal called "car" with
target month YYYY-MM can represent a major purchase savings plan, but
the timeline never assumes a car is actually purchased, never charges
its target as a second expense and does not move savings into a bank.
A month with a target gap shows it. Previously missed target dates
receive a separate notice.

Income and expenses repeat monthly because the existing schema has no
specific due day, frequency other than monthly, or one-time purchase
record. We do not invent payment dates. The first month is the user's
current local calendar month. This is a constant-rate simulation; real
income, tax, debts, inflation, unusual costs, starting cash, price
changes and bank-verified balances are not supplied here.

## Architecture and data boundary

FinanceHouseholdTimelinePolicy.js is pure in-memory arithmetic: it
refuses unrecognized contexts, invalid months or money, duplicate row IDs,
missing income and unexpected horizons. It never performs IO.
FinanceHouseholdTimelinePane.qml is mounted inside the pre-existing
FinanceHouseholdPlansPane.qml scroll content, with only current selected
local records supplied after the plan store reports ready.

No storage schema, household membership, bank account registry,
Social, Identity, Connections, Actual Budget or protected writer changed.
The five plan contexts are separate local plaintext files readable by the
same Linux user, not independently authenticated household members.

## Verification

node tests/finance/test_household_timeline_fp1d.mjs
python3 tests/finance/test_household_timeline_fp1d_contracts.py
Existing FinanceW FP1a/b/c, Market and Actual regression CI.

Real Qt/Wayland compact/expanded/fullscreen scroll and keyboard acceptance
remains pending. This change is draft-only and not a live desktop update.
