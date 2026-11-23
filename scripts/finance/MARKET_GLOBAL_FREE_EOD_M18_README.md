# FinanceW Market M18 // Free-tier worldwide daily price bridge

## IMPLEMENTATION

This is a separate, explicit two-stage **EODHD free-account-key** extension
to the M17 OpenFIGI worldwide STOCKS identity search.

The operator first uses **Finance → MARKET → STOCKS → GLOBAL SEARCH**,
searches a company/ticker without any key, and selects **PRICE OPTIONS** next
to one of the returned OpenFIGI identity records.

The price panel shows the original **OpenFIGI FIGI, local ticker, exchange
code and name**, but it does **NOT claim an automatic match** between this
identity and a market-data-provider symbol. Pressing **FIND EODHD PRICE
LISTINGS** uses the already-supported owner-only local EODHD token to query
the vendor's **Search API** for the selected exact local ticker. It returns
up to 25 vendor listings filtered to the same ticker and stock-like type.
Each is labeled with EODHD's own **Code.Exchange**, name, country, currency
and ISIN where provided. The operator must inspect name, country, exchange
and instrument type, then explicitly choose an EODHD listing.

Only **LOAD SELECTED DAILY HISTORY** requests price data, with an exact
selected provider symbol/currency and an inclusive 7/30/90/180-calendar-day
window. The resulting chart shows EODHD daily-close sessions, consistent
adjusted/raw price basis, provider timestamps, and currency metadata from
the *EODHD search response*. The EOD price endpoint itself does not
separately certify that currency or match the OpenFIGI FIGI.

## FREE-FIRST / ACCOUNT OPTIONS

- **No account/key needed** for OpenFIGI M17 worldwide identity search.
- **Free EODHD account key needed** for the EODHD Search API. EODHD says
  registration is free with no credit card. There is **no paid-plan
  subscription requirement in this implementation**.
- Official free-tier documentation: **20 API calls/day, 1 year of EOD
  history**. A search plus a price-range read normally uses **2 calls**.
  Allowances are shared with other EODHD tools; no account-wide quota
  counter has been implemented or claimed here.
- The same protected key path the preexisting price reader uses is
  read-only: `~/.local/share/post-apollo/finance-market/eodhd-token.txt`.
  This milestone creates no credentials, key files, account or account-link
  service.
- No unauthorized paid upgrade/fallback is attempted. HTTP 429 is shown
  as a quota/rate limit. HTTP 401, 402 and 403 are surfaced as
  key/entitlement issues. Actual key entitlement and country/instrument
  coverage can vary and have **not** been probed live in this draft.

Official sources:
- https://eodhd.com/help/plans
- https://eodhd.com/financial-apis/search-api-for-stocks-etfs-mutual-funds
- https://eodhd.com/financial-apis/quick-start-with-our-financial-data-apis
- https://www.openfigi.com/api/documentation

## SOURCE SAFETY

- Fixed HTTPS EODHD hostname and two bounded API routes only:
  `/api/search/TICKER` and `/api/eod/CODE.EXCHANGE`.
- Token loaded using the existing owner-only file/permission checks;
  no token is printed to Quickshell, placed in argv, or saved elsewhere.
- Search and price fetch are each manually triggered; no timers,
  auto-crawlers, polling, background calls or writing.
- Search input and source symbol reject path separators or invalid
  exchange formats. Provider data and result size are bounded before
  consumption. Daily bars are validated and sorted with no synthetic
  weekends/holiday points or FX conversion.
- QML checks the original OpenFIGI FIGI, exact requested ticker and later
  EODHD selected symbol, currency, date range, source and price-row schema
  before rendering results.
- New data does not flow into the original six-company EODHD Market Hub,
  SEC filing-date price context, Budget, Banking, Strategies or signed
  Identity/Connections service. Existing issuer and provider allowlists are
  untouched.

## VERIFY

`node tests/finance/test_global_free_price_bridge.mjs` verifies fictional
global same-ticker/different-exchange results, requested free key behavior,
HTTP limits/refusals, exact source symbol, currency propagation,
invalid/malformed records, bound price windows, zero-session ranges,
adjusted close basis, no silent provider requests and Quickshell source
integration. It is imported from `test_market_price_range.mjs`, already
run by the FinanceW workflow along with M9–M17 regressions.

Native Quickshell mouse/keyboard/compact and actual free-account coverage
remain pending separate operator acceptance. A review is required before
enabling any automatic FIGI→provider mapping, account token UI or quota
persistence.

## RECOVERY / NEXT

One new read-only data script, one new Quickshell reader, one new price
viewer and a narrowly scoped addition to the existing global search
pane plus offline tests. No desktop state has been modified.

Next: independent security review; then native acceptance after approved
merge/local update. Later enhancements can add provider discovery/fallback
and per-provider quota tracking under separately authorized ownership,
without requiring users to pay for Market research.
