#!/usr/bin/env python3
"""Research M3 isolated pane contract. No live financial or filesystem actuation."""
from pathlib import Path
p = Path(__file__).resolve().parents[2] / "widgets/FinanceResearchInvestigationsPane.qml"
s = p.read_text()
for marker in (
    'property var investigations: []',
    'property bool writeEnabled: false',
    'property string loadState: "preview"',
    'readonly property var selectedInvestigation:',
    'signal loadRequested()',
    'signal createRequested(string title, string question)',
    'signal attachRequested(string investigationId, string source, string title,',
    'signal removeRequested(string investigationId, string evidenceId)',
    'available: pane.canCreate',
    'available: pane.canAttach',
    'pane.armedRemoveId = evidenceRow.modelData.id',
    'pane.removeRequested(pane.selectedId, evidenceRow.modelData.id)',
    'NeonScrollPaneV2 {',
    'columns: pane.wide ? 2 : 1',
    'textFormat: Text.PlainText',
    'SOURCES '
):
    assert marker in s, marker
for forbidden in (
    "Process {", "Qt.openUrlExternally", "XMLHttpRequest",
    "financeWrite", "financeBudget", "FinanceW.qml",
    "writeFile", "fetch(", "exec(", "onCompleted: pane.createRequested",
    "property bool writeEnabled: true"
):
    assert forbidden not in s, forbidden
assert s.count('ActionButton {') >= 7
assert 'writeEnabled && loadState === "ready"' in s
print("Finance Research M3 isolated pane contracts: PASS")
