# FinanceW Market STOCKS // M9

## Implementation

M9 adds a third **STOCKS** mode beside Polymarket and OSIRIS inside
FinanceW's existing Market page. This is a second read-only consumer of
the **same M8 optional market hub / EODHD history adapter** already used
by SEC Research.

There is no new financial-data provider, polling service, public trading
endpoint, user account, automatic installer, or extra floating window.

## How to use

After review, merge and safe local Quickshell update:

1. Open **Finance → Market → STOCKS**.
2. Select one of the *currently allowed* SEC pilot issuers: AAPL, MSFT, NVDA.
3. Choose a **reference date** with FinanceW's existing Month/Day/Year control.
   The default is 14 calendar days before the current UTC day, so the
   symmetric price window will ordinarily include past sessions around it.
4. Press **LOAD HISTORY** to request historical **daily closing prices**.
5. See the actual sessions, source basis, delivery path, cached/served
   timestamps and a small in-window chart. Use REFRESH PRICE explicitly
   for another request. Changing issuer or date clears the displayed data.

The reference date is a user-chosen historical *comparison anchor*. It is
**not an SEC filing date**, an event timestamp, or a claim that the market
reacted to any specific news. The adapter's internal field is still
`filingDate` because M9 intentionally reuses the already-validated M8
protocol without extending it or creating competing infrastructure.

Both SEC Research and Market STOCKS use exactly the same cache key in M7
(**EODHD + issuer CIK + reference date**). When the same pair is requested
through both views while the optional hub runs, the second request is a
cache hit and doesn't fetch the provider again.

## Provider coverage

- Apple AAPL.US: the EODHD public demo path already verified locally.
- Microsoft MSFT.US: EODHD demo eligibility is uncertain; show actual
  prices only if authorized, otherwise clear provider-denied text.
- NVIDIA NVDA.US: requires optional private EODHD key, no fabricated
  fallback. This M9 PR does not change credential setup or entitlements.

Historical window is bounded to ten days before the anchor and fourteen
days after (not beyond the current day). Missing trading sessions are
not fabricated; prices are either all adjusted closes or all unadjusted
closes, depending on provider data completeness. The 2-session percent
comparison around an arbitrary date is descriptive, **not a trading signal**.

## Market page isolation

POLYMARKET retains its own Gamma API service, page, and state.
OSIRIS retains its own optional WebEngine pane. STOCKS is a sibling
component and never uses a Polymarket order API or a Budget writer.

Only STOCKS **LOAD HISTORY** or **REFRESH PRICE** invokes a price subprocess.
Selecting STOCKS, the issuer, or the date never requests a quote. No
automatic price polling or extra service starts on Market opening.

## Verification

Offline, fake-only:
- `node tests/finance/test_market_stocks_shared_hub.mjs`
  Exercises the real M7 HTTP loopback API using fictional adapter prices.
  Confirms SEC/Market cache reuse when issuer+date match and isolation when
  either dimension changes.
- `python3 tests/finance/test_finance_market_stocks_contracts.py`
  Verifies existing FinanceW single window/host, Market/OSIRIS isolation,
  reuse of the shared M8 adapter, existing date component, on-click gating,
  source/provenance information and no budget writes.

GitHub CI does **not** load a Qt/Wayland desktop or make live EODHD
requests. Operator acceptance should cover STOCKS in compact and wide
FinanceW, its calendar control, DIRECT mode with the local hub stopped,
and HUB FETCHED/CACHED with the hub running. No need to retest three
companies individually to validate the architecture.

## Future work

A separate, explicitly approved provider/contract upgrade can broaden
issuer coverage and add a genuine general-purpose daily history API
rather than reusing the filing-reference window. Hosting a market-data
hub for other users requires security and licensed distribution rights;
this PR does neither.
