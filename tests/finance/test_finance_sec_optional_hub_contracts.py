#!/usr/bin/env python3
"""M8: optional read-through source, never mandatory startup or surprise retry."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
bridge=(root/"scripts/finance/read_sec_price_optional_hub.mjs").read_text()
direct=(root/"scripts/finance/read_sec_price_context.mjs").read_text()
server=(root/"scripts/finance/market_data_server.mjs").read_text()
service=(root/"services/finance/FinanceSecPriceReadService.qml").read_text()
priceview=(root/"widgets/FinanceSecPriceContext.qml").read_text()
app=(root/"widgets/FinanceW.qml").read_text()
market=(root/"widgets/FinanceMarketPane.qml").read_text()
budget=(root/"widgets/FinanceBudgetGrid.qml").read_text()

assert 'import { loadPrices, SYMBOLS } from "./read_sec_price_context.mjs"' in bridge
assert 'connectionRefused(error)' in bridge
assert 'error?.cause?.code === "ECONNREFUSED"' in bridge
assert 'if (!connectionRefused(error))' in bridge
assert 'directReader(cik,filingDate)' in bridge
assert 'if (!res.ok) throw failure("hub-unhealthy")' in bridge
assert 'health.service !== "post-apollo-market-hub"' in bridge
assert 'health.readOnly !== true' in bridge
assert 'health.backgroundPolling !== false' in bridge
assert 'health.providerIds.includes("eodhd")' in bridge
assert '"/v1/health"' in bridge and '"/v1/price-context?cik="' in bridge
assert 'LOCAL_HOST = "127.0.0.1"' in bridge
assert '"X-Post-Apollo-Client":"financew"' in bridge
assert 'signal:AbortSignal.timeout(900)' in bridge
assert 'signal:AbortSignal.timeout(14000)' in bridge
assert '"hub-invalid-response"' in bridge
assert 'FINANCE_SEC_PRICE ' in bridge and 'FINANCE_SEC_PRICE_ERROR ' in bridge
assert '"DIRECT"' in bridge and '"HUB"' in bridge
assert 'POST_APOLLO_MARKET_HUB_PORT' in bridge
assert 'pathToFileURL(process.argv[1])' in bridge
assert 'writeFile(' not in bridge and 'setInterval(' not in bridge
assert 'exec(' not in bridge and 'spawn(' not in bridge

assert 'Quickshell.shellPath("scripts/finance/read_sec_price_optional_hub.mjs")' in service
assert '"hub-unhealthy"' in service
assert '"hub-invalid-response"' in service
assert 'data.delivery.via === "HUB"' in service
assert 'data.delivery.via === "DIRECT"' in service
assert 'LOCAL MARKET HUB ERROR' in service
assert 'FINANCE_SEC_PRICE ' in service
assert 'PRICE CONTEXT' in priceview
assert 'onLeftClicked: priceFeed.inspect(context.filing)' in priceview
assert 'context.marketSnapshot.delivery.via' in priceview
assert 'context.marketSnapshot.delivery.cachedAt' in priceview
assert 'context.marketSnapshot.delivery.servedAt' in priceview
assert app.count("PanelWindow {") == 1
assert app.count("FinanceToolHost {") == 1
assert 'FinanceServices.FinanceSecPriceReadService {' in app
assert 'server.listen(port,"127.0.0.1"' in server
assert 'loadPrices(cik, filingDate' in direct
assert 'POLYMARKET' in market
assert 'FINANCE_SEC_PRICE' not in budget
print("Finance M8 optional market hub bridge and provenance contracts: PASS")
