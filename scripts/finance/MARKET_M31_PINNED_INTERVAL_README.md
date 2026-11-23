# FinanceW Market M31 // Observed interval between pinned A and selected B

## IMPLEMENTATION

M30 allows choosing two historical closing-price sessions from the exact same already-loaded EODHD RANGE (A pinned, B selected). M31 shows **what happened between those sessions**, in addition to their endpoint change. No further provider API request or quota reservation is needed.

The existing pure Market policy `FinanceStockRangeAnalysisPolicy.js` gains `summarizePinnedInterval(snapshot,firstIndex,secondIndex)`. It begins by calling M30's strictly validated, read-only A/B comparison. After checking both actual bar indices, it examines only the inclusive, *chronologically ordered* subrange from the earlier index to the later index. It reports copies of:

- Earlier and later actual closing dates/prices and count of observed loaded sessions.
- Highest and lowest **observed daily closing price** and their dates within the chosen subrange.
- Largest chronological peak-to-subsequent-trough decline between observed closing prices within that subrange, including the dates if a decline occurred. A subrange that never fell reports **0% / NONE OBSERVED** instead of inventing an event.
- Counts of observed up/down/flat consecutive session-close transitions and total observed transitions.

These interval statistics have the same values when A and B are selected in reverse chronological order. This is intentional: the history between two dates is the same, while M30's **B minus A** signed comparison preserves the operator's selection direction. The calculation never treats calendar weekends/holidays as sessions.

`FinanceStockHistoryPane.qml` displays a read-only **BETWEEN PINNED A AND B** panel directly below M30's existing A/B endpoint comparison. It reuses M30's exact loaded snapshot identity, validated issuer and date-range checks, current selected point and pin invalidation. Choosing a new B updates it. Clearing A/B, switching DAY or replacing a range hides it. No new buttons or service required.

No provider adapter, network process, SQLite ledger, caching, security credential, trading permission, Banking, Strategies, Research or Universal Connections code changes.

## HOW TO USE

After separately authorized merge and native source deployment:

1. Finance → MARKET → STOCKS → RANGE → load an existing historical range.
2. Click a chart point A and press **PIN AS A**.
3. Click another actual returned session B. Under the existing B-minus-A comparison, read **BETWEEN PINNED A AND B**.
4. Choose another B to change the subrange, or **CLEAR PIN A** to end the comparison. Switching DAY or replacing the range resets the pin as before.

For illustration only, closing prices [110,105,120,90] have highest close 120, lowest close 90, a chronological peak-to-trough closing-price decline of 25%, and 1 up / 2 down observed transitions. This is **not** a live quote, intraday high/low or trading recommendation.

## VERIFY

The new `tests/finance/test_market_m31_pinned_interval.mjs` contains deterministic fictional immutable price bars and checks:
- A/B and B/A produce the identical chronological subrange statistics;
- exact high/low values/dates, 25% drawdown and correct observed session up/down/flat counts;
- earlier short section with 4.55% drawdown, rising-only, declining-only, flat and single-point windows;
- zero drawdown has no invented peak/trough event;
- copy-out behavior leaves frozen original price bars intact;
- invalid source, malformed/misordered dates and quotes, invalid A/B indices and oversized ranges fail closed;
- QML's M31 panel is tied to the existing trusted pinned comparison, with no new provider/API, process or file-write calls.

The test is added to the existing Market M10–M31 `test_market_price_range.mjs` regression chain and CI workflow, preserving the older M12 chart interaction contracts and M20–M21 quota tests.

## WATCH OUT FOR

The highest/lowest values refer **only to the daily closing-price basis in the loaded range**, not intraday extremes. A reported maximum drawdown is within this selected subwindow only, not a lifetime asset risk measure or performance forecast. Adjusted closes may later be revised following corporate actions. Picking B earlier than A does not reverse chronological path statistics.

Automated source/Node checks do not establish native Quickshell UI rendering. M30 is merged and the operator reported that it worked; the M31 panel must be visually verified separately after an approved merge/deployment. The operator's dirty local Quickshell state remains untouched.

## CHECKLIST

- [x] M30 merged and operator-reported native functional PASS recorded
- [x] Current Syntagma, Hospital and Market source ownership rechecked
- [x] M31 pure interval policy, read-only existing-screen panel and no-IO test
- [x] Existing full Market regression integration
- [ ] M31 exact-head GitHub CI and raw log verification
- [ ] Operator merge authorization
- [ ] Optional operator native Quickshell visual acceptance

## NEXT

Run exact-head workflows, fix any regression, preserve draft source and recovery pointers; do not merge or reload Quickshell without operator authorization. Test on already-loaded data rather than spending provider quota solely for M31.

**DRAFT // NO NEW PROVIDER REQUESTS // NO LOCAL HOST CHANGES // PRODUCTION HOLD.**
