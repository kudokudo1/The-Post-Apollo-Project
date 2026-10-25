#!/usr/bin/env python3
"""M11 DAY and RANGE have separate dates, identical bounded read-only pipeline."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
service=(root/"services/finance/FinanceStockHistoryReadService.qml").read_text()
pane=(root/"widgets/FinanceStockHistoryPane.qml").read_text()
policy=(root/"widgets/FinanceStockModePolicy.js").read_text()
adapter=(root/"scripts/finance/read_market_price_range_optional_hub.mjs").read_text()
provider=(root/"scripts/finance/read_market_price_range.mjs").read_text()
sec=(root/"services/finance/FinanceSecPriceReadService.qml").read_text()
app=(root/"widgets/FinanceW.qml").read_text()
market=(root/"widgets/FinanceMarketPane.qml").read_text()

assert app.count("PanelWindow {")==1
assert app.count("FinanceToolHost {")==1
assert 'FinanceServices.FinanceStockHistoryReadService {' in app
assert 'FinanceServices.FinanceSecPriceReadService {' in app
assert 'label: "POLYMARKET"' in market and 'label: "OSIRIS"' in market
assert 'label: "STOCKS"' in market

assert 'property string displayMode: "range"' in service
assert 'property string dayDate: dateOffset(-1)' in service
assert 'property string startDate: dateOffset(-30)' in service
assert 'property string endDate: dateOffset(0)' in service
assert 'import "../../widgets/FinanceStockModePolicy.js" as StockModePolicy' in service
assert 'StockModePolicy.selectWindow(' in service
assert 'displayMode, dayDate, startDate, endDate, dateOffset(0)' in service
assert 'function selectMode(nextMode)' in service
assert 'function selectDayDate(day)' in service
assert 'function selectStartDate(day)' in service
assert 'function selectEndDate(day)' in service
assert 'displayMode = nextMode;' in service
assert 'const from=activeWindow.from, to=activeWindow.to;' in service
assert 'const key=displayMode+"/"+selectedCik+"/"+from+"/"+to;' in service
assert 'desiredKey!==displayMode+"/"+selectedCik+"/"' in service
assert 'data.from!==activeWindow.from || data.to!==activeWindow.to' in service
assert 'if (desiredKey !== inFlightKey || !monitoring) return;' in service
assert 'if (reader.running)' in service
assert 'onMonitoringChanged:' in service and 'if (!monitoring) clear();' in service
assert '(displayMode==="day" && data.bars.length>1)' in service
assert 'NO TRADING SESSION FOR THIS CALENDAR DAY' in service
assert 'Quickshell.shellPath("scripts/finance/read_market_price_range_optional_hub.mjs")' in service
assert 'reader.exec([' in service and 'reader.exec([' not in pane
assert 'FINANCE_STOCK_RANGE ' in service

assert 'import "FinanceStockModePolicy.js" as StockModePolicy' in pane
assert 'label: "DAY"' in pane and 'label: "RANGE"' in pane
assert 'stocks.stockFeed.selectMode("day")' in pane
assert 'stocks.stockFeed.selectMode("range")' in pane
assert 'stocks.dayMode ? 66 : (sideBySide ? 66 : 136)' in pane
assert pane.count("FinanceDateInput {")==3
assert 'visible: stocks.dayMode' in pane
assert 'visible: !stocks.dayMode' in pane
assert 'stocks.stockFeed.selectDayDate(value)' in pane
assert 'stocks.stockFeed.selectStartDate(value)' in pane
assert 'stocks.stockFeed.selectEndDate(value)' in pane
assert 'StockModePolicy.daySession(snapshot, stockFeed.dayDate)' in pane
assert 'REFRESH DAY' in pane and 'LOAD DAY' in pane
assert 'REFRESH RANGE' in pane and 'LOAD RANGE' in pane
assert 'NO TRADING SESSION' in pane
assert 'stocks.dayResult.close.toFixed(2)' in pane
assert 'visible: !stocks.dayMode && stocks.priceBars.length >= 2' in pane
assert 'stocks.snapshot.first.price.toFixed(2)' in pane
assert 'stocks.snapshot.last.price.toFixed(2)' in pane
assert 'SOURCE EODHD EOD' in pane
assert 'stocks.snapshot.delivery.cachedAt' in pane
assert 'priceCanvas.requestPaint()' in pane

assert 'function selectWindow(mode, dayDate, startDate, endDate, today)' in policy
assert 'return day !== null && day >= minimum && day <= upper' in policy
assert '{from:dayDate, to:dayDate, kind:"day"}' in policy
assert 'b - a <= 180' in policy
assert 'function daySession(snapshot, requestedDay)' in policy
assert 'state:"no-session"' in policy
assert 'snapshot.bars.length > 1' in policy

assert 'FINANCE_STOCK_RANGE ' in adapter
assert 'directReader(cik,from,to)' in adapter
assert '"provider-key-required"' in provider
assert 'MAX_RANGE_DAYS = 180' in provider
assert 'FINANCE_SEC_PRICE ' in sec
assert 'read_sec_price_optional_hub.mjs' in sec
for forbidden in ('Qt.openUrlExternally','writeFile(', 'financeWrite.submit(',
                  'financeFundingWrite.submit(', 'setInterval('):
    assert forbidden not in pane+policy+service, forbidden
print("Finance M11 separate DAY/RANGE UI and stale-data isolation contracts: PASS")
