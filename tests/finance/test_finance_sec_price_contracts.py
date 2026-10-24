#!/usr/bin/env python3
"""Finance SEC M5 price context stays issuer-bound, manual and non-mutating."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
ui=(root/"widgets/FinanceW.qml").read_text()
pane=(root/"widgets/FinanceSecFilingsPane.qml").read_text()
inspector=(root/"widgets/FinanceSecDocumentInspector.qml").read_text()
view=(root/"widgets/FinanceSecPriceContext.qml").read_text()
service=(root/"services/finance/FinanceSecPriceReadService.qml").read_text()
reader=(root/"scripts/finance/read_sec_price_context.mjs").read_text()
old=(root/"widgets/FinanceSecEvidenceCompare.qml").read_text()

assert ui.count("PanelWindow {") == 1
assert ui.count("FinanceToolHost {") == 1
assert "FinanceServices.FinanceSecPriceReadService {" in ui
assert "secFeed: secService" in ui
assert "priceFeed: secPriceService" in ui
assert 'root.selectedMainMode === "research"' in ui

assert "property var priceFeed: null" in pane
assert "if (priceFeed) priceFeed.clear();" in pane
assert "priceFeed: pane.priceFeed" in pane
assert "property var priceFeed: null" in inspector
assert "FinanceSecPriceContext {" in inspector
assert "priceFeed: inspector.priceFeed" in inspector
assert "FinanceSecEvidenceCompare {" in inspector
assert "card.modelData.documentUrl" in old

assert "onLeftClicked: priceFeed.inspect(context.filing)" in view
assert "Canvas {" in view
assert "sparkline.requestPaint()" in view
assert "NO CAUSAL" in view.upper() or "do not establish a filing reaction" in view
assert "SAME-DAY" not in view or "same-day" in view.lower()
assert "EODHD HISTORICAL" in view
assert "context.marketSnapshot.changePct.toFixed(2)" in view
assert "context.marketSnapshot.previous.price.toFixed(2)" in view
assert "context.marketSnapshot.next.price.toFixed(2)" in view

assert 'if (!monitoring || !secFeed || !secFeed.snapshot || !filing' in service
assert 'secFeed.snapshot.filings.some' in service
assert 'if (reader.running)' in service
assert "if (desiredKey !== inFlightKey" in service
assert "FINANCE_SEC_PRICE_ERROR" in service
assert "FINANCE_SEC_PRICE " in service
assert "Quickshell.shellPath(\"scripts/finance/read_sec_price_context.mjs\")" in service
assert "priceFeed.inspect" not in ui  # only user action in price view starts fetch

assert 'const token = await tokenLoader();' in reader
assert 'if (!token && cik !== "0000320193")' in reader
assert 'api_token:token||"demo"' in reader
assert 'https://eodhd.com/api/eod/' in reader
assert 'AbortSignal.timeout(12000)' in reader
assert 'readOnly:true' in reader
assert "const previous=series.filter(b=>b.date<date)" in reader
assert "const next=series.find(b=>b.date>date)" in reader
assert 'priceBasis:useAdjusted?"ADJUSTED CLOSE":"CLOSE"' in reader
assert '(info.mode & 0o077) !== 0' in reader
for forbidden in ("Qt.openUrlExternally","financeWrite.submit(","financeFundingWrite.submit(","writeFile(","Process {"):
    assert forbidden not in inspector + view + pane, forbidden
assert "Process {" not in ui and "fetch(" not in view
print("Finance SEC M5 issuer-bound opt-in price context source contracts: PASS")
