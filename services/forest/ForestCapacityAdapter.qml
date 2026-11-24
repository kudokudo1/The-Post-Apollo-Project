import QtQuick
import Quickshell
import Quickshell.Io
import "ForestCapacityPolicy.js" as CapacityPolicy

// ForestW only. P2C already owns bounded Ollama and fixed /sys DRM reads.
// One explicit CHECK. No timer, model argument, new provider, inference,
// application mutation, host authentication, C5 permission or persistence.
Scope {
    id: capacity
    property bool scanning: false
    property string status: "NOT_CHECKED"
    property string reason: ""
    property var data: CapacityPolicy.beginScan().data
    property var scanState: CapacityPolicy.beginScan()

    function inspectCapacity() {
        if (scanning || inspectProcess.running)
            return false;
        scanState = CapacityPolicy.beginScan();
        status = "CHECKING";
        reason = "";
        data = scanState.data;
        scanning = true;
        inspectProcess.exec([
            "python3",
            Quickshell.shellPath("scripts/forest/performance_capacity_p2c.py"),
            "inspect"
        ]);
        return true;
    }
    function acceptProgress(next) {
        if (!scanning || !next)
            return;
        scanState = next;
        if (!next.complete)
            return;
        status = next.status;
        reason = next.reason;
        data = next.data;
        scanning = false;
    }

    Process {
        id: inspectProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                capacity.acceptProgress(CapacityPolicy.captureStdout(
                    capacity.scanState, String(this.text || "")));
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                capacity.acceptProgress(CapacityPolicy.captureStderr(
                    capacity.scanState, String(this.text || "")));
            }
        }
        onExited: function(code, exitStatus) {
            capacity.acceptProgress(CapacityPolicy.captureExit(
                capacity.scanState, code, exitStatus));
        }
    }
}
