# FinanceW Market M29 // Historical SMA5/SMA20 relationship

## IMPLEMENTATION

M28 provides optional trailing **5-session and 20-session** closing-price lines on an already loaded EODHD RANGE. M29 adds a read-only summary of their **observed historical relationship**, without fetching more history, spending quota, persisting data, or making a buy/sell recommendation.

The existing pure `FinanceStockRangeAnalysisPolicy.js` gains `movingAverageRelationship(snapshot)`. It calls M28's validator/moving-average generator on the **same single-basis, chronological, bounded, read-only loaded RANGE**, then compares aligned SMA5 and SMA20 positions starting with index 19. Results include:

- `insufficient` and actual session count when fewer than **20 loaded sessions** exist;
- last **ABOVE / BELOW / EQUAL** SMA5 relative to SMA20 for a valid 20+ session range;
- signed difference in price units and percentage of the contemporaneous SMA20;
- number of **observed side changes** in the loaded range, separated into moved-above and moved-below;
- date and direction of the most recent side change, or NONE.

This explicitly **does not** claim the literal price intersection time, trading signal, intraday event, forecast or market-wide history. An observed side change is recorded only when a later **non-equal** SMA relationship differs from a prior non-equal relationship within the loaded sample. A period of equality is not counted as a change by itself. The first observed definite relationship is not a change. Small floating-point differences within a 1e-10 relative tolerance are treated as equal.

The existing `FinanceStockHistoryPane.qml` shows this summary beneath M28's historical averages **only while the optional 5/20 SMA overlay is on and a valid current RANGE is loaded**. With 5–19 sessions, it shows a clear **NEED 20 OBSERVED SESSIONS**, without fetching or fabricating a 20-session history. DAY/invalid data/overlay OFF hides the M29 summary.

The summary includes no new services, background processes, provider calls, quota reservations, files, credentials, watcher or chart-control behavior.

## HOW TO USE

After authorized merge and separately approved deployment:

Finance → MARKET → STOCKS → RANGE → LOAD RANGE → SHOW 5/20 SMA.

The existing SMA panel displays historical prices. M29 adds **SMA 5 VS SMA 20 // HISTORICAL RELATIONSHIP** below it, including latest relation, spread, count of observed side changes and last side-change date where available. Use **HIDE 5/20 SMA** to hide both M28 lines and the M29 summary.

No new button or provider operation is required. A 7D or 30D calendar range may contain fewer than twenty actual market sessions; that is handled as insufficient loaded history, not a request to fill missing sessions.

## VERIFY

- `tests/finance/test_market_m29_sma_relationship.mjs` uses fictional in-memory price series to verify 1/19 sessions insufficient, 20 equal closes showing equal/no change, initial above/below states without inventing a crossing, and a 50-session high/low/high fixture with exactly **two** observed side changes (one moved below, one moved above, last at the observed index 42). Frozen input remains unchanged. Invalid source/basis/first-last/sequence/price/length fails closed.
- QML source assertions ensure M29 appears only from the existing loaded range/SMA overlay, with no read, process, writer, provider, or quota command in its content.
- M29 joins the established Market M10–M29 `test_market_price_range.mjs` chain; the existing `financew-market-m26-range-analysis.yml` CI job adds M29 trigger paths and runs that entire mock-provider suite.

## WATCH OUT FOR

The direction and count are **relative comparisons of trailing historical closing-price averages**. They do not indicate an investment action, predict future returns, report a live quote, reflect actual invested holdings, or count every theoretical intersection between observation dates. Adjusted closes may later be revised by the provider after dividends/splits.

Only the history **already loaded** is inspected, so starting with 20 sessions can yield a side but cannot establish whether a side change happened before the range began. Never infer no historical side changes beyond the selected sample.

This is ordinary Market analysis, not Universal Connections or a change to the protected M20 quota ledger. A focused M20 filesystem review remains a separate security-only Nurse 2 matter. Main Quickshell working tree, local files, processes and provider accounts must remain untouched by GitHub source-only work.

## CHECKLIST

- [x] M28 merged to main and operator-reported native functional PASS
- [x] Current Syntagma/Market code and M29 PR collision preflight
- [x] Pure historical SMA relationship and conditional existing-panel UI
- [x] Fictional/data-refusal tests and established Market regression CI wiring
- [ ] M29 exact-head CI and raw job evidence
- [ ] Operator merge authorization and later native visual acceptance

## NEXT

Check the exact-head CI and retain a draft PR until authorized. Native review should use already-loaded history without spending a provider request purely to test this summary.

**DRAFT / NO NEW API REQUESTS / NO HOST MUTATION / PRODUCTION HOLD.**
