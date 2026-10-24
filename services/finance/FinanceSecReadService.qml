import QtQuick
import Quickshell
import Quickshell.Io

// Official SEC/EDGAR issuer submissions. No trading or crawling process.
// Only SEC user-agent contact is read by the Node child; never exposed to QML.
Scope {
    id: secFeed
    property bool monitoring: false
    property string selectedCik: "0000320193"
    property string inFlightCik: ""
    property bool pendingRefresh: false
    property string state: "idle"
    property string message: "Select an issuer or press REFRESH."
    property var snapshot: null
    readonly property bool loading: state === "loading"

    onMonitoringChanged: {
        if (monitoring && state === "idle")
            refresh();
    }

    function selectIssuer(cik) {
        if (["0000320193", "0000789019", "0001045810"].indexOf(cik) < 0)
            return false;
        if (selectedCik === cik) return true;
        selectedCik = cik;
        snapshot = null;
        state = "idle";
        message = "Issuer changed. No previous issuer data shown.";
        if (monitoring)
            refresh();
        return true;
    }

    function refresh() {
        if (!monitoring) return false;
        if (reader.running) {
            pendingRefresh = selectedCik !== inFlightCik;
            snapshot = null;
            state = "loading";
            message = "Waiting for prior issuer request.";
            return false;
        }
        pendingRefresh = false;
        inFlightCik = selectedCik;
        snapshot = null;
        state = "loading";
        message = "Reading public SEC submissions.";
        reader.exec(["/usr/bin/env", "node",
                     Quickshell.shellPath("scripts/finance/read_sec_filings.mjs"),
                     selectedCik]);
        return true;
    }

    function acceptOutput(raw) {
        if (selectedCik !== inFlightCik) return;  // stale issuer response
        const lines = String(raw || "").split(/\r?\n/);
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.indexOf("FINANCE_SEC_ERROR ") === 0) {
                snapshot = null;
                const reason = line.slice("FINANCE_SEC_ERROR ".length);
                state = reason.indexOf("identity-") === 0 ? "setup" : "failed";
                message = reason.indexOf("identity-") === 0
                    ? "SEC USER-AGENT SETUP REQUIRED // SEE RESEARCH GUIDE"
                    : "SEC FEED UNAVAILABLE // CHECK CONNECTION AND IDENTITY";
                return;
            }
            if (line.indexOf("FINANCE_SEC_SNAPSHOT ") !== 0) continue;
            try {
                const data = JSON.parse(line.slice("FINANCE_SEC_SNAPSHOT ".length));
                if (!data || data.schemaVersion !== 1
                        || data.source !== "sec-edgar-submissions"
                        || data.readOnly !== true || data.cik !== selectedCik
                        || typeof data.issuer !== "string"
                        || typeof data.retrievedAt !== "string"
                        || !Array.isArray(data.filings) || data.filings.length > 30
                        || !data.filings.every(function(f) {
                            return f && typeof f.accession === "string"
                              && /^\d{10}-\d{2}-\d{6}$/.test(f.accession)
                              && ["8-K","8-K/A","4","4/A","SC 13D","SC 13D/A",
                                  "SC 13G","SC 13G/A","10-Q","10-Q/A",
                                  "10-K","10-K/A"].indexOf(f.form) >= 0
                              && typeof f.filedAt === "string"
                              && /^\d{4}-\d{2}-\d{2}$/.test(f.filedAt)
                              && typeof f.category === "string"
                              && typeof f.primaryDocument === "string"
                              && /^(?:xslF345X\d{2}\/)?[A-Za-z0-9][A-Za-z0-9_.-]{0,170}$/.test(f.primaryDocument)
                              && Array.isArray(f.items) && f.items.length <= 12
                              && f.items.every(function(item) {
                                  return typeof item === "string" && /^[1-9]\.\d{2}$/.test(item);
                              })
                              && typeof f.documentUrl === "string"
                              && f.documentUrl.indexOf("https://www.sec.gov/Archives/edgar/data/") === 0
                              && (f.acceptedAt === null || typeof f.acceptedAt === "string");
                        }))
                    throw new Error("invalid snapshot");
                snapshot = data;
                state = "ready";
                message = data.filings.length
                    ? "SEC SUBMISSIONS SNAPSHOT // READ ONLY"
                    : "NO SELECTED FORMS IN RECENT SUBMISSIONS";
            } catch (error) {
                snapshot = null;
                state = "failed";
                message = "Could not validate SEC submissions.";
            }
            return;
        }
    }

    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: secFeed.acceptOutput(text)
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                if (secFeed.pendingRefresh && secFeed.monitoring) {
                    secFeed.pendingRefresh = false;
                    secFeed.state = "idle";
                    secFeed.refresh();
                } else if (secFeed.state === "loading") {
                    secFeed.snapshot = null;
                    secFeed.state = "failed";
                    secFeed.message = "SEC read failed; select REFRESH to retry.";
                }
            });
        }
    }
}
