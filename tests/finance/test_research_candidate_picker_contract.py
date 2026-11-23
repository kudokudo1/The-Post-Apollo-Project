#!/usr/bin/env python3
"""Research M7: source-selection UI keeps M6 read-only and cannot write."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
picker=(root/"widgets/FinanceResearchEvidenceCandidatePicker.qml").read_text()
host=(root/"widgets/FinanceResearchEvidenceCandidatePreviewHost.qml").read_text()
service=(root/"services/finance/FinanceResearchCandidatePreviewService.qml").read_text()
bridge=(root/"scripts/finance/research_candidate_preview_bridge.mjs").read_text()
model=(root/"scripts/finance/research_evidence_candidates.mjs").read_text()

for token in (
    'import "../components"',
    "NeonScrollPaneV2 {",
    "ActionButton {",
    'label: "ALL"',
    'label: "SEC"',
    'label: "DEMO"',
    '"BUILD PREVIEW"',
    "onLeftClicked: picker.previewRequested()",
    "onLeftClicked: picker.selectedKey = modelData.key",
    "onCandidatePreviewChanged:",
    "onFilterModeChanged:",
    "previewRequested()",
    'labelItem.textFormat: Text.PlainText',
    'textFormat: Text.PlainText',
    "NO SOURCE INSPECTED",
    "NO EVIDENCE SAVE AVAILABLE",
    "DEMO DATA // CANNOT ATTACH TO FINANCIAL RESEARCH",
    "PREVIEW ONLY // SOURCE CONTENT NOT AUTHENTICATED // NO WRITES"
):
    assert token in picker, token

for token in (
    "property bool active: false",
    "property var secFeed: null",
    "property var crawlFeed: null",
    "FinanceServices.FinanceResearchCandidatePreviewService {",
    "FinanceResearchEvidenceCandidatePicker {",
    "monitoring: host.active",
    "secFeed: host.secFeed",
    "crawlFeed: host.crawlFeed",
    "onPreviewRequested: previewService.refresh()",
    "onSnapshotChanged() { previewService.clear(); }",
    "onSelectedCikChanged() { previewService.clear(); }",
):
    assert token in host, token

for token in (
    "property bool monitoring: false",
    "property int generation: 0",
    "property int submittedGeneration: -1",
    "function clear()",
    "function refresh()",
    "if (!monitoring || worker.running || loading)",
    "secFeed.state === \"ready\"",
    "crawlFeed.state === \"ready\"",
    "JSON.stringify({",
    'action: "preview", selectedCik: cik,',
    "Quickshell.shellPath(",
    "research_candidate_preview_bridge.mjs",
    "stdinEnabled: true",
    "worker.write(candidateService.requestFrame)",
    "submittedGeneration",
    "=== candidateService.generation",
    "candidateService.monitoring",
    "candidateService.candidatePreview = null",
    "state = \"failed\"",
    "FINANCE_RESEARCH_CANDIDATES_RESULT ",
    "item.reviewed !== false",
    "item.authenticatedProvenance !== false",
    "item.eligibleForDraft === false"
):
    assert token in service, token

for token in (
    "previewEvidenceCandidates",
    "process.argv.length!==2",
    'request.action!=="preview"',
    'Buffer.byteLength(frame,"utf8") > MAX_REQUEST_BYTES',
    "const frame=await readCandidateFrame(process.stdin)",
    "RESULT_PREFIX+payload",
    "INVALID_SOURCE_SNAPSHOT",
):
    assert token in bridge, token

for text in (picker,host,service,bridge):
    for banned in (
        "onAttachRequested:", "onCreateRequested:", "onRemoveRequested:",
        "run({action:\"create\"", "FinanceResearchInvestigationStore",
        "writeEnabled: true", "Qt.openUrlExternally", "shellCommand",
        "financeWrite.submit(", "allowWrites: true", "Process.execCommand"
    ):
        assert banned not in text, banned

assert "Process {" not in picker
assert "Process {" not in host
assert service.count("Process {")==1
assert "Process {" not in model
assert "import fs " not in bridge
assert "import { run" not in bridge
assert "fetch(" not in bridge
assert not (root/"widgets/qmldir").exists(), (
    "If widgets/qmldir is introduced, the M7 picker/host must be exported"
)
assert not (root/"services/finance/qmldir").exists(), (
    "If finance services get a qmldir, the M7 service must be exported"
)
print("Finance Research M7 candidate picker and read-only owner wiring: PASS")
