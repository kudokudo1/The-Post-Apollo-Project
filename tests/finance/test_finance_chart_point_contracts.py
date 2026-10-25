#!/usr/bin/env python3
"""M12: native RANGE Canvas selects existing returned EOD points only."""
from pathlib import Path
r=Path(__file__).resolve().parents[2]
pane=(r/"widgets/FinanceStockHistoryPane.qml").read_text()
policy=(r/"widgets/FinanceStockChartPointPolicy.js").read_text()
service=(r/"services/finance/FinanceStockHistoryReadService.qml").read_text()
app=(r/"widgets/FinanceW.qml").read_text()
market=(r/"widgets/FinanceMarketPane.qml").read_text()
sec=(r/"services/finance/FinanceSecPriceReadService.qml").read_text()
provider=(r/"scripts/finance/read_market_price_range.mjs").read_text()
hub=(r/"scripts/finance/market_data_hub.mjs").read_text()
oldpolicy=(r/"widgets/FinanceStockModePolicy.js").read_text()

assert app.count("PanelWindow {") == 1
assert app.count("FinanceToolHost {") == 1
assert app.count("FinanceServices.FinanceStockHistoryReadService {") == 1
assert 'label: "POLYMARKET"' in market and 'label: "OSIRIS"' in market
assert 'label: "STOCKS"' in market

assert 'import "FinanceStockChartPointPolicy.js" as ChartPointPolicy' in pane
assert 'property int selectedPointIndex: -1' in pane
assert 'readonly property var inspectedPoint: !dayMode' in pane
assert 'ChartPointPolicy.selectedBar(priceBars, selectedPointIndex)' in pane
assert 'function inspectChartPoint(x, y)' in pane
assert 'ChartPointPolicy.nearestPoint(priceBars,' in pane
assert 'priceCanvas.width, priceCanvas.height, x, y, 18' in pane
assert 'selectedPointIndex = index === selectedPointIndex ? -1 : index;' in pane
assert 'onPriceBarsChanged: {' in pane
assert 'selectedPointIndex = -1;' in pane
assert 'onDayModeChanged: {' in pane
assert 'onSelectedPointIndexChanged: priceCanvas.requestPaint()' in pane
assert 'Canvas {' in pane
assert 'ctx.strokeStyle = "#C74EC7"' in pane
assert 'ctx.fillStyle = "#ED981A"' in pane
assert 'ctx.arc(point.x, point.y, 5, 0, Math.PI * 2)' in pane
assert 'MouseArea {' in pane
assert 'enabled: !stocks.dayMode && stocks.priceBars.length >= 2' in pane
assert 'acceptedButtons: Qt.LeftButton' in pane
assert 'stocks.inspectChartPoint(mouse.x, mouse.y)' in pane
assert 'stocks.inspectedPoint.date' in pane
assert 'stocks.inspectedPoint.price.toFixed(2)' in pane
assert 'stocks.snapshot.symbol' in pane
assert 'stocks.snapshot.priceBasis' in pane
assert 'CLICK A DATA POINT TO INSPECT' in pane
assert pane.count("FinanceDateInput {") == 3
assert 'label: "DAY"' in pane and 'label: "RANGE"' in pane
assert 'stocks.stockFeed.refresh()' in pane
assert 'stocks.stockFeed.selectMode("day")' in pane
assert 'stocks.stockFeed.selectMode("range")' in pane

assert 'function pointAt(bars, width, height, index)' in policy
assert 'function nearestPoint(bars, width, height, x, y, radius)' in policy
assert 'function selectedBar(bars, index)' in policy
assert 'const d2 = dx * dx + dy * dy' in policy
assert 'if (d2 <= distanceSquared)' in policy
assert 'return {date:bar.date, price:bar.price, index:index};' in policy
assert 'point.price' not in policy or 'bar.price' in policy
assert 'function selectWindow' in oldpolicy
assert 'selectDayDate(day)' in service and 'selectStartDate(day)' in service
assert 'selectEndDate(day)' in service
assert 'FINANCE_STOCK_RANGE ' in service
assert 'read_market_price_range_optional_hub.mjs' in service
assert 'FINANCE_SEC_PRICE ' in sec and 'read_sec_price_optional_hub.mjs' in sec
assert 'MAX_RANGE_DAYS = 180' in provider
assert 'getPriceRange' in hub

# Hit testing is QML-only. No fetching, writing, shelling or market orders.
for forbidden in ('fetch(', 'reader.exec(', 'Process {', 'writeFile(', 'Qt.openUrlExternally',
                  'setInterval(', 'financeWrite.submit(', 'financeFundingWrite.submit('):
    assert forbidden not in policy, forbidden
for forbidden in ('fetch(', 'reader.exec(', 'writeFile(', 'Qt.openUrlExternally',
                  'financeWrite.submit(', 'financeFundingWrite.submit('):
    assert forbidden not in pane, forbidden
print("Finance M12 on-chart existing-session selection and no-write contracts: PASS")
