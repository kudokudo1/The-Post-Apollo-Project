#!/usr/bin/env python3
"""M9a: verify ephemeral Research case creation never gains writer authority."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceResearchInvestigationsPane.qml").read_text()
host=(root/"widgets/FinanceResearchEvidenceCandidatePreviewHost.qml").read_text()
bridge=(root/"scripts/finance/research_candidate_draft_preview.mjs").read_text()

for marker in (
    "property bool scratchEnabled: false",
    'property string scratchId: ""',
    "readonly property bool canCreateScratch:",
    "scratchEnabled && controllerConnected",
    "signal createScratchRequested(string title, string question)",
    "signal discardScratchRequested()",
    'label: pane.scratchEnabled ? "CREATE SCRATCH" : "CREATE CASE"',
    'pane.createScratchRequested(',
    'pane.createRequested(',
    'label: "DISCARD SCRATCH"',
    'pane.discardScratchRequested()',
    '"SCRATCH INVESTIGATION // MEMORY ONLY"',
    '"INVESTIGATIONS // SCRATCH UNSAVED"',
    '"[UNSAVED] " + modelData.title',
    "onTextEdited: pane.draftTitle = text",
    "onTextChanged: if (activeFocus) pane.draftQuestion = text",
    "available: pane.canAttach",
    "controllerConnected && writeEnabled && loadState === \"ready\"",
    "MEMORY ONLY // BACK OR LEAVING RESEARCH DISCARDS SCRATCH AND DRAFT",
):
    assert marker in pane, marker
for marker in (
    "property var scratchCase: null",
    "readonly property bool scratchSelected:",
    "readonly property int selectedRevision: scratchSelected ? 0",
    "function createScratch(title, question)",
    "function discardScratch()",
    "function closeReview()",
    "discardScratch();",
    "schemaVersion: 1, id: id, title: title, question: question,",
    "createdAt: timestamp, updatedAt: timestamp, evidence: []",
    'const timestamp = new Date().toISOString();',
    'const id = "scratch_"',
    'readService.investigations.length >= 50',
    'title.length < 1 || title.length > 160',
    'question.length < 1 || question.length > 1000',
    "scratchCase = item;",
    "caseEditor.selectedId = id;",
    "readService.investigations.concat([host.scratchCase])",
    "scratchEnabled: true",
    "writeEnabled: false",
    "onCreateScratchRequested: function(title, question)",
    "onDiscardScratchRequested: host.discardScratch()",
    "(!scratchSelected && readService.state !== \"ready\")",
    "data.caseRevision !== selectedRevision",
    "draftService.prepare(reviewCandidate,",
    "caseEditor.selectedInvestigation,selectedRevision",
    'statusMessage: host.scratchCase !== null',
    "function onCandidatePreviewChanged()",
    "if (!active) closeReview();"
):
    assert marker in host,marker
# Old write callbacks remain unconnected, regardless of scratch availability.
for forbidden in (
    "onCreateRequested:", "onAttachRequested:", "onRemoveRequested:",
    "writeEnabled: true", "FinanceResearchWriteAttempt",
    "FinanceResearchInvestigationWriteService", "Qt.openUrlExternally",
    "FileView {", "Process {", "worker.exec("
):
    assert forbidden not in host,forbidden
# The pure bridge still creates no executable "action":"attach" result.
assert 'preparedOnly:true' in bridge
assert 'fields:{' in bridge
assert "process.exitCode=1" in bridge
assert '"action":"attach"' not in bridge

# Compact form must not move the discard control into the fixed-width row.
start=pane.index('Row {\n                spacing: 6')
finish=pane.index('Rectangle {\n                width: parent.width\n                height: newForm.',start)
assert 'label: "DISCARD SCRATCH"' in pane[start:finish]
assert pane.index('label: "DISCARD SCRATCH"') > pane.index('text: "CASES "')
print("Finance Research M9a scratch in-memory, editor reuse and hard writer HOLD: PASS")
