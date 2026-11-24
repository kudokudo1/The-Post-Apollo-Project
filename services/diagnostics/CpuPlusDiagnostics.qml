pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "CpuPlusDiagnosticsPolicy.js" as Policy

// Session owner, independent of the demand-loaded CPU++ pane.
// No process or timer runs until an explicit button request.
Scope {
    id: owner
    property bool busy: false
    property bool faulted: false
    property string kind: ""
    property string feedback: "READY // ON DEMAND"
    property var reports: ({})
    property bool received: false
    property bool exited: false
    property bool exitOk: false
    property bool cancelled: false
    property string output: ""
    readonly property int maximumReport: 65536

    function request(job) {
        if (busy || faulted || worker.running) return false;
        const args = Policy.argumentsFor(job, path => Quickshell.shellPath(path));
        if (!args) return false;
        kind = job;
        received = false;
        exited = false;
        exitOk = false;
        cancelled = false;
        output = "";
        busy = true;
        feedback = "RUNNING // " + job.toUpperCase();
        deadline.restart();
        worker.exec(args);
        return true;
    }

    function cancel() {
        if (!busy || cancelled) return;
        cancelled = true;
        feedback = "STOPPING DIAGNOSTIC // WAIT FOR EXIT";
        worker.running = false;
    }

    function finish() {
        if (!busy || !received || !exited) return;
        deadline.stop();
        const summary = !cancelled && exitOk && output.length <= maximumReport
            ? Policy.summarize(kind, output) : null;
        const next = Object.assign({}, reports);
        next[kind] = {
            status: cancelled ? "CANCELLED" : summary ? "COMPLETE" : "NOT VERIFIED",
            summary: summary || "NO VERIFIED RESULT // PARTIAL OUTPUT MAY BE AVAILABLE",
            text: output.length <= maximumReport ? output : "",
            finishedAt: new Date().toISOString()
        };
        reports = next;
        feedback = next[kind].status + " // " + kind.toUpperCase();
        output = "";
        busy = false;
    }

    Timer {
        id: deadline
        interval: 155000
        repeat: false
        onTriggered: {
            if (!owner.busy) return;
            // Missing exit/stream notification: refuse another run rather than
            // accepting late output under a new request identity.
            owner.faulted = true;
            owner.busy = false;
            owner.output = "";
            owner.feedback = "RUNNER UNAVAILABLE // COMPLETION NOT OBSERVED";
            worker.running = false;
        }
    }

    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                if (!owner.busy) return;
                owner.output = this.text;
                owner.received = true;
                owner.finish();
            }
        }
        onExited: function(code, exitStatus) {
            if (!owner.busy) return;
            owner.exitOk = code === 0 && exitStatus === 0;
            owner.exited = true;
            owner.finish();
        }
    }
}
