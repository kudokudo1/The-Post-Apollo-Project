#!/usr/bin/env python3
"""Finance M9: a second, explicitly activated price consumer in Market."""
from pathlib import Path
r=Path(__file__).resolve().parents[2]
root=(r/"widgets/FinanceW.qml").read_text()
market=(r/"widgets/FinanceMarketPane.qml").read_text()
pane=(r/"widgets/FinanceStockHistoryPane.qml").read_text()
service=(r/"services/finance/FinanceStockHistoryReadService.qml").read_text()
existing=(r/"services/finance/FinanceSecPriceReadService.qml").read_text()
adapter=(r/"scripts/finance/read_sec_price_optional_hub.mjs").read_text()
hub=(r/"scripts/finance/market_data_hub.mjs").read_text()
server=(r/"scripts/finance/market_data_server.mjs").read_text()

assert root.count("PanelWindow {")==1
assert root.count("FinanceToolHost {")==1
assert root.count("FinanceServices.FinanceMarketReadService {")==1
assert root.count("FinanceServices.FinanceSecPriceReadService {")==1
assert root.count("FinanceServices.FinanceStockHistoryReadService {")==1
assert 'monitoring: root.menuOpen && root.selectedMainMode === "market"' in root
assert "stockFeed: stockHistoryService" in root
assert "marketFeed: marketService" in root
assert 'Quickshell.shellPath("scripts/finance/read_sec_price_optional_hub.mjs")' in existing
assert 'Quickshell.shellPath("scripts/finance/read_market_price_range_optional_hub.mjs")' in service
assert 'function refresh()' in service
assert 'function selectIssuer(cik)' in service
assert 'function selectStartDate(day)' in service
assert 'function selectEndDate(day)' in service
assert 'onMonitoringChanged:' in service and 'if (!monitoring) clear();' in service
assert 'if (reader.running)' in service
assert 'if (desiredKey !== inFlightKey || !monitoring)' in service
assert 'data.cik!==selectedCik' in service
assert 'data.from!==startDate || data.to!==endDate' in service
assert 'data.symbol!==symbols[selectedCik]' in service
assert 'data.delivery.via==="HUB"' in service
assert 'stockFeed.acceptOutput(text)' in service
assert '"provider-key-required"' in service
assert '"demo-not-authorized"' in service
assert '"hub-unhealthy"' in service
assert 'reader.exec([' in service and 'reader.exec([' not in pane
assert 'reader.exec([' not in market

assert 'label: "POLYMARKET"' in market
assert 'label: "OSIRIS"' in market
assert 'label: "STOCKS"' in market
assert 'pane.activeTool === "stocks"' in market
assert 'FinanceStockHistoryPane {' in market
assert 'stockFeed: pane.stockFeed' in market
assert 'FinanceOsirisPane {' in market

assert 'FinanceDateInput {' in pane
assert 'onValueEdited: function(value)' in pane
assert 'stocks.stockFeed.selectStartDate(value)' in pane
assert 'stocks.stockFeed.selectEndDate(value)' in pane
assert 'label: stocks.stockFeed && stocks.stockFeed.loading ? "READING"' in pane
assert 'stocks.stockFeed.refresh()' in pane
assert 'HISTORICAL RANGE // INCLUSIVE // MAX 180 DAYS' in pane
assert 'Select an issuer and START/END dates' in pane
assert 'SOURCE EODHD EOD' in pane
assert 'stocks.snapshot.delivery.cachedAt' in pane
assert 'stocks.snapshot.delivery.servedAt' in pane
assert 'Canvas {' in pane
assert 'onPriceBarsChanged: priceCanvas.requestPaint()' in pane
assert 'Math.min.apply(null,nums)' in pane
assert 'property var stockFeed: null' in market
assert 'property var stockFeed: null' in pane

assert 'createMarketDataHub' in hub
assert 'getPriceContext' in hub
assert 'const key = provider + "|" + cik + "|" + filingDate;' in hub
assert '"/v1/price-context?cik="' in adapter
assert 'url.pathname!=="/v1/price-context"' in server
for forbidden in ('financeWrite.submit(', 'financeFundingWrite.submit(',
                  'writeFile(', 'Qt.openUrlExternally','setInterval(',
                  'https://clob.polymarket.com/order'):
    assert forbidden not in service+pane, forbidden
assert 'Process {' not in pane
assert 'Process {' in service
assert "fetch(" not in pane
print("Finance M9 Market STOCKS second read-only consumer source contracts: PASS")
