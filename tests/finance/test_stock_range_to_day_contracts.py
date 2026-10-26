#!/usr/bin/env python3
"""M13: explicit no-network session handoff, preserve separate DAY/RANGE data."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
service=(root/"services/finance/FinanceStockHistoryReadService.qml").read_text()
pane=(root/"widgets/FinanceStockHistoryPane.qml").read_text()
policy=(root/"widgets/FinanceStockModePolicy.js").read_text()
point=(root/"widgets/FinanceStockChartPointPolicy.js").read_text()
app=(root/"widgets/FinanceW.qml").read_text()
market=(root/"widgets/FinanceMarketPane.qml").read_text()
sec=(root/"services/finance/FinanceSecPriceReadService.qml").read_text()
adapter=(root/"scripts/finance/read_market_price_range_optional_hub.mjs").read_text()
provider=(root/"scripts/finance/read_market_price_range.mjs").read_text()

assert app.count("PanelWindow {") == 1
assert app.count("FinanceToolHost {") == 1
assert app.count("FinanceServices.FinanceStockHistoryReadService {") == 1
assert 'label: "POLYMARKET"' in market and 'label: "OSIRIS"' in market
assert 'label: "STOCKS"' in market

assert 'function openRangePointInDay(index, expectedDate)' in service
method=service.split("    function openRangePointInDay(index, expectedDate)",1)[1].split(
    "    function selectStartDate(day)",1)[0]
assert 'displayMode !== "range"' in method
assert '!monitoring || !ready || loading || reader.running' in method
assert 'StockModePolicy.daySnapshotFromRange(' in method
assert 'snapshot, index, selectedCik, activeWindow.from, activeWindow.to' in method
assert 'if (!day || day.from !== expectedDate) return false;' in method
assert 'dayDate = day.from;' in method
assert 'displayMode = "day";' in method
assert 'snapshot = day;' in method
assert 'state = "ready";' in method
assert 'NO NEW MARKET REQUEST' in method
# Handoff does not clear the original range start/end selectors or start work.
for forbidden in ('reader.exec(', 'refresh(', 'selectStartDate(', 'selectEndDate(',
                  'startDate =', 'endDate =', 'clear();', 'Process {',
                  'financeWrite.submit(', 'fetch('):
    assert forbidden not in method, forbidden

assert 'bar.date>=activeWindow.from' in service
assert 'bar.date<=activeWindow.to' in service
assert 'bar.date>=startDate' not in service
assert 'bar.date<=endDate' not in service
assert 'function selectMode(nextMode)' in service
assert 'if (displayMode !== nextMode)' in service
assert 'function selectDayDate(day)' in service
assert 'reader.exec([' in service
assert 'Quickshell.shellPath("scripts/finance/read_market_price_range_optional_hub.mjs")' in service

assert 'label: "OPEN IN DAY"' in pane
assert 'id: openSelectedInDay' in pane
assert 'visible: !stocks.dayMode && stocks.inspectedPoint !== null' in pane
assert 'stocks.stockFeed.openRangePointInDay(' in pane
assert 'stocks.selectedPointIndex, stocks.inspectedPoint.date' in pane
assert 'stocks.stockFeed.ready && !stocks.stockFeed.loading' in pane
assert 'DAY SOURCE // PREVIOUSLY LOADED RANGE // NO NEW REQUEST' in pane
assert 'stocks.snapshot.derivedFromRange' in pane
assert 'stocks.stockFeed.selectStartDate(value)' in pane
assert 'stocks.stockFeed.selectEndDate(value)' in pane
assert 'stocks.stockFeed.selectDayDate(value)' in pane
assert pane.count("FinanceDateInput {")==3
assert 'label: "DAY"' in pane and 'label: "RANGE"' in pane
assert 'function inspectChartPoint(x, y)' in pane
assert 'ChartPointPolicy.selectedBar(priceBars, selectedPointIndex)' in pane
assert 'selectedPointIndex = -1;' in pane
assert 'onDayModeChanged' in pane
assert 'visible: !stocks.dayMode && stocks.priceBars.length >= 2' in pane

assert 'function daySnapshotFromRange(snapshot, index, cik, rangeFrom, rangeTo)' in policy
assert 'snapshot.from !== rangeFrom || snapshot.to !== rangeTo' in policy
assert 'snapshot.cik !== cik || snapshot.symbol !== symbols[cik]' in policy
assert 'bar.date < rangeFrom || bar.date > rangeTo' in policy
assert 'const exact = {date:bar.date, price:bar.price}' in policy
assert 'from:bar.date, to:bar.date' in policy
assert 'changePct:null, bars:[exact]' in policy
assert 'derivedFromRange:true' in policy
assert 'originRange:{from:rangeFrom,to:rangeTo}' in policy
assert 'readOnly:true' in policy
assert 'source:"eodhd-eod"' in policy
assert 'function selectedBar(bars, index)' in point

assert 'FINANCE_SEC_PRICE ' in sec
assert 'getPriceRange' not in pane+policy
assert 'MAX_RANGE_DAYS = 180' in provider
assert 'FINANCE_STOCK_RANGE ' in adapter
for forbidden in ('reader.exec(', 'Process {', 'fetch(', 'writeFile(',
                  'financeWrite.submit(', 'Qt.openUrlExternally'):
    assert forbidden not in pane+policy, forbidden
print("Finance M13 explicit OPEN IN DAY, issuer/date integrity and no-network contracts: PASS")
