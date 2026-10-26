#!/usr/bin/env python3
"""Finance M14: one guarded UI-only in-memory return, no provider request."""
from pathlib import Path
r=Path(__file__).resolve().parents[2]
service=(r/"services/finance/FinanceStockHistoryReadService.qml").read_text()
pane=(r/"widgets/FinanceStockHistoryPane.qml").read_text()
policy=(r/"widgets/FinanceStockModePolicy.js").read_text()
app=(r/"widgets/FinanceW.qml").read_text()
market=(r/"widgets/FinanceMarketPane.qml").read_text()
sec=(r/"services/finance/FinanceSecPriceReadService.qml").read_text()
provider=(r/"scripts/finance/read_market_price_range.mjs").read_text()
adapter=(r/"scripts/finance/read_market_price_range_optional_hub.mjs").read_text()

assert app.count("PanelWindow {")==1
assert app.count("FinanceToolHost {")==1
assert 'FinanceServices.FinanceStockHistoryReadService {' in app
assert 'label: "POLYMARKET"' in market and 'label: "OSIRIS"' in market
assert 'label: "STOCKS"' in market
assert 'property var returnTicket: null' in service
assert 'readonly property bool canReturnToRange: monitoring && ready' in service
assert 'snapshot.derivedFromRange === true && returnTicket !== null' in service
assert 'returnTicket.cik === selectedCik' in service
assert 'returnTicket.openedDay === dayDate' in service
assert 'returnTicket.from === startDate && returnTicket.to === endDate' in service
assert 'function openRangePointInDay(index, expectedDate)' in service
assert 'StockModePolicy.rangeReturnTicket(' in service
assert 'returnTicket = ticket;' in service
assert 'function returnToRange()' in service
restore=service.split("    function returnToRange()",1)[1].split(
    "    function selectStartDate(day)",1)[0]
assert 'if (!canReturnToRange || loading || reader.running) return false;' in restore
assert 'StockModePolicy.rangeFromReturnTicket(' in restore
assert 'returnTicket, snapshot, selectedCik, startDate, endDate' in restore
assert 'if (!restored)' in restore
assert 'returnTicket = null;' in restore
assert 'displayMode = "range";' in restore
assert 'snapshot = restored;' in restore
assert 'state = "ready";' in restore
assert 'RANGE RESTORED FROM MEMORY // NO NEW MARKET REQUEST' in restore
for forbidden in ('reader.exec(', 'refresh(', 'fetch(', 'startDate =',
                  'endDate =', 'selectDayDate(', 'financeWrite.submit(',
                  'Process {', 'clear();', 'writeFile('):
    assert forbidden not in restore, forbidden

assert 'function clear() {' in service
clear=service.split("    function clear() {",1)[1].split(
    "    onMonitoringChanged:",1)[0]
assert 'returnTicket = null;' in clear
assert 'if (!monitoring) clear();' in service
assert 'if (dayDate !== day) {dayDate=day;clear();}' in service
assert 'if (selectedCik !== cik)' in service
assert 'if (startDate !== day) {startDate=day;clear();}' in service
assert 'if (endDate !== day) {endDate=day;clear();}' in service
assert 'if (displayMode !== nextMode)' in service
assert 'returnTicket = null;' in service.split("    function refresh()",1)[1]
assert 'reader.exec([' in service
assert 'read_market_price_range_optional_hub.mjs' in service

assert 'label: "BACK TO RANGE"' in pane
assert 'id: backToRange' in pane
assert 'visible: stocks.dayMode && stocks.stockFeed' in pane
assert 'stocks.stockFeed.canReturnToRange' in pane
assert 'stocks.stockFeed.returnToRange()' in pane
assert 'stocks.snapshot.restoredFromDay' in pane
assert 'RANGE SOURCE // RESTORED FROM MEMORY // NO NEW REQUEST' in pane
assert 'label: "OPEN IN DAY"' in pane
assert 'stocks.stockFeed.openRangePointInDay(' in pane
assert 'label: "DAY"' in pane and 'label: "RANGE"' in pane
assert pane.count("FinanceDateInput {")==3
assert 'priceCanvas.requestPaint()' in pane

assert 'function rangeReturnTicket(snapshot, index, cik, from, to)' in policy
assert 'daySnapshotFromRange(snapshot, index, cik, from, to)' in policy
assert 'snapshot.bars.length > 132' in policy
assert 'JSON.parse(JSON.stringify(snapshot))' in policy
assert 'function rangeFromReturnTicket(ticket, daySnapshot, cik, from, to)' in policy
assert 'daySnapshot.derivedFromRange !== true' in policy
assert 'daySnapshot.originRange.from !== from' in policy
assert 'daySnapshot.delivery.cachedAt !== ticket.snapshot.delivery.cachedAt' in policy
assert 'restored.restoredFromDay = true;' in policy
assert 'restored.returnedFromDay = ticket.openedDay;' in policy

assert 'FINANCE_SEC_PRICE ' in sec
assert 'MAX_RANGE_DAYS = 180' in provider
assert 'FINANCE_STOCK_RANGE ' in adapter
for forbidden in ('reader.exec(', 'Process {', 'fetch(', 'writeFile(',
                  'financeWrite.submit(', 'Qt.openUrlExternally'):
    assert forbidden not in pane+policy, forbidden
print("Finance M14 guarded BACK TO RANGE and no-request contracts: PASS")
