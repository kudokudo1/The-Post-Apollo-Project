import QtQuick
import Quickshell
import Quickshell.Io

// Research M4a: explicit read-only controller. No storage write path.
// The view is cleared on deactivation and stale child responses are refused.
Scope {
    id: researchRead
    property bool monitoring: false
    property var investigations: []
    property int revision: -1
    property string state: "idle" // idle, loading, ready, failed
    property string message: "RESEARCH READ DISCONNECTED"
    property string commandFrame: ""
    property string capturedOutput: ""
    property int generation: 0
    property int submittedGeneration: -1
    readonly property bool loading: state === "loading"

    function clearView() {
        investigations = [];
        revision = -1;
        state = "idle";
        message = monitoring
            ? "LOCAL RESEARCH // PRESS LOAD CASES"
            : "RESEARCH READ DISCONNECTED";
    }

    onMonitoringChanged: {
        generation += 1;
        clearView();
    }

    function load() {
        if (!monitoring || worker.running || state === "loading")
            return false;
        investigations = [];
        revision = -1;
        state = "loading";
        message = "READING LOCAL INVESTIGATIONS // READ ONLY";
        capturedOutput = "";
        commandFrame = '{"action":"list"}\n';
        submittedGeneration = generation;
        worker.exec({
            command: ["/usr/bin/env", "node",
                Quickshell.shellPath("scripts/finance/research_investigation_read_bridge.mjs")],
            environment: ({
                ACTUAL_PASSWORD_FILE: null, ACTUAL_SYNC_ID: null,
                ACTUAL_SERVER_URL: null, ACTUAL_SYNC_ID_FILE: null
            })
        });
        return true;
    }

    function acceptDocument(doc) {
        if (!doc || typeof doc !== "object" || Array.isArray(doc)
                || Object.keys(doc).length !== 3
                || doc.schemaVersion !== 1
                || !Number.isSafeInteger(doc.revision) || doc.revision < 0
                || !Array.isArray(doc.investigations)
                || doc.investigations.length > 50)
            return false;
        const seen = {};
        for (let i = 0; i < doc.investigations.length; i++) {
            const item = doc.investigations[i];
            if (!item || typeof item.id !== "string"
                    || !/^[a-zA-Z0-9_-]{1,64}$/.test(item.id)
                    || seen[item.id] || typeof item.title !== "string"
                    || item.title.length > 160
                    || typeof item.question !== "string"
                    || item.question.length > 1000
                    || !Array.isArray(item.evidence)
                    || item.evidence.length > 40)
                return false;
            seen[item.id] = true;
            for (let j = 0; j < item.evidence.length; j++) {
                const evidence = item.evidence[j];
                if (!evidence || typeof evidence.id !== "string"
                        || typeof evidence.source !== "string"
                        || typeof evidence.title !== "string"
                        || typeof evidence.summary !== "string"
                        || typeof evidence.url !== "string"
                        || typeof evidence.observedAt !== "string"
                        || evidence.title.length > 160
                        || evidence.summary.length > 2000
                        || evidence.url.length > 1000)
                    return false;
            }
        }
        investigations = doc.investigations;
        revision = doc.revision;
        state = "ready";
        message = "LOCAL INVESTIGATIONS // READ ONLY // NOT ACCOUNT VERIFIED";
        return true;
    }

    function acceptOutput(raw, exitCode) {
        if (exitCode !== 0 || typeof raw !== "string"
                || raw.length > 500100)
            return false;
        const prefix = "FINANCE_RESEARCH_READ_RESULT ";
        const lines = raw.split(/\r?\n/);
        if (lines.length !== 2 || lines[1] !== ""
                || lines[0].indexOf(prefix) !== 0)
            return false;
        try {
            return acceptDocument(JSON.parse(lines[0].slice(prefix.length)));
        } catch (error) {
            return false;
        }
    }

    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            // Finish the read-only child even if the view was closed mid-start.
            if (researchRead.commandFrame !== "") {
                worker.write(researchRead.commandFrame);
                researchRead.commandFrame = "";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: researchRead.capturedOutput = text
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                const sameView = researchRead.monitoring
                    && researchRead.submittedGeneration === researchRead.generation;
                const output = researchRead.capturedOutput;
                researchRead.capturedOutput = "";
                researchRead.commandFrame = "";
                if (!sameView)
                    return;
                if (!researchRead.acceptOutput(output, exitCode)) {
                    researchRead.investigations = [];
                    researchRead.revision = -1;
                    researchRead.state = "failed";
                    researchRead.message = "LOCAL RESEARCH READ FAILED // CHECK STORAGE // REFRESH MANUALLY";
                }
            });
        }
    }
}
