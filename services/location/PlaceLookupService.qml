import QtQuick
import Quickshell
import Quickshell.Io
import "PlaceSearchPolicy.js" as SearchPolicy

// M4 explicit city/region/postal-code search. No autosuggest or state writes.
// Free Open-Meteo endpoint is for non-commercial use; commercial deployment
// requires provider licensing or an approved self-hosted adapter.
Scope {
    id: lookup

    property string status: "idle"
    property string errorCode: ""
    property var rows: []
    property string completedQuery: ""
    property string activeQuery: ""
    property string responseText: ""
    property double lastRequestMs: 0

    readonly property bool loading: status === "loading"

    function search(queryText) {
        if (searchProcess.running || loading)
            return false;
        const spec = SearchPolicy.request(queryText);
        if (!spec.ok) {
            errorCode = spec.reason;
            status = "error";
            rows = [];
            return false;
        }
        const nowMs = Date.now();
        if (nowMs < lastRequestMs + 2500) {
            errorCode = "RATE_GUARD";
            status = "error";
            rows = [];
            return false;
        }
        lastRequestMs = nowMs;
        activeQuery = spec.query;
        completedQuery = "";
        responseText = "";
        rows = [];
        errorCode = "";
        status = "loading";
        searchProcess.command = [
            "curl", "-fsSL", "--max-time", "10", "--connect-timeout", "5",
            "--max-redirs", "2", "--max-filesize", "65536",
            spec.url
        ];
        searchProcess.running = true;
        return true;
    }

    function finish(exitCode) {
        if (status !== "loading")
            return;
        if (Number(exitCode) !== 0) {
            errorCode = "REQUEST_FAILED";
            status = "error";
            return;
        }
        const parsed = SearchPolicy.parseResponse(responseText);
        if (!parsed.ok) {
            errorCode = parsed.reason;
            status = "error";
            return;
        }
        completedQuery = activeQuery;
        rows = parsed.rows;
        errorCode = "";
        status = parsed.rows.length ? "ready" : "empty";
    }

    Process {
        id: searchProcess
        command: []
        running: false
        stdout: StdioCollector {
            onStreamFinished: lookup.responseText = String(text || "")
        }
        onExited: function(exitCode, exitStatus) {
            // stdout StdioCollector may finish in the same event turn.
            // Defer settlement once before reading its finished contents.
            Qt.callLater(function() {
                lookup.finish(exitCode);
            });
        }
    }
}
