# FinanceW // SEC Dated Price Context M5

## Purpose

The already-verified SEC Evidence Desk now has an optional **PRICE CONTEXT**
button in its filing detail panel. It compares a selected issuer's price
history around the **SEC filing date**, not a forecast, trading signal,
or evidence that the filing caused a price movement.

The first feed is **EODHD end-of-day price history**. This is a distinct,
third-party source with licensing/access restrictions, not the SEC itself.

Official provider reference:
https://eodhd.com/financial-apis/api-for-historical-data-and-volumes

## First live test, no key or installation

EODHD's public **demo** access supports Apple `AAPL.US`, which matches our
already-tested Apple SEC CIK. After operator merge and local update:

1. Open Finance → Research → SEC EDGAR → APPLE.
2. Select a dated 8-K or Form 4.
3. Press **PRICE CONTEXT** in its detail panel.
4. Inspect source, basis, last daily close **strictly before** the filing
   date, and first daily close **strictly after** it, plus a short sparkline.
5. Use **REFRESH PRICE** for an explicit new attempt. No background polling.

The comparison skips holidays/weekends automatically because it uses
actual returned daily sessions. If the newer price is unavailable (e.g.
a filing on the latest trading day), the change is shown as N/A rather
than invented.

This first pilot does **not** incorporate an SEC acceptance timestamp or
intraday price changes. The orange chart guide denotes the filing date,
not the exact instant the market received the disclosure.

## Microsoft trial and NVIDIA gating

EODHD's own published material is **inconsistent about which symbols
its public `demo` credential supports**. Some provider pages include
`MSFT.US` and other current pages omit it. Apple is already locally
verified; Microsoft's **actual API authorization has not yet been verified**
on this desktop.

M6 makes one bounded demo request for Microsoft's selected SEC filing
when you press PRICE CONTEXT. If the provider permits it, genuine sourced
historical prices display. If it returns 401/403 or an explicit
Unauthenticated/Unauthorized response, the UI reports **MICROSOFT DEMO
ACCESS DENIED // PROVIDER KEY REQUIRED**. We never produce demonstration
or guessed stock prices as a fallback. No hidden retries and no requests
until the user presses the button.

NVIDIA (`NVDA.US`) is *not* listed as an eligible demo symbol by the
provider documentation examined; it still requires a valid private
EODHD token and makes **zero** requests when no token is configured.

If you separately choose a provider account/token, keep it private and
use the existing one-time host-only setup:

```zsh
mkdir -p "$HOME/.local/share/post-apollo/finance-market"
chmod 700 "$HOME/.local/share/post-apollo/finance-market"
read -rs "eod_token?EODHD token (private): "
printf '%s\n' "$eod_token" > "$HOME/.local/share/post-apollo/finance-market/eodhd-token.txt"
chmod 600 "$HOME/.local/share/post-apollo/finance-market/eodhd-token.txt"
unset eod_token
```

The private token remains outside GitHub and QML. Do not paste it into
screenshots, shell logs, or chats.

### Why not add a magic keyless provider?

Stooq added a CAPTCHA/API-key requirement for historical downloads in
2026. Yahoo's internal chart interface is not a documented redistributable
financial-data API. Neither is suitable for an unverified, silent
production fallback. A future Post-Apollo-managed licensed market-data
service could provide centralized credentials, caching and controlled
redistribution so ordinary users do not configure individual keys.

Provider references:
- https://eodhd.com/financial-apis/quick-start-with-our-financial-data-apis
- https://eodhd.com/lp/eodhd-chatgpt
- https://stooq.com/q/d/

## Scope / metrics

- Read-only, one opt-in bounded HTTPS request, 12-second timeout, 128 KB cap.
- Fixed CIK-to-symbol mapping: Apple `AAPL.US`, Microsoft `MSFT.US`,
  NVIDIA `NVDA.US`.
- Time window is ten calendar days before through fourteen after the filing
  date, limited to current UTC date if the filing is recent.
- Prior and next closes are **strictly** before/after filing date;
  a same-day close is visible only in the series and is not treated as the
  first post-filing session.
- Use consistent adjusted closes only if **all** daily rows provide them;
  otherwise use unadjusted closes across the whole returned series.
  Adjustments may change historically for dividends/splits.
- Computed percentage = (first following close / last preceding close - 1)
  × 100. This is a descriptive two-session span, not a causal event study.
- Missing provider data, rate limits, missing bars, invalid prices or keys
  fail visibly. No fallback to fake values or undocumented price endpoints.
- Nothing stored on disk by the viewer. Leaving/changing issuer or filing
  clears the previous market context. No separate background poller.

## Verify offline

```bash
node tests/finance/test_sec_price_context.mjs
python3 tests/finance/test_finance_sec_price_contracts.py
```

CI is fake-only. It does not guarantee your desktop can reach EODHD,
nor that the provider licenses this data for future public distribution.

## What comes next

M6: verify whether Microsoft's *actual* API endpoint permits demo
read access. If denied, retain the explicit setup message, do not bypass
provider access restrictions, and assess a licensed provider for wider
coverage. NVIDIA remains token-gated. Only then pursue benchmarks,
acceptance-time alignment or cross-source claims with explicit evidence.
