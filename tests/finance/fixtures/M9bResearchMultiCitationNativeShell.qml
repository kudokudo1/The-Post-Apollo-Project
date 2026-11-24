import QtQuick
import Quickshell
import "widgets"

// M9b: actual Quickshell, two SEC citations in one memory-only scratch case.
ShellRoot {
    id: root
    property int step: 0
    property int ticks: 0
    property bool finished: false
    property string caseId: ""
    property string firstKey: ""
    property string secondKey: ""

    QtObject {
        id: secMock
        property string state: "ready"
        property string selectedCik: "0000320193"
        property var snapshot: ({
            schemaVersion:1,source:"sec-edgar-submissions",readOnly:true,
            cik:"0000320193",issuer:"Apple",
            retrievedAt:"2026-11-24T12:00:00.000Z",
            filings:[
                {
                    accession:"0000320193-26-000111",
                    form:"8-K",category:"MATERIAL EVENT",filedAt:"2026-11-20",
                    acceptedAt:null,primaryDocument:"index.htm",items:[],
                    documentUrl:"https://www.sec.gov/Archives/edgar/data/"
                        +"320193/000032019326000111/index.htm"
                },
                {
                    accession:"0000320193-26-000112",
                    form:"4",category:"INSIDER DISCLOSURE",filedAt:"2026-11-21",
                    acceptedAt:null,primaryDocument:"form4.xml",items:[],
                    documentUrl:"https://www.sec.gov/Archives/edgar/data/"
                        +"320193/000032019326000112/form4.xml"
                }
            ]
        })
    }
    QtObject {
        id: crawlMock
        property string state: "idle"
        property var snapshot: null
    }
    FloatingWindow {
        id: window
        title: "M9B-RESEARCH-TWO-CITATIONS"
        visible: true
        width: 460
        height: 680
        color: "#110516"
        FinanceResearchEvidenceCandidatePreviewHost {
            id: host
            anchors.fill: parent
            active: true
            secFeed: secMock
            crawlFeed: crawlMock
        }
    }
    function fail(reason) {
        if (finished) return;
        finished = true;
        console.error("M9B_NATIVE_FAIL // " + reason);
        Qt.quit();
    }
    function pass() {
        if (finished) return;
        finished = true;
        console.log("M9B_NATIVE_PASS // TWO_SEC_MEMORY_ONLY_CITATIONS");
        Qt.quit();
    }
    Timer {
        interval: 85
        repeat: true
        running: !root.finished
        onTriggered: {
            root.ticks++;
            if (root.ticks > 230) {
                root.fail("TIMEOUT // STEP=" + root.step
                    + " / DRAFT=" + host.draftState
                    + " / APPEND=" + host.appendState);
                return;
            }
            if (host.previewState === "failed") {
                root.fail("SEC_PREVIEW_FAILED");
                return;
            }
            if (root.step === 0) {
                if (!host.buildPreview())
                    root.fail("BUILD_PREVIEW_REFUSED");
                root.step=1;
                return;
            }
            if (root.step === 1 && host.previewState === "ready") {
                if (!host.previewResult || host.previewResult.counts.sec !== 2
                        || host.previewResult.candidates.length !== 2) {
                    root.fail("TWO_SEC_CANDIDATES_ABSENT");
                    return;
                }
                root.firstKey=host.previewResult.candidates[0].key;
                root.secondKey=host.previewResult.candidates[1].key;
                if (!host.beginReview(root.firstKey)
                        || !host.createScratch("Two source notes",
                            "Which metadata is listed for each filing?")) {
                    root.fail("FIRST_REVIEW_OR_SCRATCH_REFUSED");
                    return;
                }
                root.caseId=host.scratchCaseId;
                if (!root.caseId || host.writerEnabled || host.caseReadState!=="idle")
                    root.fail("UNEXPECTED_WRITER_OR_CASE_READ");
                if (!host.prepareDraft())
                    root.fail("FIRST_DRAFT_REFUSED");
                root.step=2;
                return;
            }
            if (root.step === 2 && host.draftState === "failed") {
                root.fail("FIRST_DRAFT_FAILED // " + host.draftMessage);
                return;
            }
            if (root.step === 2 && host.draftState === "ready") {
                if (!host.scratchAppendReady
                        || !host.addToScratch(
                            "First SEC filing index note",
                            "Filing metadata only; content not inspected.",
                            host.editorDraftUrl)) {
                    root.fail("FIRST_APPEND_REFUSED");
                    return;
                }
                root.step=3;
                return;
            }
            if (root.step === 3 && host.appendState === "failed") {
                root.fail("FIRST_APPEND_FAILED // " + host.appendMessage);
                return;
            }
            if (root.step === 3 && host.scratchEvidenceCount === 1) {
                if (host.writerEnabled
                        || host.scratchCaseId !== root.caseId
                        || host.scratchCase.evidence[0].title
                            !== "First SEC filing index note"
                        || host.scratchCase.evidence[0].reviewed !== false
                        || host.scratchCase.evidence[0].source !== "manual"
                        || host.editorDraftUrl !== ""
                        || host.draftResult !== null) {
                    root.fail("FIRST_MEMORY_APPEND_INVALID");
                    return;
                }
                console.log("M9B_NATIVE_CHECK // FIRST_CITATION_ONLY_IN_MEMORY");
                if (!host.pickNextFiling()
                        || host.reviewOpen
                        || host.scratchCaseId !== root.caseId
                        || host.scratchEvidenceCount !== 1
                        || !host.beginReview(root.secondKey)
                        || host.editorCaseId !== root.caseId
                        || !host.prepareDraft()) {
                    root.fail("PICK_NEXT_DID_NOT_PRESERVE_CASE");
                    return;
                }
                root.step=4;
                return;
            }
            if (root.step === 4 && host.draftState === "failed") {
                root.fail("SECOND_DRAFT_FAILED // " + host.draftMessage);
                return;
            }
            if (root.step === 4 && host.draftState === "ready") {
                if (!host.scratchAppendReady
                        || !host.addToScratch(
                            host.editorDraftTitle,
                            host.editorDraftSummary,
                            host.editorDraftUrl)) {
                    root.fail("SECOND_APPEND_REFUSED");
                    return;
                }
                root.step=5;
                return;
            }
            if (root.step === 5 && host.appendState === "failed") {
                root.fail("SECOND_APPEND_FAILED // " + host.appendMessage);
                return;
            }
            if (root.step === 5 && host.scratchEvidenceCount === 2) {
                const evidence=host.scratchCase.evidence;
                if (!evidence || evidence.length!==2
                        || evidence[0].url===evidence[1].url
                        || evidence[0].id===evidence[1].id
                        || evidence[0].title!=="First SEC filing index note"
                        || evidence[0].reviewed!==false
                        || evidence[1].reviewed!==false
                        || host.writerEnabled || host.scratchCaseId!==root.caseId) {
                    root.fail("TWO_UNSAVED_REFERENCES_INVALID");
                    return;
                }
                console.log("M9B_NATIVE_CHECK // TWO_SEC_CITATIONS_ONE_SCRATCH");
                if (!host.prepareDraft()) {
                    root.fail("DUPLICATE_PREPARE_NOT_STARTED");
                    return;
                }
                root.step=6;
                return;
            }
            if (root.step === 6 && host.draftState === "failed") {
                if (host.draftMessage
                        !== "DRAFT REFUSED // CANDIDATE_REVIEW_REQUIRED"
                        || host.scratchEvidenceCount!==2
                        || host.writerEnabled) {
                    root.fail("DUPLICATE_REFUSAL_OR_STORAGE_GUARD_FAILED");
                    return;
                }
                console.log("M9B_NATIVE_CHECK // DUPLICATE_SOURCE_REFUSED");
                secMock.selectedCik="0000789019";
                root.step=7;
                return;
            }
            if (root.step === 7 && host.previewState === "idle") {
                if (host.reviewOpen || host.scratchCaseId !== ""
                        || host.scratchEvidenceCount !== 0
                        || host.draftResult !== null
                        || host.editorDraftUrl !== ""
                        || host.writerEnabled) {
                    root.fail("SOURCE_CHANGE_LEFT_SCRATCH_DATA");
                    return;
                }
                console.log("M9B_NATIVE_CHECK // SOURCE_CHANGE_DISCARDED_TWO_CITATIONS");
                root.pass();
            }
        }
    }
}
