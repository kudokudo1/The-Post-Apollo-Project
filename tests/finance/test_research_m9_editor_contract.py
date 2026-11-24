#!/usr/bin/env python3
"""M9: selected SEC candidate -> existing M3 editor; absolutely no writer."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
host=(root/"widgets/FinanceResearchEvidenceCandidatePreviewHost.qml").read_text()
picker=(root/"widgets/FinanceResearchEvidenceCandidatePicker.qml").read_text()
editor=(root/"widgets/FinanceResearchInvestigationsPane.qml").read_text()
read_service=(root/"services/finance/FinanceResearchInvestigationReadService.qml").read_text()
draft_service=(root/"services/finance/FinanceResearchCandidateDraftService.qml").read_text()
draft_bridge=(root/"scripts/finance/research_candidate_draft_preview.mjs").read_text()
m6=(root/"scripts/finance/research_evidence_candidates.mjs").read_text()

for marker in (
    "signal reviewRequested(string candidateKey)",
    'label: "REVIEW IN CASE EDITOR"',
    "visible: picker.selectedCandidate !== null",
    'picker.selectedCandidate.kind === "sec-index"',
    "picker.selectedCandidate.eligibleForDraft === true",
    "picker.reviewRequested(",
):
    assert marker in picker,marker
for marker in (
    'import "../components"',
    "property bool reviewOpen: false",
    "property string reviewKey:",
    "function beginReview(key)",
    "function prepareDraft()",
    "function applyPreparedDraft(data)",
    "function closeReview()",
    "onActiveChanged:",
    "function onCandidatePreviewChanged()",
    'target: readService',
    "function onRevisionChanged()",
    "FinanceServices.FinanceResearchInvestigationReadService {",
    "monitoring: host.active && host.reviewOpen",
    "FinanceServices.FinanceResearchCandidateDraftService {",
    "onPreparedDraftChanged: host.applyPreparedDraft(preparedDraft)",
    "FinanceResearchEvidenceCandidatePicker {",
    "onPreviewRequested: previewService.refresh()",
    "onReviewRequested: function(candidateKey)",
    "FinanceResearchInvestigationsPane {",
    "id: caseEditor",
    "visible: host.reviewOpen",
    "writeEnabled: false",
    "onLoadRequested: readService.load()",
    'label: "BACK"',
    'label: host.width < 430 ? "PREPARE" : "PREPARE UNSAVED"',
    "reviewActions.availableWidth * (host.scratchSelected",
    "reviewActions.availableWidth * (host.scratchSelected",
    "caseEditor.draftEvidenceTitle = data.fields.title;",
    "caseEditor.draftEvidenceSummary = data.fields.summary;",
    "caseEditor.draftEvidenceUrl = data.fields.url;",
    "caseEditor.draftSource = \"manual\";",
    "data.caseRevision !== selectedRevision",
    "data.candidateKey !== reviewKey",
    "draftService.clear();",
):
    assert marker in host,marker
assert host.count("FinanceResearchInvestigationsPane {")==1
assert host.count("FinanceServices.FinanceResearchInvestigationReadService {")==1
assert host.count("FinanceServices.FinanceResearchCandidateDraftService {")==1
assert "FinanceResearchInvestigationWriteService" not in host
assert "Process {" not in host
for forbidden in (
    "onAttachRequested:", "onCreateRequested:", "onRemoveRequested:",
    "writeEnabled: true", "Qt.openUrlExternally",
    "attachEvidence(", "run({action:\"attach\"",
    "FinanceResearchWriteAttempt", "worker.exec",
):
    assert forbidden not in host,forbidden
assert 'property bool writeEnabled: false' in editor
assert 'available: pane.canAttach' in editor
assert 'controllerConnected && writeEnabled && loadState === "ready"' in editor
assert 'onLoadRequested: readService.load()' in host
assert 'readService.load()' in host
assert 'commandFrame = \'{"action":"list"}\\n\';' in read_service
for marker in (
    "function prepare(candidate, investigation, revision)",
    "function complete(force)",
    "function clear()",
    'state = "loading"',
    'preparedDraft = null',
    "if (ok && acceptResult(raw))",
    'readonly property bool loading: state === "loading"',
    "caseRevision: revision",
    "FINANCE_RESEARCH_DRAFT_RESULT ",
    "DRAFT REFUSED // ",
    "Quickshell.shellPath(",
    "research_candidate_draft_preview.mjs",
):
    assert marker in draft_service,marker
for marker in (
    "prepareCandidateAttachDraft", "prepareUnsavedCitation(",
    'request.action!=="prepare-draft"',
    'readOnly:true,preparedOnly:true',
    'source:"manual",reviewed:false',
    'caseRevision:request.caseRevision',
    'const MAX_INPUT_BYTES = 200000',
    'const MAX_RESULT_BYTES = 5500',
    "process.argv.length!==2",
):
    assert marker in draft_bridge,marker
assert "import fs " not in draft_bridge
assert "import { run" not in draft_bridge
assert "fetch(" not in draft_bridge
assert "Process {" not in editor
assert "prepareCandidateAttachDraft" in m6
assert (root/"services/finance/FinanceResearchCandidateDraftService.qml").is_file()
assert (root/"scripts/finance/research_candidate_draft_preview.mjs").is_file()
assert not (root/"services/finance/qmldir").exists(), (
    "If qmldir is introduced, the draft service must be registered"
)
print("Finance Research M9 selected-candidate editor review contract: PASS")
