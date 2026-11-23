# FinanceW Market M26 // Read-only loaded RANGE movement statistics

## IMPLEMENTATION

The STOCKS RANGE screen previously displayed first/last daily closes and their percentage change. M26 extends it with **descriptive movement statistics derived entirely from the already loaded, validated EODHD closing-price snapshot**. It does not request an additional market quote or reserve a provider slot.

A new pure QML JavaScript policy `FinanceStockRangeAnalysisPolicy.js` accepts the existing `schemaVersion:1`, `source:eodhd-eod`, `readOnly:true`, single basis `CLOSE` or `ADJUSTED CLOSE` range snapshot with 1–132 strictly increasing, valid dated, positive-price sessions inside the requested period. It also checks that `first` and `last` match those actual bars. Unknown, stale, mixed, misordered, duplicated, oversized or malformed ranges return `null` rather than pretend numbers.

It returns copies of:

- highest and lowest **observed closing price** and dates,
- largest chronological peak-to-subsequent-trough decline within that loaded range,
- count of consecutive observed session-to-session closing increases, decreases, and unchanged closes,
- biggest positive and negative consecutive session-close percentage moves, where present.

The pure function does not annualize, infer weekend/holiday sessions, contact providers, read files, make recommendations or label daily closes as intraday high/low. It never modifies the original bars.

`FinanceStockHistoryPane.qml` adds a read-only, wrapping summary panel below the existing range first/last comparison, visible only for current selected issuer and matching start/end RANGE, not in DAY. Results automatically follow the current snapshot and vanish when invalid or DAY-selected. The rest of chart selection and direct-range/day navigation remains unchanged.

## HOW TO USE

After a separately authorized merge and deployment:

Finance → MARKET → STOCKS → RANGE → choose issuer and dates or 7D/30D/90D/180D → LOAD RANGE.

Under the existing first/last summary, a **RANGE MOVEMENT** panel shows high/low closes, max peak-to-trough drop, session up/down/flat counts, and largest close-to-close moves. It will not appear for DAY, unloaded, stale or invalid data. No new API/token, user configuration, database, chart mode or button is added.

## VERIFY

- `tests/finance/test_market_m26_range_analysis.mjs` verifies exact fictional statistics, chronological drawdown (not global high minus an earlier low), upward/declining/flat/single-session cases, detached nonmutating results, and rejection of invalid dates, duplicate/misordered rows, NaN/Infinity, impossible prices, mismatched summary boundaries, non-EODHD or read-only-invalid sources.
- Test verifies the production QML panel's new labels, read-only boundaries, no process/provider or mutation code in its source span.
- Existing `test_market_price_range.mjs` includes M26 so the established M10-M21 provider/hub/quota mock regression suite exercises it without real external provider calls.
- Dedicated GitHub workflow runs the new test and full Market range regression on a disposable Ubuntu runner with Node 22.

## WATCH OUT FOR

This is **descriptive historical close data**, not intraday high/low, actual portfolio performance, a forecast, a technical investment signal or a provider-account quota. Adjusted-close history can change following subsequent corporate actions; figures are recomputed from the currently loaded price basis, not stored for trading decisions. Selected session steps may span multiple calendar days.

M25's separate quota UI PR #2318 remains unmerged as of M26 preflight, with **no overlapping M26 changed files**. M26 does not alter the M20 protected SQLite ledger, provider price readers, quota status screen, Banking, Research, Strategies or Connections. No host machine changes.

## CHECKLIST

- [x] Current Market code / M25 ownership and Syntagma preflight
- [x] Pure loaded-range analysis policy and read-only STOCKS panel
- [x] Synthetic functional and source regression tests
- [x] Dedicated workflow and existing Market test-chain hook
- [ ] M26 exact-head CI and raw output verification
- [ ] Operator merge approval and subsequent native UI observation

## NEXT

Fix any exact-head CI issues in this draft branch. After CI PASS, present the source diff and operator acceptance path; do not merge or restart live Quickshell without the necessary approval.

**SOURCE-ONLY DRAFT / NO PROVIDER REQUESTS / NO LIVE HOST WRITES.**
