# FinanceW M8 // Optional Market Hub Routing

The existing SEC **PRICE CONTEXT** button now uses a small
`read_sec_price_optional_hub.mjs` adapter. It does not start a process,
install software, make the Market Data Hub mandatory, or change provider
licensing. The original EODHD reader remains available on the same host.

## How it behaves

| Market Hub state | What FinanceW does |
| --- | --- |
| Not listening at 127.0.0.1:48731 | Automatically uses the existing direct EODHD reader |
| Healthy and running | Uses the hub; shares its cache and concurrent request limits |
| Healthy, provider returns key/denial error | Shows the provider error; **no automatic second request** |
| Listener running but unhealthy, timed out, or invalid data | Shows LOCAL MARKET HUB ERROR; **no direct retry** |
| App exits or issuer/file changes | Clears current in-memory price snapshot as before |

**Why an error instead of automatic fallback when the hub is unhealthy?**
The hub may have already issued an external request. A direct retry could
silently double traffic, bypass hub throttling, or attribute the response
to the wrong source. Only the explicit local TCP refusal (ECONNREFUSED)
proves the service is absent for this purpose.

The SEC filing list, Form 4/8-K inspector and evidence comparison are
unchanged. PRICE CONTEXT remains a **manual** request.

## Using it

1. Merge/review M8 and safely update Quickshell when appropriate.
2. Open Finance → Research → SEC EDGAR → APPLE → select filing →
   **PRICE CONTEXT**.
3. Without an active hub, see `PATH DIRECT // DIRECT` and the same
   original historical prices and chart.
4. Optionally, in a **separate** Kitty session start the already-reviewed
   hub (no systemd service, no automatic startup):

       node "$HOME/.config/quickshell/scripts/finance/market_data_server.mjs"

5. Press REFRESH PRICE in FinanceW. You should see
   `PATH HUB // FETCHED` initially, then `PATH HUB // CACHED` on
   another request within the TTL. Price dates and source remain the same.
6. Stop the manually started hub with Ctrl+C. PRICE CONTEXT should use
   the direct reader again on the next click.

There is no reason to restart Quickshell to switch between DIRECT and
HUB while the widget is already loaded.

Both server and adapter accept
`POST_APOLLO_MARKET_HUB_PORT` with an explicitly validated port in the
nonprivileged range. The host address is **always 127.0.0.1**. This local
header-and-port restriction is **not** internet-grade authentication.

## Provenance

The source remains **EODHD** (as in M5). Added delivery metadata is kept
separate from source data:
- DIRECT: `via=DIRECT, state=DIRECT, servedAt`.
- HUB: `via=HUB, state=FETCHED/CACHED/SHARED, cachedAt,
  expiresAt, servedAt, ageSeconds`.

The widget labels both the delivery path and cache time. Dates and prices
are independently validated against the currently selected SEC filing's
issuer/date; stale or malformed hub data is rejected.

## Local automated verification (fictional prices)

    node tests/finance/test_sec_optional_hub.mjs
    python3 tests/finance/test_finance_sec_optional_hub_contracts.py

The Node test runs an ephemeral **real local M7 HTTP server with fake
price fixtures** to verify hub fetch/cache, missing listener fallback,
bad health, provider errors, and reject wrong-issuer data. It makes no
requests to EODHD and does not read provider credentials.

## Limits and next steps

The cache exists **only when the manually started hub process is running**.
M8 does not provide a cloud backend, stock coverage beyond the existing
approved EODHD symbols, automatically provision any EODHD/SEC key,
satisfy provider redistribution licensing or enable trading.

Before adding other widgets as consumers, the operator should first
verify DIRECT, HUB FETCHED, HUB CACHED, stopping the hub, and the
compact/wide layouts. Do not deploy this local endpoint to the internet
or turn on autostart without a separate authorization and operational plan.
