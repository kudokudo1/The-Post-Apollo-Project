#!/usr/bin/env python3
"""Finance SEC M4 evidence desk: no fetches, no Budget changes, state bounded."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceSecFilingsPane.qml").read_text()
inspector=(root/"widgets/FinanceSecDocumentInspector.qml").read_text()
comparison=(root/"widgets/FinanceSecEvidenceCompare.qml").read_text()
policy=(root/"widgets/FinanceSecEvidencePolicy.js").read_text()
root_ui=(root/"widgets/FinanceW.qml").read_text()
service=(root/"services/finance/FinanceSecDocumentReadService.qml").read_text()

assert root_ui.count("PanelWindow {") == 1
assert root_ui.count("FinanceToolHost {") == 1
assert 'FinanceSecDocumentInspector {' in pane
assert 'import "FinanceSecEvidencePolicy.js" as EvidencePolicy' in pane
assert 'readonly property var filteredFilings: EvidencePolicy.filterFilings(filings, filterMode)' in pane
assert 'model: pane.filteredFilings' in pane
for mode in ('"all"','"insider"','"events"','"owners"','"reports"'):
    assert mode in pane, mode
assert 'property var pinnedEvidence: []' in pane
assert 'function pinCurrentEvidence()' in pane
assert 'function clearEvidence()' in pane
assert 'onFilingsChanged:' in pane and 'clearEvidence();' in pane
assert 'documentFeed.state !== "ready"' in pane
assert 'secFeed.snapshot.cik' in pane
assert 'pinMessage: pane.pinMessage' in pane

assert 'import "FinanceSecEvidencePolicy.js" as EvidencePolicy' in inspector
assert 'signal pinRequested()' in inspector and 'signal clearRequested()' in inspector
assert 'onLeftClicked: inspector.pinRequested()' in inspector
assert 'onLeftClicked: inspector.clearRequested()' in inspector
assert 'onLeftClicked: inspector.compareActive = !inspector.compareActive' in inspector
assert 'evidenceSlots.length === 2' in inspector
assert 'FinanceSecEvidenceCompare {' in inspector
assert 'EvidencePolicy.filterTransactions(details.transactions, transactionFilter)' in inspector
for mode in ('"all"','"P"','"S"','"A"','"M"','"other"'):
    assert mode in inspector,mode
assert 'inspector.filteredTransactions' in inspector

assert 'model: comparison.evidenceSlots' in comparison
assert 'comparison.wide ? 2 : 1' in comparison
assert 'card.modelData.documentUrl' in comparison
assert 'FILING HEADING' not in comparison # no invented source status

assert 'return pinned.slice(-2);' in policy
assert 'row.cik === cik' in policy
assert 'document.cik !== cik' in policy
assert 'document.accession !== filing.accession' in policy
assert 'document.form !== filing.form' in policy
assert 'source:' not in policy
assert 'Qt.openUrlExternally' not in pane + inspector + comparison
for forbidden in ('Process {','writeFile(', 'fetch(', 'financeWrite.submit('):
    assert forbidden not in pane + inspector + comparison + policy, forbidden
assert 'FINANCE_SEC_DETAIL ' in service
print("Finance SEC M4 isolated evidence desk source contracts: PASS")
