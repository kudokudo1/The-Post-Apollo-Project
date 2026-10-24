#!/usr/bin/env python3
"""M3 document inspector source contracts. No external SEC requests."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
menu = (root/"widgets/FinanceW.qml").read_text()
index = (root/"scripts/finance/read_sec_filings.mjs").read_text()
sec_service = (root/"services/finance/FinanceSecReadService.qml").read_text()
service = (root/"services/finance/FinanceSecDocumentReadService.qml").read_text()
pane = (root/"widgets/FinanceSecFilingsPane.qml").read_text()
inspector = (root/"widgets/FinanceSecDocumentInspector.qml").read_text()
parser = (root/"scripts/finance/inspect_sec_document.py").read_text()

assert menu.count("PanelWindow {") == 1
assert menu.count("FinanceToolHost {") == 1
assert 'FinanceServices.FinanceSecDocumentReadService {' in menu
assert 'secFeed: secService' in menu
assert 'documentFeed: secDocumentService' in menu
assert "FinanceSecFilingsPane {" in menu
assert 'monitoring: root.menuOpen && root.selectedMainMode === "research"' in menu

assert 'primaryDocument: document' in index
assert 'Array.isArray(recent.items)' in index
assert 'xslF345X' in index
assert 'typeof f.primaryDocument === "string"' in sec_service
assert 'Array.isArray(f.items)' in sec_service

assert 'property var documentFeed: null' in pane
assert 'FinanceSecDocumentInspector {' in pane
assert 'onSelectedIndexChanged:' in pane
assert 'documentFeed.clear();' in pane
assert 'INSPECT' in inspector
assert 'onLeftClicked: documentFeed.inspect(inspector.filing)' in inspector
assert 'NON-DERIVATIVE TRANSACTIONS' in inspector
assert 'REPORTED ITEM CLASSIFICATIONS' in inspector
assert 'EST. NOTIONAL' in inspector
assert 'source: "sec-edgar-document"' in parser or '"sec-edgar-document"' in parser
assert 'XML' not in parser or 'ET.fromstring' in parser
assert 'xml.etree.ElementTree' in parser
assert 'HTMLParser' in parser
assert 'NoRedirect' in parser
assert 'agent_loader()' in parser
assert 'no-supported-transactions' in parser
assert 'MAX_BYTES = 2_000_000' in parser
assert 'FINANCE_SEC_DETAIL' in parser
assert 'only fixed' in service.lower() or 'prevalidated filing' in service.lower()
assert 'if (reader.running)' in service
assert 'if (desiredKey !== inFlightKey)' in service
assert 'secFeed.snapshot.filings.some' in service
assert '["4","4/A","8-K","8-K/A"]' in service
assert 'catch (error)' in service
for forbidden in ('Qt.openUrlExternally', 'financeWrite.submit(',
                  'financeFundingWrite.submit(', 'writeFile(', 'fetch('):
    assert forbidden not in inspector + service, forbidden
print("Finance SEC M3 on-demand document inspection contracts: PASS")
