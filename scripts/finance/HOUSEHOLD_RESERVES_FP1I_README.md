# FinanceW FP1i // Read-only sinking-fund earmarks

## Scope

This increment adds an optional **planning estimate** to FinanceW's
existing Finance → STRATEGIES → PLANS → TIMELINE.

Quarterly and annual expenses already use the per-charge amount and
actual recurrence months established by FP1h. FP1i does **not** change
the timing or the cash cost of those bills, and does **not** create
separate account balances, bank transactions, payment authorizations,
new local records, migration scripts or protected writer calls.

Instead, it projects an amount that could be earmarked each month for
each existing quarterly (every 3 months) or annual (every 12 months)
bill, using its current manually entered full charge amount.

## Financial semantics

The recommended modeled earmark equals the charge amount divided by
the recurrence interval, in integer cents. Cent remainders are assigned
to specific phases of each recurrence cycle, so the sum of a complete
3- or 12-month cycle equals the full bill exactly, with no drift.

Examples:
- A $900 quarterly charge produces three $300 earmarks per cycle.
- A $1,200 annual charge produces twelve $100 earmarks per cycle.
- A $100.01 quarterly charge splits into $33.34, $33.34 and $33.33.

Modeled earmarks accumulate in a separate *notional* bucket. When an
eligible modeled bill charge occurs, the policy applies available
notional reserves first, limited to the bill amount. Any charge beyond
the projected reserve is labeled a **model shortfall**; it remains a
cash-flow expense in the existing timeline, not an unpaid invoice claim.

A skipped occurrence has no modeled charge and therefore does not
draw down the earmark. A deferred occurrence is funded, to the extent
available in the model, only in its new payment month. The destination
month may also have its ordinary bill; both charges remain visible.
No changes are made to the earlier FP1f/g/h source charge calculations.

An earmark is **not another expense**. The original cash-change model
remains unchanged. The unreserved-change view is computed using:

    unreserved change = modeled cash change
                        - newly earmarked amount
                        + notional reserve used on scheduled charges

The cumulative unreserved change equals the preexisting cumulative
cash-change estimate minus the ending notional reserve. This is a
conservation check, not an observed account balance.

## Starting conditions and limitations

**Starting cash and actual saved reserves are UNKNOWN.** The model
starts with zero notional funds at the beginning of the selected
6/12/24-month projection window; it does not invent historical savings.
If an annual bill arrives early in that window, its fund may cover only
a small part of the bill. The model flags that shortfall rather than
asserting the balance was already accumulated.

If the first charge is in the future, the model begins suggested
earmarks within the last N months before that scheduled first charge,
but the visible window may not cover the entire interval. Earmarks are
suggestions, not standing orders. Nothing is actually saved or moved.
Model "unreserved" is **not spendable cash**, affordability, net worth,
legal debt status, or bank-verified income. Unknown bills, taxes,
interest, inflation, income variability and family access permissions
remain outside the model. Five planning contexts remain one local Unix
user's labels, not independently authenticated family identities.

## Data, source ownership, and rollback

Implementation: pure in-memory
\`widgets/FinanceHouseholdReservePolicy.js\`, imported by the existing
\`widgets/FinanceHouseholdTimelinePane.qml\`. It consumes only the
already-validated local timeline output and selected manual plan
records. No changes to FP1h schedule v4 or FP1c plan v2 file formats.
There are no file writes or network calls in the new policy.

Rollback is to revert the two FP1i source changes and new test/docs
without any data conversion. **However**, existing FP1g/FP1h v3/v4
schedule files still require their separately documented rollback
protection; FP1i does not solve or weaken that requirement.

## Verification

node tests/finance/test_household_reserves_fp1i.mjs
python3 tests/finance/test_household_reserves_fp1i_contracts.py

Retain all FP1a-h, read-only Actual Budget and Market contracts.
Native Quickshell scroll, responsive layout, long text, source record
switching, and operator acceptance remain separately required.
