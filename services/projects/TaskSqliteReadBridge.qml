import QtQuick
import Quickshell
import Quickshell.Io

// M10k standalone read-only Quickshell Process bridge, not mounted anywhere.
// No default database path, timers, auto-load, FileView or write methods.
// A future, separately approved host must explicitly set candidatePath and
// call requestStatus(). This is not a replacement for ApolloHubTodoStore.
Scope {
    id: probe

    property string candidatePath: ""
    property bool busy: false
    property string status: "NOT_CHECKED"
    property string errorCode: ""
    property var summary: null
    property bool processExited: false
    property bool stdoutFinished: false
    property int exitCode: -1
    property string stdoutBuffer: ""

    readonly property bool writeReady: false
    readonly property bool remoteWriteAuthorized: false

    signal inspected()

    function requestStatus() {
        if (busy) return false;
        // Absolute explicit path only, never infer or open a live user DB.
        if (!/^\/.+\/tasks\.db$/.test(candidatePath)) {
            status = "ERROR";
            errorCode = "EXPLICIT_PATH_REQUIRED";
            summary = null;
            return false;
        }
        busy = true;
        status = "READING";
        errorCode = "";
        summary = null;
        processExited = false;
        stdoutFinished = false;
        exitCode = -1;
        stdoutBuffer = "";
        readProcess.exec(["python3", "-B", "-I",
            Quickshell.shellPath("services/projects/TaskSqliteReadProbe.py"),
            "--db", candidatePath]);
        return true;
    }

    function acceptResult() {
        if (!busy || !processExited || !stdoutFinished) return;
        busy = false;
        if (exitCode !== 0 || stdoutBuffer.length > 1024) {
            status = "ERROR";
            errorCode = "READ_PROBE_FAILED";
            summary = null;
            inspected();
            return;
        }
        try {
            const x = JSON.parse(stdoutBuffer);
            if (!x || x.writeReady !== false
                    || x.remoteWriteAuthorized !== false
                    || typeof x.available !== "boolean"
                    || ["ABSENT","EMPTY","READY","RECOVERY_REVIEW"].indexOf(x.status) < 0)
                throw new Error("BAD_STATUS");
            if (x.status === "READY" || x.status === "RECOVERY_REVIEW") {
                const values = [x.revision, x.projects, x.tasks,
                                x.operations, x.blockedOperations];
                for (let i=0; i<values.length; i++) {
                    if (!Number.isSafeInteger(values[i]) || values[i] < 0)
                        throw new Error("BAD_COUNT");
                }
                if (!x.available || x.status === "READY" && x.blockedOperations !== 0
                        || x.status === "RECOVERY_REVIEW" && x.blockedOperations === 0)
                    throw new Error("INCONSISTENT_STATUS");
                summary = {revision:x.revision, projects:x.projects,
                    tasks:x.tasks, operations:x.operations,
                    blockedOperations:x.blockedOperations};
            } else {
                if (x.available) throw new Error("UNEXPECTED_AVAILABLE");
                summary = null;
            }
            status = x.status;
            errorCode = "";
        } catch (e) {
            status = "ERROR";
            errorCode = "INVALID_READ_RESPONSE";
            summary = null;
        }
        inspected();
    }

    Process {
        id: readProcess
        stdout: StdioCollector {
            onStreamFinished: {
                probe.stdoutBuffer = this.text;
                probe.stdoutFinished = true;
                probe.acceptResult();
            }
        }
        // Errors are intentionally not shown to users: absolute paths and
        // diagnostics may contain private machine information.
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            probe.exitCode = Number(code);
            probe.processExited = true;
            probe.acceptResult();
        }
    }
}
