import QtQuick
import Quickshell
import "widgets"

// M9a native acceptance: a real Quickshell M9 host with EMPTY local storage.
// SEC data is synthetic, in memory, and never fetched from a provider.
ShellRoot {
    id: root
    property bool requestedPreview: false
    property bool startedReview: false
    property bool createdScratch: false
    property bool prepared: false
    property bool discarded: false
    property bool recreated: false
    property bool complete: false
    property int ticks: 0

    QtObject {
        id: secMock
        property string state: "ready"
        property string selectedCik: "0000320193"
        property var snapshot: ({
            schemaVersion:1,source:"sec-edgar-submissions",
            readOnly:true,cik:"0000320193",issuer:"Apple",
            retrievedAt:"2026-11-23T12:00:00.000Z",
            filings:[{
                accession:"0000320193-26-000111",form:"8-K",
                category:"MATERIAL EVENT",filedAt:"2026-11-20",
                acceptedAt:null,primaryDocument:"index.htm",items:[],
                documentUrl:"https://www.sec.gov/Archives/edgar/data/"
                    +"320193/000032019326000111/index.htm"
            }]
        })
    }
    QtObject {
        id: crawlMock
        property string state: "idle"
        property var snapshot: null
    }

    FloatingWindow {
        id: window
        title: "M9A-RESEARCH-SCRATCH-NATIVE"
        visible: true
        width: 420
        height: 650
        color: "#110516"
        FinanceResearchEvidenceCandidatePreviewHost {
            id: host
            anchors.fill: parent
            active: true
            secFeed: secMock
            crawlFeed: crawlMock
        }
    }

    function fail(code) {
        if (complete) return;
        complete = true;
        console.error("M9A_NATIVE_FAIL // " + code);
        Qt.quit();
    }
    function pass() {
        if (complete) return;
        complete = true;
        console.log("M9A_NATIVE_PASS // EMPTY_STORE_SCRATCH_AND_DRAFT");
        Qt.quit();
    }

    Timer {
        interval: 80
        repeat: true
        running: !root.complete
        onTriggered: {
            root.ticks++;
            if (root.ticks > 170) {
                root.fail("TIMEOUT // " + host.previewState
                    + " // " + host.draftState);
                return;
            }
            if (!root.requestedPreview) {
                root.requestedPreview = true;
                if (!host.buildPreview())
                    root.fail("BUILD_PREVIEW_REFUSED");
                return;
            }
            if (host.previewState === "failed") {
                root.fail("PREVIEW_FAILED");
                return;
            }
            if (!root.startedReview && host.previewState === "ready") {
                if (!host.previewResult
                        || host.previewResult.counts.sec !== 1) {
                    root.fail("NO_SEC_CANDIDATE");
                    return;
                }
                root.startedReview =
                    host.beginReview(host.previewResult.candidates[0].key);
                if (!root.startedReview)
                    root.fail("REVIEW_UNAVAILABLE");
                return;
            }
            if (root.startedReview && !root.createdScratch) {
                if (host.caseReadState !== "idle") {
                    root.fail("UNEXPECTED_CASE_READ");
                    return;
                }
                root.createdScratch = host.createScratch(
                    "Synthetic unsaved analysis",
                    "What does the listed 8-K index record describe?");
                if (!root.createdScratch
                        || host.scratchCaseId.length === 0
                        || host.editorCaseId !== host.scratchCaseId
                        || host.scratchTitle !== "Synthetic unsaved analysis"
                        || !host.scratchQuestion
                        || host.writerEnabled) {
                    root.fail("SCRATCH_CREATION_OR_HARD_HOLD_FAILED");
                    return;
                }
                console.log("M9A_NATIVE_CHECK // CASE_CREATED_WITH_NO_STORED_CASES");
                if (host.createScratch("Duplicate scratch","No"))
                    root.fail("DUPLICATE_SCRATCH_ALLOWED");
                if (!host.prepareDraft())
                    root.fail("SCRATCH_DRAFT_DISPATCH_REFUSED");
                return;
            }
            if (root.createdScratch && !root.prepared) {
                if (host.draftState === "failed") {
                    root.fail("DRAFT_FAILED // " + host.draftMessage);
                    return;
                }
                if (host.draftState === "ready") {
                    const data = host.draftResult;
                    if (!data || !data.readOnly || !data.preparedOnly
                            || data.investigationId !== host.scratchCaseId
                            || data.caseRevision !== 0
                            || data.fields.source !== "manual"
                            || data.fields.reviewed !== false
                            || data.fields.title !== host.editorDraftTitle
                            || data.fields.summary !== host.editorDraftSummary
                            || data.fields.url !== host.editorDraftUrl
                            || host.writerEnabled) {
                        root.fail("SCRATCH_DRAFT_PREFILL_INVALID");
                        return;
                    }
                    root.prepared = true;
                    console.log("M9A_NATIVE_CHECK // UNSAVED_SEC_CITATION_PREFILLED");
                    host.discardScratch();
                    return;
                }
            }
            if (root.prepared && !root.discarded) {
                if (host.scratchCaseId !== ""
                        || host.draftResult !== null
                        || host.editorDraftUrl !== ""
                        || host.editorDraftTitle !== ""
                        || host.editorCaseId !== "") {
                    root.fail("DISCARD_DID_NOT_CLEAR_VOLATILE_DATA");
                    return;
                }
                root.discarded = true;
                console.log("M9A_NATIVE_CHECK // SCRATCH_DISCARD_CLEARED");
                return;
            }
            if (root.discarded && !root.recreated) {
                root.recreated = host.createScratch(
                    "Second scratch", "Does an issuer change clear this?");
                if (!root.recreated) {
                    root.fail("SCRATCH_RECREATE_REFUSED");
                    return;
                }
                secMock.selectedCik = "0000789019";
                return;
            }
            if (root.recreated && host.previewState === "idle") {
                if (host.reviewOpen || host.scratchCaseId !== ""
                        || host.draftResult !== null || host.editorDraftUrl !== ""
                        || host.writerEnabled) {
                    root.fail("SOURCE_CHANGE_LEFT_STALE_SCRATCH");
                    return;
                }
                console.log("M9A_NATIVE_CHECK // SOURCE_CHANGE_DISCARDED_SCRATCH");
                root.pass();
            }
        }
    }
}
