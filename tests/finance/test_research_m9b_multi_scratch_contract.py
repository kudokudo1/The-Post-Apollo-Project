#!/usr/bin/env python3
"""Research M9b contract: multiple unpersisted citations, not an M2 writer."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceResearchInvestigationsPane.qml").read_text()
host=(root/"widgets/FinanceResearchEvidenceCandidatePreviewHost.qml").read_text()
service=(root/"services/finance/FinanceResearchScratchEvidenceService.qml").read_text()
bridge=(root/"scripts/finance/research_scratch_citation_preview.mjs").read_text()
model=(root/"scripts/finance/research_investigations.mjs").read_text()
for marker in (
    "property bool scratchAppendReady: false",
    "signal appendScratchRequested(string title, string summary, string url)",
    'label: "ADD TO SCRATCH"',
    "available: visible && pane.controllerConnected",
    "&& pane.scratchAppendReady",
    "pane.appendScratchRequested(",
    'label: "ATTACH SOURCE"',
    "available: pane.canAttach",
    "pane.controllerConnected && pane.writeEnabled && pane.loadState",
    "UNSAVED SCRATCH // "
):
    assert marker in pane,marker
for marker in (
    "property var scratchCase: null",
    "readonly property bool scratchSelected:",
    "readonly property bool scratchAppendReady:",
    "scratchEvidenceCount < 40",
    "function addToScratch(title, summary, url)",
    "function applyAppendedCase(data)",
    "function pickNextFiling()",
    "function closeReview()",
    "discardScratch();",
    "scratchEvidenceService.clear();",
    "scratchCase = data.scratchCase;",
    "draftService.clear();",
    "onResultChanged: host.applyAppendedCase(result)",
    "monitoring: host.active && host.reviewOpen",
    "FinanceServices.FinanceResearchScratchEvidenceService {",
    "label: \"PICK NEXT\"",
    "host.pickNextFiling()",
    "caseEditor.scratchAppendReady",
    "host.addToScratch(title, summary, url);",
    "writeEnabled: false",
    "onCandidatePreviewChanged()",
    "if (host.reviewOpen || host.scratchCase !== null)",
    "if (!active) closeReview();",
):
    # caseEditor wiring uses 'scratchAppendReady: host...'
    if marker == "caseEditor.scratchAppendReady":
        assert "scratchAppendReady: host.scratchAppendReady" in host
    else:
        assert marker in host,marker
for forbidden in (
    "onAttachRequested:", "onCreateRequested:", "onRemoveRequested:",
    "writeEnabled: true", "FinanceResearchInvestigationWriteService",
    "FinanceResearchWriteAttempt", "Qt.openUrlExternally",
    "FileView {", "worker.exec(",
):
    assert forbidden not in host, forbidden
for marker in (
    "property bool monitoring: false",
    "function append(candidate, prepared, scratchCase, fields)",
    "function accept(raw)",
    "function complete(force)",
    "onMonitoringChanged: clear()",
    'result = null;',
    '"scripts/finance/research_scratch_citation_preview.mjs"',
    "FINANCE_RESEARCH_SCRATCH_RESULT ",
    "FINANCE_RESEARCH_SCRATCH_ERROR ",
    "data.persisted !== false",
    "data.memoryOnly !== true",
    "JSON.stringify(item.evidence.slice(0, expectedCount))",
    "candidate.reviewed !== false",
    "worker.exec({",
):
    assert marker in service, marker
for marker in (
    'import { randomUUID } from "node:crypto";',
    'attachEvidence, validInvestigation, validEvidence',
    'prepareCandidateAttachDraft, CandidateRefusal',
    'request.action!=="append-to-memory"',
    'request.revision!==0',
    'request.scratchCase.id.startsWith("scratch_")',
    'request.edits.url!==canonical.url',
    'request.prepared.fields.source!=="manual"',
    'request.prepared.fields.reviewed!==false',
    'request.scratchCase.evidence.some(e=>e.url===url)',
    'updated=attachEvidence(',
    'schemaVersion:1,memoryOnly:true,persisted:false',
    'process.argv.length!==2',
):
    assert marker in bridge,marker
for forbidden in ("from \"node:fs\"", "from \"node:net\"",
                  "from \"node:http\"", "from \"node:https\"",
                  "fetch(", "writeFile", "mkdirSync", "openSync",
                  "FinanceResearchWriteAttempt"):
    assert forbidden not in bridge,forbidden
assert "export function attachEvidence(" in model
assert not (root/"services/finance/qmldir").exists()
print("Finance Research M9b multi-SEC scratch in-memory and no-writer contract: PASS")
