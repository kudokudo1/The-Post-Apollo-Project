import QtQuick
import Quickshell
import Quickshell.Io
import "../hub/ApolloHubTodoPolicy.js" as TodoPolicy

// M10y independent TEST-ONLY read-only SQLite-v2 to live snapshot projection.
// Not mounted in shell.qml or TASKS. No automatic path or startup, no writer.
Scope {
    id: bridge
    property string candidatePath: ""
    property bool busy: false
    property string status: "NOT_CHECKED"
    property string errorCode: ""
    property int revision: -1
    property string sourceHash: ""
    property int blockedOperations: 0
    property var snapshot: TodoPolicy.view(
        "loading", TodoPolicy.emptyDocument(), "")

    property bool processExited: false
    property bool stdoutFinished: false
    property int exitCode: -1
    property string stdoutBuffer: ""

    readonly property bool writeReady: false
    readonly property bool remoteWriteAuthorized: false
    readonly property bool activate: false

    signal inspected()

    function unavailable(reason) {
        busy = false;
        status = "ERROR";
        errorCode = reason;
        revision = -1;
        sourceHash = "";
        blockedOperations = 0;
        snapshot = TodoPolicy.view(
            "error", TodoPolicy.emptyDocument(), reason);
        inspected();
    }

    function requestSnapshot() {
        if (busy) return false;
        // The extra private fixture-directory name prevents this UI from
        // accepting an arbitrary live tasks.db path. Host remains unmounted.
        if (!/^\/.+\/m10y-snapshot-test\/tasks\.db$/.test(candidatePath)) {
            unavailable("EXPLICIT_TEST_FIXTURE_REQUIRED");
            return false;
        }
        busy = true;
        status = "READING";
        errorCode = "";
        revision = -1;
        sourceHash = "";
        blockedOperations = 0;
        snapshot = TodoPolicy.view(
            "loading", TodoPolicy.emptyDocument(), "");
        processExited = false;
        stdoutFinished = false;
        exitCode = -1;
        stdoutBuffer = "";
        worker.exec(["python3", "-B", "-I",
            Quickshell.shellPath("services/projects/TaskSqliteSnapshotProbeM10y.py"),
            "--db", candidatePath]);
        return true;
    }

    function acceptResult() {
        if (!busy || !processExited || !stdoutFinished) return;
        if (exitCode !== 0 || stdoutBuffer.length > 1048576) {
            unavailable("READ_ONLY_PROBE_FAILED");
            return;
        }
        try {
            var reply = JSON.parse(stdoutBuffer);
            var keys = ["protocol","status","available","revision",
                "sourceHash","blockedOperations","document",
                "writeReady","remoteWriteAuthorized"];
            if (!reply || typeof reply !== "object" ||
                    Array.isArray(reply) || Object.keys(reply).length !== keys.length)
                throw new Error("INVALID_FIELDS");
            for (var i=0; i<keys.length; ++i)
                if (!Object.prototype.hasOwnProperty.call(reply, keys[i]))
                    throw new Error("MISSING_FIELD");
            if (reply.protocol !== 1 || reply.writeReady !== false
                    || reply.remoteWriteAuthorized !== false
                    || typeof reply.available !== "boolean")
                throw new Error("BAD_PROTOCOL");
            if (reply.status === "ABSENT") {
                if (reply.available !== false || reply.document !== null
                        || reply.revision !== null || reply.sourceHash !== null
                        || reply.blockedOperations !== 0)
                    throw new Error("INVALID_ABSENT");
                busy = false;
                status = "ABSENT";
                errorCode = "TEST_FIXTURE_ABSENT";
                snapshot = TodoPolicy.view(
                    "unsupported", TodoPolicy.emptyDocument(), errorCode);
                inspected();
                return;
            }
            if (["READY","EMPTY","RECOVERY_REVIEW"].indexOf(reply.status) < 0
                    || reply.available !== true
                    || !Number.isSafeInteger(reply.revision) || reply.revision < 0
                    || typeof reply.sourceHash !== "string"
                    || !/^[0-9a-f]{64}$/.test(reply.sourceHash)
                    || !Number.isSafeInteger(reply.blockedOperations)
                    || reply.blockedOperations < 0
                    || reply.blockedOperations > 1000)
                throw new Error("INVALID_STATUS");
            var doc = reply.document;
            if (!doc || doc.version !== 3 || !TodoPolicy.validate(doc).ok)
                throw new Error("INVALID_COMPATIBILITY_DOCUMENT");
            if ((reply.status === "READY" && (doc.tasks.length === 0
                     || reply.blockedOperations !== 0))
                    || (reply.status === "EMPTY" &&
                        (doc.tasks.length !== 0 || reply.blockedOperations !== 0))
                    || (reply.status === "RECOVERY_REVIEW" &&
                        reply.blockedOperations === 0))
                throw new Error("INCONSISTENT_STATUS");
            var safeView = TodoPolicy.view(
                doc.tasks.length === 0 ? "empty" : "ready", doc, "");
            safeView.writable = false;
            // Recovery-review remains visible for diagnosis, never writable.
            snapshot = safeView;
            revision = reply.revision;
            sourceHash = reply.sourceHash;
            blockedOperations = reply.blockedOperations;
            status = reply.status;
            errorCode = "";
            busy = false;
            inspected();
        } catch (e) {
            unavailable("INVALID_READ_RESPONSE");
        }
    }

    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                bridge.stdoutBuffer = this.text;
                bridge.stdoutFinished = true;
                bridge.acceptResult();
            }
        }
        // Never send private task descriptions or fixture paths to QS logs.
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            bridge.exitCode = Number(code);
            bridge.processExited = true;
            bridge.acceptResult();
        }
    }
}
