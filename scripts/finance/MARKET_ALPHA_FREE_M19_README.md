# FinanceW Market M19 // Second free global price provider

## Implemented

**Finance → MARKET → STOCKS → GLOBAL SEARCH → PRICE OPTIONS →
ALPHA VANTAGE // FREE PRICE OPTIONS**.

M19 adds a separate, manually selected **Alpha Vantage** market-data lane,
distinct from the existing free EODHD account lane and no-account OpenFIGI
instrument identities. Its only external API functions are:

1. `SYMBOL_SEARCH` for the OpenFIGI result's literal local ticker. Display
   candidate symbol, name, market region, type, and currency from Alpha
   Vantage, but **never equate a returned ticker or region to the OpenFIGI
   FIGI**.
2. `TIME_SERIES_DAILY` with explicit exact candidate symbol and
   `outputsize=compact` after an operator presses **LOAD ALPHA VANTAGE DAILY
   CLOSES**. Only the most recent 100 provider sessions are requested.
   Display provider-returned raw daily closes in the exact selected date
   window (7/30/90/180 calendar-day presets), first/last, change %, source
   and currency from the preceding Alpha Vantage symbol search.

An Alpha Vantage free API key is necessary for these calls. The additional
separate owner-only file path is:

`~/.local/share/post-apollo/finance-market/alpha-vantage-token.txt`.

It uses the **existing** permission-checking key loader (regular file, no
symlinks or group/other access, checked token syntax); this PR does **not**
create, modify, store, migrate or reveal a key. Key setup is a separately
approved host operation.

### Current provider facts

- Alpha Vantage free tier: up to **25 requests/day**; get the key without
  buying a premium plan. A search plus daily history normally requires
  **two requests**.
- `TIME_SERIES_DAILY` returns **unadjusted** OHLCV, not dividends/splits
  adjusted prices. The free `compact` output has up to **100 most recent
  sessions**, so 180 calendar days often exceeds available depth. The pane
  flags when 100 rows reach backward less than the selected range.
- EODHD free key: **20 requests/day**, reset midnight GMT, one year of EOD
  price history; all other EODHD consumers share the same account allowance.
  Its daily prices can be **ADJUSTED CLOSE** or **CLOSE**, so there is no
  implicit comparison/fallback between these two providers.

Official documentation:
- https://www.alphavantage.co/documentation/
- https://www.alphavantage.co/support/
- https://eodhd.com/help/plans
- https://eodhd.com/help/limits

## Local quota management, bounded by honest observability

The Alpha Vantage and EODHD QML read services now each count **request
attempts started by their own running widget**. Each service refuses a
further request after its documented free-limit count (25 AV, 20 EODHD)
during that UTC day in that Quickshell session. Both counts persist through
the widget's in-app close/reopen and change of selected stock, and reset
when a manual request is attempted on a different UTC date.

**This is not the provider's actual remaining allowance.** Other processes,
machines, browser requests and the old six-company EODHD reader can spend
the same account's allowance without appearing in these counters. Quickshell
restart resets this in-memory estimate; no shared or durable provider quota
file is written. Provider-side HTTP 429 or Alpha Vantage's JSON
`Information`/`Note` limit response takes precedence. No automatic
fallback, retries, paid upgrade, account/identity linking or background
requests occur.

## Data/provenance guards

- Fixed HTTPS `www.alphavantage.co/query` endpoint, strict GET,
  no redirects, 12-second timeout, maximum 192k response body.
- Validated local ticker and Alpha Vantage symbol; reject path controls
  and unrelated candidates; no guessed vendor suffix.
- Validate selected OpenFIGI FIGI, candidate source symbol, currency from
  Alpha Search, timeframe, response schema and Meta Data symbol.
- Cap JSON daily series to 100; reject invalid, duplicate or non-positive
  raw provider close values. No synthetic market sessions, no currency
  conversion, no adjusted-price claims.
- Search, candidate selection and price load are three explicit acts;
  switching a stock clears the prior candidate and result. UI/source state
  drops stale responses and keeps the EODHD pane separate.
- New read-only scripts/services do not access bank account data, signing,
  protected spend records, shared Market Hub or any FinanceW money writer.

## Verify

`node tests/finance/test_alpha_vantage_free.mjs` uses a fictional Alpha
Vantage response to check Netherlands EUR vs USA USD same-ticker listings,
unrelated symbol/ETF rejection, free-key permission boundaries, API request
shape, provider 200 quota error JSON, 429/401/403, time-series compact
truncation, raw close basis, invalid date/range/schema and QML source
isolation. Import is wired to the existing Market tests.

CI does not verify live Alpha Vantage provider entitlement, actual free
account daily usage, native Quickshell input/focus/chart behavior or
investment identity. Review and explicit operator acceptance remain
required before merge/desktop sync.

## Future

Add an authorized durable, account-wide quota source only after cross-worker
ownership and crash/concurrency rules are agreed. Consider a third free
provider as an independent, explicit lane. Preserve provenance/price basis
before any cross-provider comparison.
