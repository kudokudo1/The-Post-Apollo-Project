#!/usr/bin/env python3
"""Finance Research M4b-T2 outcome UI: staging only, no live write path."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
panel=(root/"widgets/FinanceResearchWriteOutcomePanel.qml").read_text()
host=(root/"widgets/FinanceResearchInvestigationsReadHost.qml").read_text()
dispatcher=(root/"scripts/finance/research_investigation_disposable_dispatcher.mjs").read_text()
for item in (
    "property bool simulationOnly: true",
    "property bool readerConnected: false",
    "property bool exactAcknowledgement: false",
    "property int acknowledgedRevision: -1",
    "phase === \"acknowledged\"",
    "exactAcknowledgement && acknowledgedRevision >= 0",
    "OUTCOME UNKNOWN // KEEP DRAFT",
    "RELOAD READ ONLY",
    "signal reloadRequested()",
    "textFormat: Text.PlainText",
    "DISPOSABLE PREVIEW // NOT SAVED TO LIVE STORAGE",
):
    assert item in panel, item
assert "available: !feedback.simulationOnly && feedback.unresolved" in panel
assert "onLeftClicked: feedback.reloadRequested()" in panel
for forbidden in ("Process {","Qt.openUrlExternally","onCreateRequested:",
                  "onAttachRequested:","onRemoveRequested:","financeWrite",
                  "FinanceW.qml","onLeftClicked: feedback.dispatch"):
    assert forbidden not in panel, forbidden
assert "writeEnabled: false" in host
assert "onCreateRequested:" not in host
assert "onAttachRequested:" not in host
assert "onRemoveRequested:" not in host
assert "constructor(targetOverride)" in dispatcher
assert "TARGET_OVERRIDE_FORBIDDEN" in dispatcher
assert "fs.mkdtempSync" in dispatcher
assert "run(command,this.#dir)" in dispatcher
assert "XDG_DATA_HOME" not in dispatcher.split("import fs")[1]
print("Finance Research M4b-T2 outcome UI contract: PASS")
