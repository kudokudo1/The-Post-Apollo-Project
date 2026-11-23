#!/usr/bin/env python3
"""Research M4a: isolate the explicit read path from M2 financial/research writes."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
service = (root / "services/finance/FinanceResearchInvestigationReadService.qml").read_text()
host = (root / "widgets/FinanceResearchInvestigationsReadHost.qml").read_text()
pane = (root / "widgets/FinanceResearchInvestigationsPane.qml").read_text()
bridge = (root / "scripts/finance/research_investigation_read_bridge.mjs").read_text()
assert 'import Quickshell.Io' in service
assert 'property bool monitoring: false' in service
assert 'property int generation: 0' in service
assert 'submittedGeneration === researchRead.generation' in service
assert 'function load()' in service
assert '"scripts/finance/research_investigation_read_bridge.mjs"' in service
assert 'commandFrame = \'{"action":"list"}\\n\'' in service
assert 'stdinEnabled: true' in service
assert 'state = "failed"' in service
assert 'state = "ready"' in service
assert 'FINANCE_RESEARCH_READ_RESULT ' in service
assert 'monitoring: host.active' in host
assert 'controllerConnected: host.active' in host
assert 'writeEnabled: false' in host
assert 'onLoadRequested: readService.load()' in host
assert 'FinanceResearchInvestigationsPane {' in host
assert 'signal createRequested(' in pane
assert 'signal attachRequested(' in pane
assert 'signal removeRequested(' in pane
assert 'readOneLine(process.stdin)' in bridge
assert 'process.argv.length !== 2' in bridge
assert 'readStore({action:"list"})' in bridge
for text in (service,host):
    for banned in ('onCreateRequested:', 'onAttachRequested:', 'onRemoveRequested:',
                   'writeFile', 'Qt.openUrlExternally', 'FinanceW.qml',
                   'financeWrite.submit(', 'allowWrites: true'):
        assert banned not in text, banned
assert 'Process {' in service
assert 'Process {' not in host
# Shared main navigation stays outside this PR.
print("Finance Research M4 read-only controller contract: PASS")
