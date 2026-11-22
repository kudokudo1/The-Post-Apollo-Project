# FinanceW FP1j // In-memory configurable reserve cushions

## Dependency and scope

FP1i PR #2106 is merged to application main. The operator explicitly
approved that interface on 2026-11-21 in the conversation, but this
does **not** constitute independent security review or proof of
live-host installation. No live Hospital registration is asserted.

FP1j adds **optional reserve cushion scenario choices**, with no new
storage schema, bank account, credential or persisted household settings.

## How to use (after independent review and separately authorized merge)

Finance → STRATEGIES → PLANS → TIMELINE.

For a household with at least one entered quarterly or annual bill,
select one of three controls:

- **100% BASE:** The existing FP1i monthly earmark, no extra cushion.
- **110% +10%:** Build an extra notional cushion equal to 10% of the
  entered per-occurrence bill price.
- **125% +25%:** Build an extra notional cushion equal to 25% of the
  entered per-occurrence bill price.

Each choice immediately updates only the read-only reserve estimates.
It does not change source bill amounts, due dates, income, existing
savings goals, cash-flow charges, bank records or anything on disk.

**Controls are session-only** and reset to 100% whenever the household
context changes. This is deliberate: no silent cross-household scenario
inheritance, no new local write path, no claim that reserves exist.

## Precise calculation semantics

The original FP1i *base* monthly earmarks continue unchanged, including
cent-accurate 3/12-month division, skipped occurrences and deferred
payment rules. The extra cushion is modeled separately:

    cushion target cents = ceiling(bill amount cents × (percent-100)/100)

The extra target is divided into 3/12 monthly allocations using the
same cent-exact rounding. Extra allocations **stop** when the extra
cushion has reached that fixed target. This avoids collecting another
extra 10%/25% on every future cycle indefinitely.

At each simulated charge, the modeled base earmark is consumed first
and the extra cushion only if needed. The modeled cushion is replenished
in subsequent eligible months after any drawdown, up to its fixed target.
A skipped occurrence consumes nothing. A deferred occurrence consumes
the notional reserve in its modeled payment month, not its original.

Both allocations are hypothetical internal earmarks, not expenses.
The original FP1h projected cashflow totals are unchanged. The
FP1i conservation invariant remains:

    unreserved monthly change =
        original modeled cash change - modeled deposits + reserve used

    cumulative unreserved change =
        original cumulative modeled cash change - ending notional reserve

The reserve starts at zero at the beginning of the visible 6/12/24-month
window. It does not infer savings from a past month, a connected account,
or a family's bank balance. An early due bill may still be underfunded
in the model despite an extra cushion choice.

## Risk, compatibility, rollback

There are no file writes, bank transfers, payment instructions,
financial identity grants or new storage versions. FP1j adds only
scenario computations, UI buttons, tests and this documentation.
Rollback requires only code reversion to FP1i; no FP1j data migration.

Existing FP1g/FP1h v3/v4 saved schedule compatibility remains a
separate risk. Before rolling back those features, retain a protected
backup of newer local schedule records rather than resetting them.

No model output is verified available cash. Unknown household costs,
inflation, fees, tax, debt, irregular income, and actual family
permissions remain outside the scenario.

## Verification

node tests/finance/test_household_reserve_cushion_fp1j.mjs
python3 tests/finance/test_household_reserve_cushion_fp1j_contracts.py
node tests/finance/test_household_reserves_fp1i.mjs

Run all inherited FinanceW FP1a-i and protected Actual/Market workflows
at exact PR head. Native Quickshell wide/narrow viewport, keyboard
interaction and operator acceptance for **FP1j** remain pending; the
earlier FP1i approval does not preapprove this new UI.
