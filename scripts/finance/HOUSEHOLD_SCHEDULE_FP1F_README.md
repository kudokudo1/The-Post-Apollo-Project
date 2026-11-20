# FinanceW FP1f // Editing schedules, one-month bill exclusions, coverage

## How to use after review, merge and separate desktop installation

Finance → STRATEGIES → PLANS → SCHEDULE.

For existing bill/purchase records, choose EDIT, change values and
UPDATE SCHEDULE. The record ID stays the same. Stale revisions are
refused. CANCEL EDIT discards unsubmitted changes.

Choose ONE-MONTH BILL EXCLUSION, select an existing scheduled bill, enter
YYYY-MM and SAVE. The timeline excludes only that particular bill from
the indicated month's manual cost estimate. Adjacent months are
unchanged. A bill and month pair may have only one exception. To remove a
bill with exceptions, delete its exceptions first, avoiding silent
loss of user-entered schedule state.

An excluded modeled payment is NOT confirmed waived, cancelled or paid.
No omitted bill is automatically carried forward to another month. To
represent a deferred payment, the operator must separately enter the
future planned payment. This model is not a creditor schedule or bank
balance.

TIMELINE displays due-day coverage: the number of entered monthly costs
with date annotations, names of entered costs missing due dates and
an explicit warning that unlisted obligations remain unknown. An
undated expense remains included in monthly costs.

## Storage

Existing FP1e schedule v1 documents are validated and projected to v2
in memory on read, with no disk write. Only an explicit add, update,
delete or exclusion save writes v2. It preserves old record IDs and
values. The new bill_skip record uses a bounded month, expense ID and
no amount; no bank transaction or secret is stored.

Same 0700 directory/0600 files, nofollow, revision, per-context locking,
atomic replace and fsync. Malformed/newer data, stale writes, duplicate
exceptions, or orphan references fail closed. Original household plan
files remain unchanged.

## Boundaries and verification

Five contexts are labels for the SAME Linux login. They are not
authenticated household logins or encrypted records. No Actual,
Connections, Identity, Social or bank source touched.

python3 tests/finance/test_household_schedule_store_fp1e.py
python3 tests/finance/test_household_schedule_fp1f.py
node tests/finance/test_household_schedule_timeline_fp1e.mjs
node tests/finance/test_household_schedule_timeline_fp1f.mjs
python3 tests/finance/test_household_schedule_fp1f_contracts.py

Existing FinanceW FP1a-e and protected Actual/Market CI must pass.
Real Quickshell desktop acceptance and merge authorization are pending.
