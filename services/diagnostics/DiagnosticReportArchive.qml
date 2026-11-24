import QtQuick
import Quickshell
import Quickshell.Io
import "CpuPlusDiagnosticsPolicy.js" as Policy

// Event-driven local archive. No startup IO or repeating timer.
Scope {
    id: store
    property var rows: []
    property string status: "NOT LOADED"
    property bool busy: false
    property bool faulted: false
    property bool stdoutSeen: false
    property bool exitSeen: false
    property bool exitOk: false
    property string frame: ""
    property string output: ""
    property var submitted: null

    function invoke(request) {
        if (busy || faulted || worker.running) return false;
        submitted = request;
        frame = JSON.stringify(request) + "\n";
        output = "";
        stdoutSeen = false;
        exitSeen = false;
        exitOk = false;
        busy = true;
        status = request.action === "save" ? "SAVING" : "LOADING";
        deadline.restart();
        worker.exec(["/usr/bin/timeout", "--kill-after=2s", "10s", "/usr/bin/python3",
                     "-I", "-B", Quickshell.shellPath("scripts/cpuplus_diagnostic_archive.py")]);
        return true;
    }
    function finish() {
        if (!busy || !stdoutSeen || !exitSeen) return;
        deadline.stop();
        let accepted = null;
        if (exitOk && output.length <= 4194304) {
            try {
                accepted = Policy.archiveResponse(JSON.parse(output), submitted);
            } catch (error) {}
        }
        if (accepted !== null) {
            rows = accepted;
            status = "READY";
        } else {
            // Old cached rows may no longer be current; fail closed.
            rows = [];
            status = "FAILED // NOT CONFIRMED";
        }
        submitted = null;
        output = "";
        frame = "";
        busy = false;
    }
    Timer {
        id: deadline
        interval: 15000
        repeat: false
        onTriggered: {
            if (!store.busy) return;
            store.faulted = true;
            store.busy = false;
            store.rows = [];
            store.submitted = null;
            store.output = "";
            store.frame = "";
            store.status = "UNAVAILABLE // RESTART REQUIRED";
            worker.running = false;
        }
    }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            if (store.busy && store.frame) {
                worker.write(store.frame);
                store.frame = "";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                if (!store.busy) return;
                store.output = this.text;
                store.stdoutSeen = true;
                store.finish();
            }
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            if (!store.busy) return;
            store.exitOk = code === 0 && exitStatus === 0;
            store.exitSeen = true;
            store.finish();
        }
    }
}
