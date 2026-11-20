# FinanceW FP1c // Edited plans, income assumptions, monthly deltas

## Use (after review, merge, separate operator desktop update)

Finance → STRATEGIES → PLANS. Choose the local planning context.
Existing savings goals and monthly costs offer EDIT, keeping the same record
ID. Edits require a current revision and an explicit UPDATE.
An optional goal deadline is entered as YYYY-MM.
Add planned income from MONTHLY INCOME. Open FORECAST and select 12/36/60,
120 or 360 months to inspect the hypothetical change at fixed monthly rates.
An open edit refuses saving if the selected record/revision changes.

Projection = listed monthly income - listed monthly expenses -
monthly contributions for incomplete goals, multiplied by the horizon.
No cash-on-hand or net worth is calculated. This is NOT a bank balance,
guaranteed savings, purchase affordability, or reconciled financial advice.
Unlisted expenses are unknown, not zero. The model excludes interest,
inflation, tax, raises, irregular purchases, financing, and automatic
adjustments when goals reach completion.

## v1 compatibility

Existing FP1b v1 JSON documents are validated then projected into v2 IN
MEMORY without writes on list. First explicit add/edit/delete writes
v2 while preserving prior row IDs and amounts, with blank deadlines for
legacy goals. No automatic destructive migration or import is performed.
Unrecognized, malformed, unsafe or newer-version data fail closed.

The existing 0700 directory / 0600 file, non-following reads, per-context
advisory lock, revision check, fsync and atomic replacement stay in place.
All five planning contexts are labels accessible to the SAME Linux user.
Do not treat them as independent personal authentication or bank grants.
Plans are plaintext local files, NOT encrypted at rest.

## Verify

python3 tests/finance/test_household_plan_store.py
python3 tests/finance/test_household_plan_store_fp1c.py
node tests/finance/test_household_cashflow_fp1c.mjs
python3 tests/finance/test_household_plans_fp1c_contracts.py

Existing FinanceW FP1a/b, Budget and Market regression checks also apply.
Real Quickshell layout, keyboard, source persistence and host-side recovery
remain subject to independent review and operator acceptance.
No Connections, Social, Identity, Actual Budget or bank writer was modified.
