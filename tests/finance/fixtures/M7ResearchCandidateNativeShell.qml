import QtQuick
import Quickshell
import "widgets"

// Real, isolated Quickshell startup and read-only IPC smoke fixture.
// All records are synthetic; no provider, user storage or live FinanceW.
ShellRoot {
    id: root
    property bool sent: false
    property bool checkedReady: false
    property bool submittedInvalidSource: false
    property bool finished: false
    property int ticks: 0

    QtObject {
        id: secMock
        property string state: "ready"
        property string selectedCik: "0000320193"
        property var snapshot: ({
            schemaVersion: 1,
            source: "sec-edgar-submissions",
            readOnly: true,
            cik: "0000320193",
            issuer: "Apple",
            retrievedAt: "2026-11-23T12:00:00.000Z",
            filings: [{
                accession: "0000320193-26-000111",
                form: "8-K",
                category: "MATERIAL EVENT",
                filedAt: "2026-11-20",
                acceptedAt: null,
                primaryDocument: "index.htm",
                items: [],
                documentUrl: "https://www.sec.gov/Archives/edgar/data/"
                    + "320193/000032019326000111/index.htm"
            }]
        })
    }
    // A live SEC page can contain 30 records. The original M7 smoke
    // only covered one, missing the operator's populated preview failure.
    Component.onCompleted: {
        const source = secMock.snapshot;
        const filings = source.filings.slice();
        for (let i = 1; i < 30; ++i) {
            const suffix = ("000000" + (111 + i)).slice(-6);
            const accession = "0000320193-26-" + suffix;
            const form4 = i % 3 === 0;
            const document = form4
                ? "xslF345X05/wk-form4-" + suffix + ".xml" : "index.htm";
            filings.push({
                accession: accession,
                form: form4 ? "4" : "8-K",
                category: form4 ? "INSIDER DISCLOSURE" : "MATERIAL EVENT",
                filedAt: "2026-11-20",
                acceptedAt: null,
                primaryDocument: document,
                items: [],
                documentUrl: "https://www.sec.gov/Archives/edgar/data/"
                    + "320193/" + accession.replace(/-/g, "") + "/" + document
            });
        }
        secMock.snapshot = Object.assign({}, source, {filings: filings});
    }

    QtObject {
        id: crawlMock
        property string state: "ready"
        property var snapshot: ({
            schemaVersion: 1,
            source: "finance-demo-scrapy",
            readOnly: true,
            status: "snapshot",
            pageCount: 1,
            linkCount: 0,
            pages: [{
                url: "https://quotes.toscrape.com/page/1/",
                title: "Synthetic demo page",
                // Real Scrapy emits this microsecond/UTC-offset format.
                observedAt: "2026-11-23T14:42:00.123456+00:00",
                snippet: "Synthetic demonstration data",
                links: []
            }]
        })
    }

    FloatingWindow {
        id: window
        title: "M7-RESEARCH-NATIVE-SMOKE"
        visible: true
        width: 680
        height: 720
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
        console.error("M7_NATIVE_FAIL // " + reason);
        Qt.quit();
    }
    function pass() {
        if (finished) return;
        finished = true;
        console.log("M7_NATIVE_PASS // QML_TYPES_AND_READ_ONLY_IPC");
        Qt.quit();
    }

    Timer {
        interval: 75
        repeat: true
        running: !root.finished
        onTriggered: {
            root.ticks++;
            if (root.ticks > 200) {
                root.fail("TIMED_OUT // state=" + host.previewState);
                return;
            }
            if (!root.sent) {
                root.sent = true;
                if (!host.buildPreview())
                    root.fail("ON_DEMAND_PREVIEW_REFUSED");
                return;
            }
            if (!root.checkedReady && host.previewState === "failed") {
                root.fail("BRIDGE_OR_QML_VALIDATION_FAILED");
                return;
            }
            if (!root.checkedReady && host.previewState === "ready") {
                const data = host.previewResult;
                if (!data || !data.readOnly || !data.counts
                        || data.counts.sec !== 30
                        || data.counts.demo !== 1
                        || data.candidates.length !== 31
                        || data.candidates[0].authenticatedProvenance !== false
                        || data.candidates[30].eligibleForDraft !== false
                        || data.candidates[30].observedAt
                            !== "2026-11-23T14:42:00.123456+00:00") {
                    root.fail("INCOMPLETE_OR_UNSAFE_PREVIEW // SEC=" + (data && data.counts ? data.counts.sec : "null") + " / DEMO=" + (data && data.counts ? data.counts.demo : "null") + " / TOTAL=" + (data && data.candidates ? data.candidates.length : "null") + " / INPUT=" + secMock.snapshot.filings.length);
                    return;
                }
                root.checkedReady = true;
                console.log("M7_NATIVE_CHECK // CANDIDATES_FROM_NODE_VALIDATED");
                // Changing the issuer must invalidate a cached Apple preview.
                secMock.selectedCik = "0000789019";
                return;
            }
            if (root.checkedReady && host.previewState === "idle") {
                if (host.previewResult !== null) {
                    root.fail("STALE_SOURCE_PREVIEW_NOT_CLEARED");
                    return;
                }
                if (!root.submittedInvalidSource) {
                    root.submittedInvalidSource = true;
                    if (!host.buildPreview())
                        root.fail("INVALID_SOURCE_PREVIEW_NOT_DISPATCHED");
                    return;
                }
            }
            if (root.submittedInvalidSource
                    && host.previewState === "failed") {
                if (host.previewResult !== null
                        || host.previewMessage !==
                            "PREVIEW REFUSED // INVALID_SEC_SNAPSHOT") {
                    root.fail("UNSAFE_OR_AMBIGUOUS_FAILURE // "
                              + host.previewMessage);
                    return;
                }
                console.log("M7_NATIVE_CHECK // BOUNDED_FAILURE_CODE");
                root.pass();
            }
        }
    }
}
