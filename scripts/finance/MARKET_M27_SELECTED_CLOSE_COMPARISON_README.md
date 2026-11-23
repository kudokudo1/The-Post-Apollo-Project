# FinanceW Market M27 // Selected vs last loaded close

## IMPLEMENTATION

M26 shows read-only historical RANGE statistics. M27 adds a **selected session versus the last session actually present in the same loaded RANGE**. It reuses the existing chart click selection and the existing validated M26 range analysis policy. This is not a new data reader or historical provider request.

In `widgets/FinanceStockRangeAnalysisPolicy.js`, `compareSelectedToLast(snapshot,index)` first validates the existing read-only, single-price-basis, chronologically ordered EODHD range through `summarizeRange`, then checks a bounded integer selected index and computes:

- actual selected closing date and close;
- actual last loaded session date and close;
- signed dollar and percentage change from selected close to last loaded close;
- number of **observed session-to-session steps**, not calendar days.

The function returns primitive-value copies, never writable references to the returned provider bars. Null/invalid inputs return no comparison, not fabricated values. Positive, negative, flat, single-session and same-as-last choices are supported.

The existing `widgets/FinanceStockHistoryPane.qml` adds a small wrapping summary under the existing **SELECTED SESSION** label. It only appears while in RANGE, when the current issuer/date selection matches the loaded snapshot and a chart point is selected. It disappears when an old snapshot is invalidated, switching to DAY, or clearing a chart selection. The existing **OPEN IN DAY** action and first/last/range analysis stay intact.

No API calls, quote requests, persistence, credentials, tokens, timers, quota reservations, graph changes or cross-worker code paths are introduced.

## HOW TO USE

After approved merge/deployment:

Finance → MARKET → STOCKS → RANGE → choose issuer/date window → **LOAD RANGE** → click a point on the historical closing-price chart.

The selected close panel now also shows **SELECTED VS LAST LOADED CLOSE**, an absolute and percentage change, and the number of observed trading-session transitions. Click the selected point again (or empty chart space) to clear the selection; switch to DAY or load a new range to reset it.

There is **no new action required to get the comparison** and no additional provider request. If the last loaded close predates today's market activity, the screen correctly compares to that past close, not to a made-up current quote.

## VERIFY

The existing `tests/finance/test_market_m26_range_analysis.mjs` is extended to verify:

- fictional 110→90 is -$20 and -18.18%, four observed session steps;
- selected first, selected last, positive move, single-session and no price change;
- input references remain immutable; output is a copy;
- invalid index, mismatched first/last, unknown source and nonpositive values fail closed;
- QML uses only the current loaded-range snapshot, point index and pure policy, with no process, provider, filesystem or quota command.

The established `test_market_price_range.mjs` already loads that test; the existing Market M26 workflow now explicitly covers M26–M27, keeping new checks in the same regression pathway.

## WATCH OUT FOR

This is a **historical closing-price** comparison, not current-price tracking, intraday percent movement, gain on a real investment or a trading recommendation. A session step can cross weekends or exchange holidays. Price basis stays a single `CLOSE` or `ADJUSTED CLOSE` per range; adjusted closes may be revised after splits or dividends.

An automated source/Node PASS does not prove the new panel is correctly visible in the actual Fedora Quickshell until native acceptance. This feature is isolated from M20 SQLite security, Banking, Research, Strategies and Universal Connections.

## CHECKLIST

- [x] M25 and M26 already merged; current main and source preflight
- [x] Existing Market range analysis policy extended, without new data access
- [x] Selected-session UI comparison with normal point-clear behavior
- [x] Fictional deterministic numerical and invalid-input tests
- [ ] Exact-head M27 CI and raw job evidence
- [ ] Operator merge and native acceptance

## NEXT

Check all exact-head workflows on an M27 draft, retain operator-controlled merge authorization, and verify the selected comparison visually using an already-loaded range rather than making a provider call solely for testing.

**MARKET-ONLY DRAFT // NO REAL PROVIDER REQUESTS // NO LOCAL HOST CHANGES.**
