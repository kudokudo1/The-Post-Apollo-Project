import QtQuick
import Quickshell
import Quickshell.Io

// SEC M3: no inspection until explicitly clicked. One isolated, read-only
// Python stdlib process against a prevalidated filing in the selected index.
Scope {
    id: detailFeed
    property var secFeed: null
    property bool monitoring: false
    property string state: "idle"
    property string message: "Select a Form 4 or 8-K and press INSPECT."
    property var snapshot: null
    property string desiredKey: ""
    property string inFlightKey: ""
    readonly property bool loading: state === "loading"

    function clear() {
        desiredKey = "";
        snapshot = null;
        state = "idle";
        message = "Select a filing and press INSPECT.";
    }

    onMonitoringChanged: {
        if (!monitoring) clear();
    }

    function inspect(filing) {
        if (!monitoring || !secFeed || !secFeed.snapshot || !filing
                || !Array.isArray(secFeed.snapshot.filings))
            return false;
        if (["4","4/A","8-K","8-K/A"].indexOf(filing.form) < 0)
            return false;
        // Only a filing in the current validated SEC index is a valid target.
        const known = secFeed.snapshot.filings.some(function(row) {
            return row.accession === filing.accession
                && row.form === filing.form
                && row.primaryDocument === filing.primaryDocument;
        });
        if (!known || !/^\d{10}$/.test(secFeed.snapshot.cik)
                || !/^\d{10}-\d{2}-\d{6}$/.test(filing.accession)
                || typeof filing.primaryDocument !== "string"
                || !/^(?:xslF345X\d{2}\/)?[A-Za-z0-9][A-Za-z0-9_.-]{0,170}$/.test(filing.primaryDocument))
            return false;

        if (reader.running) {
            snapshot = null;
            state = "busy";
            message = "Prior inspection still running; retry when it finishes.";
            return false;
        }
        const key = secFeed.snapshot.cik + "/" + filing.accession;
        desiredKey = key;
        inFlightKey = key;
        snapshot = null;
        state = "loading";
        message = "Inspecting original SEC filing.";
        reader.exec(["/usr/bin/env", "python3",
                     Quickshell.shellPath("scripts/finance/inspect_sec_document.py"),
                     secFeed.snapshot.cik, filing.accession, filing.form,
                     filing.primaryDocument, Array.isArray(filing.items)
                         ? filing.items.join(",") : ""]);
        return true;
    }

    function acceptOutput(raw) {
        if (desiredKey !== inFlightKey) return;
        const lines = String(raw || "").split(/\r?\n/);
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.indexOf("FINANCE_SEC_DETAIL_ERROR ") === 0) {
                snapshot = null;
                state = "failed";
                message = line.indexOf("no-supported-transactions") >= 0
                    ? "NO SUPPORTED NON-DERIVATIVE TRANSACTIONS // REVIEW ORIGINAL"
                    : "SEC DOCUMENT UNAVAILABLE OR UNSUPPORTED // REVIEW ORIGINAL";
                return;
            }
            if (line.indexOf("FINANCE_SEC_DETAIL ") !== 0) continue;
            try {
                const data = JSON.parse(line.slice("FINANCE_SEC_DETAIL ".length));
                if (!data || data.schemaVersion !== 1
                    || data.source !== "sec-edgar-document" || data.readOnly !== true
                    || !secFeed || !secFeed.snapshot
                    || data.cik !== secFeed.snapshot.cik
                    || data.cik + "/" + data.accession !== desiredKey
                    || (data.kind !== "form4" && data.kind !== "form8k")
                    || typeof data.documentUrl !== "string"
                    || data.documentUrl.indexOf("https://www.sec.gov/Archives/edgar/data/") !== 0
                    || (data.kind === "form4" && (!Array.isArray(data.transactions)
                        || data.transactions.length > 20 || !Array.isArray(data.owners)
                        || data.owners.length > 8))
                    || (data.kind === "form8k" && (!Array.isArray(data.events)
                        || data.events.length > 12)))
                    throw new Error("invalid-detail");
                snapshot = data;
                state = "ready";
                message = data.kind === "form4"
                    ? "FORM 4 NON-DERIVATIVE TRANSACTIONS // ORIGINAL SEC XML"
                    : "8-K REPORTED ITEMS // ORIGINAL SEC DOCUMENT";
            } catch (error) {
                snapshot = null;
                state = "failed";
                message = "Could not validate document detail.";
            }
            return;
        }
    }

    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: detailFeed.acceptOutput(text)
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                if (detailFeed.state === "loading") {
                    detailFeed.snapshot = null;
                    detailFeed.state = "failed";
                    detailFeed.message = "SEC document inspection failed.";
                }
            });
        }
    }
}
