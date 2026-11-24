import QtQuick
import "../components"
import "../services/finance" as FinanceServices

// Research M7: isolated source-preview composition, NOT mounted in FinanceW.
// The existing FinanceW SEC and Crawl readers are passed in by the owner.
// No new provider actor, no investigation writer and no live menu changes.
Item {
    id: host
    property bool active: false
    property var secFeed: null
    property var crawlFeed: null
    property bool reviewOpen: false
    property string reviewKey: ""
    property var scratchCase: null // volatile QML memory; never persisted
    property int scratchCounter: 0
    readonly property bool scratchSelected: scratchCase !== null
        && caseEditor.selectedId === scratchCase.id
    readonly property int selectedRevision: scratchSelected ? 0
        : readService.revision

    readonly property var reviewCandidate: {
        const rows = previewService.candidatePreview
            && previewService.candidatePreview.candidates;
        if (!Array.isArray(rows)) return null;
        for (let i = 0; i < rows.length; i++) {
            if (rows[i].key === reviewKey && rows[i].kind === "sec-index")
                return rows[i];
        }
        return null;
    }
    readonly property string draftState: draftService.state
    readonly property string draftMessage: draftService.message
    readonly property var draftResult: draftService.preparedDraft
    readonly property string caseReadState: readService.state
    readonly property string editorCaseId: caseEditor.selectedId
    readonly property string editorDraftTitle: caseEditor.draftEvidenceTitle
    readonly property string editorDraftUrl: caseEditor.draftEvidenceUrl
    readonly property string editorDraftSummary: caseEditor.draftEvidenceSummary
    readonly property bool writerEnabled: caseEditor.writeEnabled
    readonly property string scratchCaseId: scratchCase ? scratchCase.id : ""
    readonly property string scratchTitle: scratchCase ? scratchCase.title : ""
    readonly property string scratchQuestion: scratchCase ? scratchCase.question : ""
    readonly property int scratchEvidenceCount: scratchCase ? scratchCase.evidence.length : 0
    readonly property string appendState: scratchEvidenceService.state
    readonly property string appendMessage: scratchEvidenceService.message
    readonly property bool scratchAppendReady: active && reviewOpen
        && scratchSelected && reviewCandidate !== null
        && draftService.state === "ready"
        && draftService.preparedDraft !== null
        && draftService.preparedDraft.candidateKey === reviewKey
        && draftService.preparedDraft.investigationId === scratchCaseId
        && draftService.preparedDraft.fields.url === reviewCandidate.url
        && caseEditor.draftEvidenceUrl === reviewCandidate.url
        && caseEditor.draftEvidenceTitle.length > 0
        && caseEditor.draftEvidenceTitle.trim() === caseEditor.draftEvidenceTitle
        && caseEditor.draftEvidenceTitle.length <= 160
        && caseEditor.draftEvidenceSummary.length > 0
        && caseEditor.draftEvidenceSummary.trim() === caseEditor.draftEvidenceSummary
        && caseEditor.draftEvidenceSummary.length <= 2000
        && scratchEvidenceCount < 40
        && !scratchCase.evidence.some(function(e) {
            return e.url === caseEditor.draftEvidenceUrl;
        })
        && !scratchEvidenceService.loading

    function loadCases() { return readService.load(); }
    function pickNextFiling() {
        if (!active || !reviewOpen || !scratchSelected
                || scratchEvidenceService.loading)
            return false;
        // Navigation within the SAME immutable source preview preserves
        // the scratch case, unlike BACK (which deliberately discards it).
        draftService.clear();
        scratchEvidenceService.clear();
        resetEditorDraft();
        reviewKey = "";
        reviewOpen = false;
        return true;
    }
    function addToScratch(title, summary, url) {
        if (!scratchAppendReady || title !== caseEditor.draftEvidenceTitle
                || summary !== caseEditor.draftEvidenceSummary
                || url !== caseEditor.draftEvidenceUrl)
            return false;
        return scratchEvidenceService.append(
            reviewCandidate,draftService.preparedDraft,scratchCase,
            {title: title,summary: summary,url: url});
    }
    function applyAppendedCase(data) {
        if (!active || !reviewOpen || !scratchSelected || !data
                || data.memoryOnly !== true || data.persisted !== false
                || data.caseRevision !== 0 || data.candidateKey !== reviewKey
                || data.scratchCase.id !== scratchCaseId
                || data.previousCount !== scratchEvidenceCount
                || data.scratchCase.evidence.length !== scratchEvidenceCount + 1)
            return;
        scratchCase = data.scratchCase;
        draftService.clear();
        resetEditorDraft();
    }

    function discardScratch() {
        scratchEvidenceService.clear();
        if (scratchCase === null) return;
        draftService.clear();
        resetEditorDraft();
        scratchCase = null;
        caseEditor.draftTitle = "";
        caseEditor.draftQuestion = "";
        caseEditor.showNewForm = false;
    }
    function createScratch(title, question) {
        if (!active || !reviewOpen || reviewCandidate === null
                || scratchCase !== null
                || typeof title !== "string" || typeof question !== "string"
                || title !== title.trim() || question !== question.trim()
                || title.length < 1 || title.length > 160
                || question.length < 1 || question.length > 1000
                || readService.investigations.length >= 50)
            return false;
        const timestamp = new Date().toISOString();
        scratchCounter++;
        const id = "scratch_" + Date.now().toString(36)
            + "_" + scratchCounter.toString(36);
        if (readService.investigations.some(function(item) {
            return item.id === id;
        })) return false;
        // Identical, bounded M1 investigation shape, but QML-owned only.
        const item = {
            schemaVersion: 1, id: id, title: title, question: question,
            createdAt: timestamp, updatedAt: timestamp, evidence: []
        };
        scratchCase = item;
        scratchEvidenceService.clear();
        caseEditor.selectedId = id;
        caseEditor.showNewForm = false;
        caseEditor.draftTitle = "";
        caseEditor.draftQuestion = "";
        draftService.clear();
        resetEditorDraft();
        return true;
    }

    function resetEditorDraft() {
        caseEditor.draftSource = "manual";
        caseEditor.draftEvidenceTitle = "";
        caseEditor.draftEvidenceSummary = "";
        caseEditor.draftEvidenceUrl = "";
    }
    function closeReview() {
        reviewOpen = false;
        reviewKey = "";
        discardScratch();
        draftService.clear();
        resetEditorDraft();
    }
    function beginReview(key) {
        if (!active || previewService.state !== "ready"
                || typeof key !== "string")
            return false;
        const rows = previewService.candidatePreview
            && previewService.candidatePreview.candidates;
        if (!Array.isArray(rows))
            return false;
        const candidate = rows.find(function(item) {
            return item.key === key && item.kind === "sec-index"
                && item.eligibleForDraft === true
                && item.reviewed === false
                && item.authenticatedProvenance === false;
        });
        if (!candidate) return false;
        // Reopening another filing through PICK NEXT retains the scratch.
        // Ordinary entry without scratch still follows the old close path.
        if (scratchCase !== null && !reviewOpen) {
            draftService.clear();
            scratchEvidenceService.clear();
            resetEditorDraft();
        } else {
            closeReview();
        }
        reviewKey = key;
        reviewOpen = true;
        if (scratchCase !== null)
            caseEditor.selectedId = scratchCase.id;
        return true;
    }
    function prepareDraft() {
        if (!active || !reviewOpen || !reviewCandidate
                || (!scratchSelected && readService.state !== "ready")
                || !caseEditor.selectedInvestigation)
            return false;
        return draftService.prepare(reviewCandidate,
            caseEditor.selectedInvestigation,selectedRevision);
    }
    function applyPreparedDraft(data) {
        if (!active || !reviewOpen || !reviewCandidate || !data
                || (!scratchSelected && readService.state !== "ready")
                || data.investigationId !== caseEditor.selectedId
                || data.caseRevision !== selectedRevision
                || data.candidateKey !== reviewKey
                || !data.fields || data.fields.url !== reviewCandidate.url
                || data.fields.source !== "manual" || data.fields.reviewed !== false)
            return;
        caseEditor.draftSource = "manual";
        caseEditor.draftEvidenceTitle = data.fields.title;
        caseEditor.draftEvidenceSummary = data.fields.summary;
        caseEditor.draftEvidenceUrl = data.fields.url;
    }
    onActiveChanged: {
        if (!active) closeReview();
    }

    // Read-only host API for isolated native acceptance and future Finance UI.
    readonly property string previewState: previewService.state
    readonly property string previewMessage: previewService.message
    readonly property var previewResult: previewService.candidatePreview
    function buildPreview() { return previewService.refresh(); }

    FinanceServices.FinanceResearchCandidatePreviewService {
        id: previewService
        monitoring: host.active
        secFeed: host.secFeed
        crawlFeed: host.crawlFeed
    }

    // Reuse M4's existing local investigations reader and M3 editor.
    // Reading cases is explicit (LOAD CASES), not automatic.
    FinanceServices.FinanceResearchInvestigationReadService {
        id: readService
        monitoring: host.active && host.reviewOpen
    }
    FinanceServices.FinanceResearchCandidateDraftService {
        id: draftService
        monitoring: host.active && host.reviewOpen
        onPreparedDraftChanged: host.applyPreparedDraft(preparedDraft)
    }
    FinanceServices.FinanceResearchScratchEvidenceService {
        id: scratchEvidenceService
        monitoring: host.active && host.reviewOpen
        onResultChanged: host.applyAppendedCase(result)
    }
    Connections {
        target: previewService
        function onCandidatePreviewChanged() {
            // Includes hidden PICK NEXT state. If source/issuer changes,
            // discard scratch rather than carrying citations across sources.
            if (host.reviewOpen || host.scratchCase !== null)
                host.closeReview();
        }
    }
    Connections {
        target: readService
        function onRevisionChanged() {
            draftService.clear();
            scratchEvidenceService.clear();
            host.resetEditorDraft();
        }
    }

    Connections {
        target: host.secFeed
        ignoreUnknownSignals: true
        function onSnapshotChanged() { previewService.clear(); }
        function onSelectedCikChanged() { previewService.clear(); }
        function onStateChanged() { previewService.clear(); }
    }
    Connections {
        target: host.crawlFeed
        ignoreUnknownSignals: true
        function onSnapshotChanged() { previewService.clear(); }
        function onStateChanged() { previewService.clear(); }
    }

    FinanceResearchEvidenceCandidatePicker {
        id: picker
        anchors.fill: parent
        visible: !host.reviewOpen
        enabled: visible
        controllerConnected: host.active
        candidatePreview: previewService.candidatePreview
        loadState: previewService.state
        statusMessage: previewService.message
        onPreviewRequested: previewService.refresh()
        onReviewRequested: function(candidateKey) {
            host.beginReview(candidateKey);
        }
    }

    // The original Research case editor is reused, not copied. The attach,
    // create and remove signals are intentionally NEVER connected to a writer.
    // Selecting a case then PREPARE fills only its local TextInput fields.
    Column {
        id: reviewToolbar
        visible: host.reviewOpen
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        spacing: 5
        Row {
            id: reviewActions
            width: parent.width
            spacing: 6
            readonly property real availableWidth: Math.max(0, width - spacing)
            ActionButton {
                width: Math.min(100, Math.floor(
                    reviewActions.availableWidth * (host.scratchSelected
                        ? 0.32 : 0.34)))
                height: 29
                label: "BACK"
                labelPixelSize: 10
                onLeftClicked: host.closeReview()
            }
            ActionButton {
                width: Math.min(120, Math.floor(
                    reviewActions.availableWidth * 0.25))
                height: 29
                label: "PICK NEXT"
                labelPixelSize: 9
                accentColor: Colors.cyan
                visible: host.scratchSelected
                available: visible && !scratchEvidenceService.loading
                onLeftClicked: host.pickNextFiling()
            }
            ActionButton {
                width: Math.min(172, Math.floor(
                    reviewActions.availableWidth * (host.scratchSelected
                        ? 0.41 : 0.66)))
                height: 29
                label: host.width < 430 ? "PREPARE" : "PREPARE UNSAVED"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: host.active && host.reviewCandidate !== null
                    && (host.scratchSelected
                        || readService.state === "ready")
                    && caseEditor.selectedInvestigation !== null
                    && !draftService.loading
                onLeftClicked: host.prepareDraft()
            }
        }
        GohuText {
            width: parent.width
            font.pixelSize: 9
            color: draftService.state === "failed" ? Colors.red : Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
            text: "SEC INDEX // CONTENT NOT INSPECTED // "
                  + (scratchEvidenceService.state === "failed"
                     || scratchEvidenceService.state === "loading"
                     || scratchEvidenceService.state === "ready"
                     ? scratchEvidenceService.message
                     : draftService.message)
        }
    }

    FinanceResearchInvestigationsPane {
        id: caseEditor
        visible: host.reviewOpen
        enabled: visible
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: reviewToolbar.bottom
        anchors.bottom: parent.bottom
        anchors.topMargin: 4
        controllerConnected: host.active && host.reviewOpen
        writeEnabled: false // HARD HOLD: no M2 writer authorization
        scratchEnabled: true
        scratchId: host.scratchCaseId
        loadState: readService.state
        statusMessage: host.scratchCase !== null
            && readService.state !== "failed"
            ? "SCRATCH CASE // MEMORY ONLY // NEVER SAVED"
            : readService.message
        investigations: host.scratchCase
            ? readService.investigations.concat([host.scratchCase])
            : readService.investigations
        onLoadRequested: readService.load()
        onCreateScratchRequested: function(title, question) {
            host.createScratch(title, question);
        }
        onDiscardScratchRequested: host.discardScratch()
        scratchAppendReady: host.scratchAppendReady
        onAppendScratchRequested: function(title, summary, url) {
            host.addToScratch(title, summary, url);
        }
        onSelectedIdChanged: {
            draftService.clear();
            scratchEvidenceService.clear();
        }
    }
}
