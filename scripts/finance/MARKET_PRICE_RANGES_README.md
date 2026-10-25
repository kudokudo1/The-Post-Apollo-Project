# Finance Market // Historical Ranges M10

M10 extends **Market → STOCKS** from a single comparison date to an
explicit inclusive **START DATE / END DATE** historical-price range.

## Operator use

After PR review/merge and a safe update of Quickshell:

1. Finance → Market → STOCKS.
2. Choose AAPL, MSFT or NVDA (same M9 issuer allowlist).
3. Choose START DATE and END DATE in the existing Finance date controls.
   The default is the past 30 calendar days through today, UTC.
4. Press **LOAD RANGE**. The interface shows actual trading sessions,
   first and last returned close, change between them, EODHD price basis,
   a range chart and DIRECT/HUB source/cache timestamps.
5. Choose another range and LOAD again. Changing either date or issuer
   invalidates the old response before it can appear under a new selection.

Both endpoints are inclusive. A weekend-only range can legitimately have
zero sessions; the UI displays that result without manufactured prices.
An out-of-order, future or greater-than-180-calendar-day range is rejected
**before** any provider request. Start/end may match (one calendar day).

The chart is historical daily data, not live quotes and not evidence
of an SEC filing reaction. Percent change is between the **first and
last actual returned trading closes**, *not* the literal start/end
calendar dates if either lacks a trading session.

## Same provider, shared local hub

M10 uses the documented EODHD EOD `from` and `to` parameters:
https://eodhd.com/financial-apis/api-for-historical-data-and-volumes

New files:
- `read_market_price_range.mjs`: one explicit bounded provider GET,
  no rerouting or scraping, one consistent adjusted-vs-raw close basis;
  180 calendar days, up to 132 returned trading sessions, 192KB cap,
  12-second deadline.
- `market_data_hub.mjs`: `getPriceRange` with its own cache key
  `range|eodhd|CIK|START|END`, but the **same** global TTL/LRU,
  at-most-two upstream request slots, and single-flight coalescing.
- `market_data_server.mjs`: read-only
  `/v1/price-range?cik=...&from=...&to=...`, on the same optional
  loopback-only service as the existing `/v1/price-context` endpoint.
- `read_market_price_range_optional_hub.mjs`: probes the local hub on
  the user action. If the listener is absent, calls EODHD directly.
  A running but failing/denying provider hub does **not** trigger a
  second direct upstream request.

Existing SEC Research date-context parsing, URLs, caches and UI are
intentionally unchanged. M9's earlier short-window date-context test
remains as a regression, while Market STOCKS now routes to the new range
protocol. POLYMARKET, OSIRIS, Budget, and FinanceW window geometry are
unmodified.

## Access and limitations

The issuer allowlist is **still limited to AAPL/MSFT/NVDA**. Apple
demonstration access was previously live-verified, but a longer window
may be subject to current provider access limits. Microsoft demo
eligibility remains uncertain; NVIDIA requires a suitable private
EODHD token. Empty/denied/partial responses produce explicit states,
not invented market data. The hub is local, manual-only and not a
multiuser or redistributable market data service. No new packages,
auto-start, schedule, service install, root permission or trading
functions.

Official provider documentation notes adjusted_close may be recomputed
on dividend/split events. The UI labels price basis, source and cached
timestamps; it does not pretend a cached adjusted price is immutable.

## Fake-only GitHub verification

    node tests/finance/test_market_price_range.mjs
    python3 tests/finance/test_finance_market_range_contracts.py

Older M7/M8/M9 SEC/Market/loopback tests remain in the existing CI. The
tests exercise provider denial, invalid dates, missing sessions, adjusted
price fallback, cache hits, issuer isolation, no direct retry while hub
fails, and 127.0.0.1 loopback integration with invented market prices.

## Live acceptance

Test a 30-day AAPL range with hub stopped (DIRECT), then with manually
started hub (HUB FETCHED/CACHED), one zero-day range, a weekend-only range,
a range longer than 180 days (no request), then compact/wide layouts.

Do not make broad company coverage, auto-start or service deployment part
of this PR. They require separate operator approval and provider licensing.
