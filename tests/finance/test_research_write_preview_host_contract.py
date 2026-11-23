#!/usr/bin/env python3
"""M4b-T2 preview host: safe in-memory walkthrough, no real write activation."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
preview = (root / "widgets/FinanceResearchWriteOutcomePreviewHost.qml").read_text()
panel = (root / "widgets/FinanceResearchWriteOutcomePanel.qml").read_text()
read = (root / "widgets/FinanceResearchInvestigationsReadHost.qml").read_text()

for marker in (
    "property bool active: false",
    'property string demoPhase: "staged"',
    "property bool draftPresent: true",
    "function beginPreview()",
    "if (demoPhase !== \"staged\" || !draftPresent) return false;",
    'demoPhase = "inFlight"',
    "function acknowledgePreview()",
    "if (!demoPending) return false;",
    "draftPresent = false;",
    'demoPhase = "acknowledged"',
    "function unknownPreview()",
    "draftPresent = true;",
    'demoPhase = "reviewRequired"',
    "function refusePreview()",
    'demoPhase = "refused"',
    "function resetPreview()",
    "if (demoPending) return false;",
    "FinanceResearchInvestigationsReadHost {",
    "FinanceResearchWriteOutcomePanel {",
    "simulationOnly: true",
    "readerConnected: false",
    "exactAcknowledgement: false",
    "acknowledgedRevision: -1",
    "active: preview.active",
    "TEST DISPATCH",
    "TEST ACK",
    "TEST UNKNOWN",
    "TEST REFUSE",
    "RESET DEMO",
    "onLeftClicked: preview.beginPreview()",
    "onLeftClicked: preview.acknowledgePreview()",
    "onLeftClicked: preview.unknownPreview()",
    "onLeftClicked: preview.refusePreview()",
    "onLeftClicked: preview.resetPreview()",
):
    assert marker in preview, marker

for forbidden in (
    "Process {", "Qt.openUrlExternally", "onCreateRequested:",
    "onAttachRequested:", "onRemoveRequested:", "writeFile",
    "financeWrite", "dispatchOnce", "onLeftClicked: preview.write",
    "FinanceW.qml", "Quickshell.Io",
):
    assert forbidden not in preview, forbidden

assert "writeEnabled: false" in read
assert "onCreateRequested:" not in read
assert "onAttachRequested:" not in read
assert "onRemoveRequested:" not in read
assert "readonly property bool simulatedAck:" in panel
assert "simulationOnly && phase === \"acknowledged\"" in panel
assert "if (simulationOnly) {" in panel
assert "TEST ACK RECEIVED // NOT SAVED TO LIVE STORAGE" in panel
assert "TEST OUTCOME UNKNOWN // KEEP DRAFT" in panel
assert "TEST REFUSED // NO LIVE WRITE" in panel
assert "!simulationOnly && phase === \"acknowledged\"" in panel
print("Finance Research M4b-T2 preview host contract: PASS")
