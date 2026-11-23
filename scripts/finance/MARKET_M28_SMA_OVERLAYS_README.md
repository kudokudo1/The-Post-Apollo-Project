# FinanceW Market M28 // Optional historical SMA 5/20 overlays

## IMPLEMENTATION

M28 introduces an optional chart overlay for trailing **5-session and 20-session simple moving averages (SMA)** calculated entirely from the `bars` already loaded in the existing STOCKS RANGE screen.

- The existing pure, read-only `FinanceStockRangeAnalysisPolicy.js` gains `movingAverageSeries(snapshot)`. It invokes the M26 trusted EODHD RANGE validator and uses a bounded sliding sum on up to 132 actually observed closing-price sessions. No calendar fill, quotes, forecasts, persistence or network.
- The trailing 5-session line begins at the **fifth** loaded session, and the 20-session line begins at the **twentieth**. Earlier positions have no values; there is no look-ahead averaging.
- The existing `FinanceStockHistoryPane.qml` gains a **SHOW 5/20 SMA** / **HIDE 5/20 SMA** toggle for valid loaded ranges of at least five sessions. Default is OFF. When ON, orange SMA5 and lilac SMA20 render over the existing cyan closing-price plot using the **same pixel axes and time positions**.
- Beneath the chart, latest loaded-session averages appear with the single `CLOSE` or `ADJUSTED CLOSE` basis. If fewer than 20 sessions are loaded, SMA20 is explicitly **N/A // NEED 20 LOADED SESSIONS**, not zero or extrapolated. Invalid or fewer than five sessions hide the toggle/summary. DAY mode suppresses the overlay. Repainting happens from local in-memory values only.
- A permanent label states that these are loaded historical sessions, **not a live quote or trade signal**. The existing cyan price plot, selected-point marker, M27 selected-to-last analysis, range statistics, date controls and Quickshell service remain untouched apart from presentation overlays.

No provider APIs, quota reservations, file/database operations, credentials, external windows, new QML services or transaction permissions are introduced.

## HOW TO USE

After separately authorized merge and native source deployment:

Finance → MARKET → STOCKS → RANGE → choose an issuer/dates or a preset → LOAD RANGE → **SHOW 5/20 SMA**.

Use the same toggle to hide the lines. The orange line is the average of the last five **observed trading-session closes** at each plotted date; lilac is the last twenty. No new provider request is made by toggling or resizing.

## VERIFY

`tests/finance/test_market_m28_moving_averages.mjs` uses fictional prices for:

- exact rolling 5-session averages of 105 then 103 in a six-session range;
- 20 sessions starting at index 19 with 10.50 SMA20 and 18.00 SMA5;
- 25 flat sessions staying at 7.00 for both averages;
- fewer than five/twenty observations showing unavailable rather than fabricated values;
- frozen source input left unchanged, output copies, rejection of malformed/untrusted/out-of-order source and invalid prices;
- production QML includes an explicit local-only toggle, legend, clear incomplete-window treatment and no provider/process/write operation in overlay code.

The test is imported by existing `tests/finance/test_market_price_range.mjs`, with the current M26–M28 workflow running both the direct and full mocked Market range chain. No real provider HTTP calls are made.

## WATCH OUT FOR

These are **trailing session averages**, not 5/20 calendar-day averages, intraday averages, future trend projections, returns on an investment, or buy/sell recommendations. A newly loaded 7D calendar range can have fewer than five actual market sessions, so the overlay will correctly be unavailable. The analysis only knows about the range the user actually requested; it will not fetch prior sessions to fill a longer indicator.

An automated source/Node PASS is not a live Fedora Quickshell visual acceptance. Subsequent native verification should use already-loaded data or a disposable test fixture rather than spending provider quota solely to test M28. The separate M20 security boundary remains an independent review topic; this ordinary Market feature does not require Connections involvement.

## CHECKLIST

- [x] M27 merged and operator-reported native success
- [x] Current Market source, roles and Syntagma preflight
- [x] Local-only trailing SMA 5/20 policy, toggle and two chart lines
- [x] Fictional edge cases, incomplete-window and no-IO regression tests
- [ ] M28 exact-head CI and raw logs
- [ ] Operator merge authorization and optional native visual check

## NEXT

Verify the exact-head source and regression CI. Keep this Market-only feature draft until operator merge approval, and preserve the existing dirty live Quickshell tree.

**DRAFT // NO REAL PROVIDER CALLS // NO LIVE HOST MUTATIONS // PRODUCTION HOLD.**
