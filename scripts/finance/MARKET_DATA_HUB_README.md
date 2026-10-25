# FinanceW Market Data Hub // M7 Foundation

This is the first **standalone, opt-in** local market-data service for
Post-Apollo. It is not a production cloud service, not automatically started,
and not yet connected to the live Quickshell price view.

The service separates three concerns which the first SEC price pilot put
inside one process:

1. Provider adapter: the existing SEC context EODHD reader is reused.
2. Shared bounded read-through memory cache and single-flight requests.
3. Read-only loopback API for future FinanceW, Radar and other consumers.

## Current capabilities

The existing provider is **EODHD only**. The only approved issuer mapping
is the existing SEC pilot: Apple, Microsoft, NVIDIA. The service does not
pretend this makes all U.S. stocks available.

- Strict issuer CIK/date/provider selection, no caller-supplied provider
  URL or arbitrary symbol input.
- At most 64 cached results and 2 concurrent upstream requests.
- Same-key concurrent requests are coalesced into one provider request.
- 15-minute TTL for filings less than seven days old and 24-hour TTL for
  older filing windows. Source response remains marked as EODHD, while the
  hub adds FETCHED, SHARED or CACHED, cachedAt, servedAt, and expiresAt.
- Malformed, wrong-issuer and unauthorized provider responses are not cached.
- No persistent files, credentials in stdout, retry storms, crawler, scheduled
  polling, trading functionality, or UI startup work.
- Does **not** bypass EODHD keys/plan limits or grant redistribution rights.

## Offline tests (no provider requests)

From the repo root:

    node tests/finance/test_market_data_hub.mjs
    node tests/finance/test_market_data_server.mjs
    python3 tests/finance/test_market_data_hub_contracts.py

Tests inject fictional market prices and use ephemeral loopback sockets.
No real stock feed, private SEC email, or paid API token is read.

## Optional manual loopback smoke test (not necessary for this PR)

The server is deliberately **not auto-installed as a systemd unit**.
An operator can run it from Kitty after separately deciding to enable
this experimental service:

    node "$HOME/.config/quickshell/scripts/finance/market_data_server.mjs"

It binds to 127.0.0.1:48731 by default. Optional:
POST_APOLLO_MARKET_HUB_PORT=48732 uses another nonprivileged port. It
never binds to 0.0.0.0 or the local network.

Read-only health (requires local client header):

    curl -sS -H 'X-Post-Apollo-Client: financew' \
      'http://127.0.0.1:48731/v1/health'

One explicit historical context query:

    curl -sS -H 'X-Post-Apollo-Client: financew' \
      'http://127.0.0.1:48731/v1/price-context?cik=0000320193&date=2026-10-20'

This query may make one external EODHD request if no cache entry exists.
Only do this when ready to exercise provider access and fair usage.
Stop the server with Ctrl+C.

The header and loopback binding are **defense-in-depth, not full
authentication**. The M7 endpoint is a local pilot only. It should NOT be
reverse-proxied, exposed on the LAN, packaged for remote users, run as
root, or shipped as a public web service.

## Deployment and licensing blockers

A **Post-Apollo-managed multi-user service** would be a separate system
requiring hosting, account isolation, request budgets, monitoring, an
operator-managed licensed market-data contract and explicitly granted
data redistribution/display rights. None of those are claimed in M7.

EODHD currently offers personal-use free and paid plans and separately
advertises commercial/B2B licensing. Sharing a single personal-use
credential with all Post-Apollo users is **not** an acceptable shortcut.
See:
- https://eodhd.com/pricing
- https://eodhd.com/financial-apis/terms-conditions

Alternative Alpha Vantage provides a documented daily stock-price API,
but it requires a key, has usage limits and its licensed real-time
datasets require separate entitlements:
- https://www.alphavantage.co/documentation/
- https://www.alphavantage.co/support/api-key/

## Integration boundary / future work

The existing FinanceW SEC inspector still calls
\`scripts/finance/read_sec_price_context.mjs\` directly, unchanged.
This PR **does not route UI requests to the new server** and therefore
does not introduce a new mandatory process, failure point or startup lag.

A later approved step can add an **optional local hub adapter** with
health/read-only fallback, then link Radar and other price consumers.
This remains subject to live user testing and legal provider access.
