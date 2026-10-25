# FinanceW Market STOCKS // DAY and RANGE M11

## IMPLEMENTATION

M11 separates historical market inspection into two explicit submodes,
without changing M10's source, date-range endpoint, market-data hub or
EODHD provider entitlements.

- **DAY**: one Finance date control. The selected calendar date is sent
  to the same bounded historical endpoint as `from=to=selected day`.
  If EODHD returns exactly one actual daily close, display that date,
  closing price, price basis and DIRECT/HUB/cache source details.
  If no session exists (for example, weekends or market holidays),
  display **NO TRADING SESSION**, not zero dollars, a fabricated previous
  close, or a made-up single-day percentage.
- **RANGE**: preserves M10's original pair of START and END Finance date
  controls, 180-calendar-day cap, actual daily close chart, first/last
  sessions and descriptive percent change.
- The selected mode and its respective dates are independent. Switching
  to DAY leaves the RANGE dates unchanged, and switching back restores
  them. Each mode switch clears the previously displayed snapshot;
  untrusted late responses cannot appear under the other mode.
- Defaults to RANGE, preserving the existing user-facing workflow.
- The new selector is in Finance → Market → STOCKS, not the main
  FinanceW mode rail. It uses the existing ActionButton and FinanceDateInput
  components, canonical palette, and compact stacking behavior.

## HOW TO USE

After operator review/merge and safe local update:

1. Open **Finance → Market → STOCKS**.
2. Choose **DAY** and set a calendar date, then press **LOAD DAY**.
   You can inspect an actual closing-price session or a no-session day.
3. Choose **RANGE** and select START and END, then press **LOAD RANGE**.
4. Switch between modes without losing either mode's date selection.

Only the LOAD/REFRESH action contacts the price reader. Switching modes,
changing dates, or opening STOCKS never triggers an API request.
M7's manually run hub remains optional. If absent, M8/M10's original
direct EODHD route remains available. An active but failing hub does
not silently cause a duplicate upstream request.

## VERIFY

Fake-only tests:

    node tests/finance/test_finance_stock_modes.mjs
    python3 tests/finance/test_finance_day_range_contracts.py

Covers valid/invalid date selection, mode isolation, one-session result,
zero-session result, preserving existing RANGE functionality, stale-data
clearing and exact source integrity. The existing M9/M10 range, SEC,
Polymarket, OSIRIS and Budget contracts remain in FinanceW CI.

GitHub's QML source contracts do not replace an actual Qt runtime
rendering test. After merge, confirm Compact and Expanded layouts,
single-date editing, no-session behavior, switching modes and the
existing RANGE chart. No provider access beyond the existing
AAPL/MSFT/NVDA pilot is implied.

## WATCH OUT FOR

- A one-day lookup gives that **day's daily close**, if it traded.
  It is not intraday information or a surrounding-day comparison.
- A DAY selection with no returned session is a legitimate read-only
  empty result. It is not a provider error and must not be padded.
- Range returns and adjusted-price values remain descriptive history,
  not trading advice or an event-causality analysis.
- No automated background work, trading order, provider configuration,
  process activation, FinanceW dimension change, or Budget mutation
  is included.
