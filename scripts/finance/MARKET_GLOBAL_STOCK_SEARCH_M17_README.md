# FinanceW Market M17 // Free Global Stock Discovery

## Current deliverable

Market → STOCKS → GLOBAL SEARCH opens a manually activated, read-only
**OpenFIGI v3** identity search. Search by a company name or ticker. The
response contains listed equity instrument identifiers (FIGI, local ticker,
exchange code, name, equity type). A user can request the **NEXT PAGE**
explicitly. This is not a market price source. Opening an item does not load
a quote, place an order, switch instruments in the EOD chart, or link a
provider to a personal account.

No OpenFIGI login or key is required. OpenFIGI's published no-key Search
limit is **5 requests/minute per IP**, with up to 100 results per page.
A limit refusal is displayed, not retried automatically. Terms:
https://www.openfigi.com/api/documentation

## Boundaries

- All network reads use the one fixed HTTPS OpenFIGI v3 endpoint. No scraping,
  redirects, background polling, write actions, cache files, or auto-refresh.
- Search terms are strict 2–80 chars/12 terms, control chars rejected.
  Pagination cursors are bounded; subprocess arguments are passed as argv,
  never through a shell.
- Input and JSON response sizes, result counts, equity types, names,
  exchange codes and FIGIs are checked. Derivative and fund results are
  filtered out of the STOCKS list. Missing identity fields are omitted.
- Changing or hiding the search view invalidates the in-memory snapshot;
  old subprocess responses are ignored. No token and no permissions/identity
  changes are involved.
- The existing 6-stock EOD chart reader, its separate EODHD token policy,
  DAY/RANGE chart controls and SEC Research allowlist remain intact.
- A ticker is NOT unique worldwide. Only the original FIGI and exchange
  identity are displayed. Currency and price history are deliberately
  **not** claimed, inferred or converted by this milestone.
- Provider coverage and instrument-type classification can vary; this
  first slice is not a complete S&P 500 membership list.

## Verification

`node tests/finance/test_openfigi_stock_search.mjs` uses only fictional
OpenFIGI responses. It covers search validation, pagination, issuer
identities, type filtering, exact endpoint/method/headers, no-key behavior,
rate-limit error, bounded responses and QML source isolation.

The existing `node tests/finance/test_market_price_range.mjs` imports the
M17 tests and runs in the established FinanceW contract workflow.
No production-provider or native desktop assertions are implied by CI.

## Next milestones

1. Review the exact-head CI and test native Quickshell keyboard/pointer and
   compact/wide results layout after operator-approved deployment.
2. Add a provider adapter registry for historical prices with **free-only**
   capability and quota disclosures, using exact FIGI/exchange mappings;
   never silently infer EODHD symbols from OpenFIGI tickers.
3. Add optional free-account keys and real historical price entitlement
   probes only by separately approved source/credential scope.
4. Add explicit watchlists, country/exchange filters and exchange/market
   calendars before comparing international stocks.
