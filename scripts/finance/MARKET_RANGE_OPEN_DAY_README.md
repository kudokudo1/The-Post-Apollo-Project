# FinanceW Market STOCKS // M13 OPEN IN DAY

## IMPLEMENTATION

M13 adds an explicit **OPEN IN DAY** action beneath the session already
selected in the M12 RANGE chart. It reuses only the real EODHD bars already
retrieved and checked by FinanceW.

- Click a RANGE chart point to inspect its date and closing price. This
  remains read-only and creates no provider request.
- Press OPEN IN DAY to transfer **exactly that trading session** into
  the existing DAY view. No `reader.exec()`, HTTP call, local hub access,
  retry, timer or new provider key. The DAY date is set to the selected
  session's date, not today's date or an interpolated weekend.
- In the DAY view, the date, close, price basis, symbol and original
  EODHD source/cache timestamps remain visible. A separate
  `DAY SOURCE // PREVIOUSLY LOADED RANGE // NO NEW REQUEST` label
  distinguishes this from an independently fetched DAY history result.
- The original RANGE START and END selector values are unchanged.
  Switching back to RANGE restores the selectors; the normal LOAD RANGE
  action retrieves the range again. The prior chart data is not retained
  across the mode transition in this milestone.
- Manually selecting another DAY, or explicitly pressing REFRESH DAY,
  retains the existing DAY behavior and can make the usual user-initiated
  provider request.

The pure `FinanceStockModePolicy.daySnapshotFromRange` validates source,
CIK, symbol, range, selected session index, price, price basis, delivery
metadata and read-only shape. It returns a new one-bar DAY-shaped
snapshot with null percent change and `derivedFromRange:true`.
Neither the original range bars nor their source metadata are mutated.
M12's existing chart selection and clearing semantics are preserved.

## HOW TO USE

After reviewing and merging the M13 draft PR and safely updating your
Quickshell setup:

1. Finance → Market → STOCKS → RANGE.
2. LOAD RANGE, then click near any plotted session.
3. Click **OPEN IN DAY**, beneath the selected session detail.
4. Verify the DAY view contains the *same* date and close immediately,
   marked as loaded from the original RANGE. No spinner or new provider
   request should occur.
5. Switch to RANGE. The same START/END dates remain selected; press
   LOAD RANGE to plot them again.

Manual DAY requests outside the saved RANGE dates also work in M13.
The validator now checks returned sessions against **the active mode's
requested window**, not the unrelated saved RANGE dates. This fixes an
M11 edge case without changing the provider or date limits.

## VERIFY

Fake-only offline checks:

    node tests/finance/test_stock_range_to_day.mjs
    python3 tests/finance/test_stock_range_to_day_contracts.py

They cover exact selected closing prices, no source mutation,
wrong-issuer or mismatched-range refusal, bad delivery metadata,
first/middle/last actual sessions, no fabricated percent change,
mode/date isolation, no automatic process/HTTP calls and the corrected
DAY requested-window validator.

Existing M5–M12 SEC, optional hub, Price RANGE, DAY/RANGE and chart-point
tests continue in the FinanceW GitHub workflow. CI validates code and
fictional sessions only; it does not render your Qt/Wayland desktop.

## WATCH OUT FOR

The transfer copies one trading session from a previously fetched
range. It is not a fresh independent EODHD response or a live quote.
Cache/retrieval timestamps belong to the original range fetch and
remain labeled as such.

No changes to issuer coverage, EODHD licensing, optional hub activation,
trading orders, Budget writers, Polymarket, OSIRIS, SEC Research, FinanceW
window dimensions or host processes. No automatic updates or polling.
