#!/usr/bin/env python3
"""Finance M10: bounded explicit range and existing SEC date context separated."""
from pathlib import Path
r=Path(__file__).resolve().parents[2]
app=(r/"widgets/FinanceW.qml").read_text()
market=(r/"widgets/FinanceMarketPane.qml").read_text()
pane=(r/"widgets/FinanceStockHistoryPane.qml").read_text()
stock=(r/"services/finance/FinanceStockHistoryReadService.qml").read_text()
sec=(r/"services/finance/FinanceSecPriceReadService.qml").read_text()
reader=(r/"scripts/finance/read_market_price_range.mjs").read_text()
adapter=(r/"scripts/finance/read_market_price_range_optional_hub.mjs").read_text()
hub=(r/"scripts/finance/market_data_hub.mjs").read_text()
server=(r/"scripts/finance/market_data_server.mjs").read_text()

assert app.count("PanelWindow {")==1
assert app.count("FinanceToolHost {")==1
assert app.count("FinanceServices.FinanceStockHistoryReadService {")==1
assert 'FinanceServices.FinanceSecPriceReadService {' in app
assert 'label: "POLYMARKET"' in market and 'label: "OSIRIS"' in market
assert 'label: "STOCKS"' in market
assert 'FinanceStockHistoryPane {' in market
assert pane.count("FinanceDateInput {")==3
assert 'START DATE' in pane and 'END DATE' in pane
assert 'dateControls.sideBySide' in pane
assert 'HISTORICAL RANGE // INCLUSIVE // MAX 180 DAYS' in pane
assert 'stocks.stockFeed.selectStartDate(value)' in pane
assert 'stocks.stockFeed.selectEndDate(value)' in pane
assert 'stocks.stockFeed.validSelection' in pane
assert 'stocks.stockFeed.refresh()' in pane
assert 'stocks.snapshot.first.price.toFixed(2)' in pane
assert 'stocks.snapshot.last.price.toFixed(2)' in pane
assert 'stocks.snapshot.delivery.cachedAt' in pane
assert 'Canvas {' in pane and 'priceCanvas.requestPaint()' in pane
assert 'REFERENCE DATE POSITION' not in pane

assert 'property string startDate: dateOffset(-30)' in stock
assert 'property string endDate: dateOffset(0)' in stock
assert 'StockModePolicy.selectWindow(' in stock
assert 'b - a <= 180' in (r/"widgets/FinanceStockModePolicy.js").read_text()
assert 'selectStartDate(day)' in stock and 'selectEndDate(day)' in stock
assert 'if (!monitoring) clear();' in stock
assert 'if (reader.running)' in stock
assert 'if (desiredKey !== inFlightKey || !monitoring)' in stock
assert 'data.from!==activeWindow.from || data.to!==activeWindow.to' in stock
assert 'data.cik!==selectedCik' in stock
assert 'data.symbol!==symbols[selectedCik]' in stock
assert 'Quickshell.shellPath("scripts/finance/read_market_price_range_optional_hub.mjs")' in stock
assert 'FINANCE_STOCK_RANGE_ERROR ' in stock
assert 'FINANCE_STOCK_RANGE ' in stock
assert 'reader.exec([' in stock and 'reader.exec([' not in pane

assert 'Quickshell.shellPath("scripts/finance/read_sec_price_optional_hub.mjs")' in sec
assert 'FINANCE_SEC_PRICE ' in sec # SEC protocol unchanged
assert 'MAX_RANGE_DAYS = 180' in reader
assert 'MAX_RANGE_BARS = 132' in reader
assert 'from,to,period:"d",order:"a"' in reader
assert 'loadOptionalToken' in reader
assert 'AbortSignal.timeout(12000)' in reader
assert 'msftTrial' in reader
assert '"provider-key-required"' in reader
assert 'sort((a,b)=>a.date.localeCompare(b.date))' in reader
assert '"ADJUSTED CLOSE":"CLOSE"' in reader
assert 'normalized' not in pane.lower() or 'SOURCE EODHD EOD' in pane

assert 'readOptionalRange' in adapter
assert 'if(!refused(healthError))' in adapter
assert 'health=await healthProbe(); healthError=null;' in adapter
assert 'directReader(cik,from,to)' in adapter
assert 'hub-unhealthy' in adapter
assert 'FINANCE_STOCK_RANGE ' in adapter
assert '"/v1/price-range?cik="' in adapter
assert 'getPriceRange' in hub
assert '"range|"+provider+"|"+cik+"|"+from+"|"+to' in hub
assert 'maxConcurrent' in hub and 'cache = new Map()' in hub
assert 'const rangeMode=url.pathname==="/v1/price-range"' in server
assert 'hub.getPriceRange' in server
assert '"invalid-range"' in server
assert 'request.method !== "GET"' in server
assert 'server.listen(port,"127.0.0.1"' in server
assert 'setInterval(' not in reader+adapter+stock
for forbidden in ('writeFile(', 'financeWrite.submit(', 'financeFundingWrite.submit(',
                  'https://clob.polymarket.com/order', 'Qt.openUrlExternally'):
    assert forbidden not in pane+stock+adapter+reader, forbidden
print("Finance M10 bounded stock-price range and original SEC isolation contracts: PASS")
