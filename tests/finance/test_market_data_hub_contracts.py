#!/usr/bin/env python3
"""Finance market-data hub M7 is explicit, loopback-only and independent."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
hub=(root/"scripts/finance/market_data_hub.mjs").read_text()
server=(root/"scripts/finance/market_data_server.mjs").read_text()
sec=(root/"scripts/finance/read_sec_price_context.mjs").read_text()
ui=(root/"widgets/FinanceW.qml").read_text()
service=(root/"services/finance/FinanceSecPriceReadService.qml").read_text()

assert "createMarketDataHub" in hub
assert "loadPrices(cik, filingDate)" in hub
assert 'provider !== "eodhd"' in hub
assert "Object.keys(adapters).some(key => key !== \"eodhd\")" in hub
assert "cache = new Map()" in hub and "inFlight = new Map()" in hub
assert "inFlight.has(key)" in hub and "maxConcurrent" in hub
assert "MAX_SLOTS = 64" in hub and "MAX_CONCURRENT = 2" in hub
assert "DEFAULT_TTL_RECENT_MS" in hub and "DEFAULT_TTL_HISTORICAL_MS" in hub
assert 'state:"CACHED"' in hub and 'state:"SHARED"' in hub and 'state:"FETCHED"' in hub
assert "source !== \"eodhd-eod\"" in hub
assert "Object.hasOwn(SYMBOLS, cik)" in hub
assert "cache.delete(cache.keys().next().value)" in hub
assert '"post-apollo-market-hub"' in hub
assert 'backgroundPolling: false' in hub

assert "createServer" in server
assert 'server.listen(port,"127.0.0.1"' in server
assert 'address !== "127.0.0.1"' in server
assert 'request.headers.origin' in server
assert 'request.headers["x-post-apollo-client"] !== CLIENT_HEADER' in server
assert '"Cache-Control": "no-store"' in server
assert "request.method !== \"GET\"" in server
assert 'url.pathname === "/v1/health"' in server
assert 'url.pathname !== "/v1/price-context"' in server
assert "request.url.length > MAX_REQUEST_PATH" in server
assert "unknown-provider" in server and "provider-busy" in server
assert "POST_APOLLO_MARKET_HUB_READY" in server
assert "process.argv[1] && import.meta.url" in server

# M7 remains an isolated, manual-only service. M8 introduces a safe optional
# client adapter; it never starts the hub or makes the running service mandatory.
assert 'Quickshell.shellPath("scripts/finance/read_sec_price_optional_hub.mjs")' in service
assert "market_data_server.mjs" not in service + ui
assert "market_data_hub.mjs" not in service + ui
assert 'loadPrices(cik, filingDate' in sec
assert 'FinanceServices.FinanceSecPriceReadService {' in ui
assert ui.count("PanelWindow {") == 1
assert ui.count("FinanceToolHost {") == 1
assert "financeWrite.submit(" not in hub + server
assert "writeFile(" not in hub + server
assert "setInterval(" not in hub + server
assert "setTimeout(" not in hub + server
assert "POST_APOLLO_MARKET_HUB_PORT" in server
print("Finance M7 standalone market-data hub architecture contracts: PASS")
