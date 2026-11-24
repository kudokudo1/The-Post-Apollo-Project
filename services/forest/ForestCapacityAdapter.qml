import QtQuick
import Quickshell
import Quickshell.Io
import "ForestCapacityPolicy.js" as CapacityPolicy

// ForestW only. P2C already owns bounded Ollama and fixed /sys DRM reads.
// One explicit CHECK; optional exact model is a read-only filter, not authority.
// No timer, new provider, inference,
// application mutation, host authentication, C5 permission or persistence.
Scope {
    id: capacity
    property bool scanning: false
    property string status: "NOT_CHECKED"
    property string reason: ""
    // Local display clock, never a second P2C/Ollama measurement.
    property string lastObservedLocalTime: ""
    // Identifies distinct completed local checks, not a trusted clock.
    property double observationSequence: 0
    property string requestedModel: ""
    property var data: CapacityPolicy.beginScan().data
    property var scanState: CapacityPolicy.beginScan()

    function inspectCapacity(model) {
        if (scanning || inspectProcess.running)
            return false;
        const wanted = model === undefined ? "" : model;
        // Reject malformed caller values before starting a process.
        const pending = CapacityPolicy.beginScan(wanted);
        if (!pending)
            return false;
        expiryTimer.stop();
        scanState = pending;
        requestedModel = wanted;
        status = "CHECKING";
        reason = "";
        lastObservedLocalTime = "";
        data = scanState.data;
        scanning = true;
        const argv = [
            "python3",
            Quickshell.shellPath("scripts/forest/performance_capacity_p2c.py"),
            "inspect"
        ];
        // P2C owns this existing opt-in read-only exact-model CLI argument.
        if (wanted !== "")
            argv.push("--model", wanted);
        inspectProcess.exec(argv);
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
        if (next.status === "OBSERVED") {
            lastObservedLocalTime = Qt.formatTime(new Date(), "HH:mm:ss");
            observationSequence += 1;
            expiryTimer.restart(); // five-minute local cache expiry only
        } else {
            lastObservedLocalTime = "";
            expiryTimer.stop();
        }
    }
    function expireObserved() {
        if (scanning || status !== "OBSERVED")
            return;
        status = "STALE";
        reason = "SNAPSHOT_EXPIRED";
        data = CapacityPolicy.beginScan().data; // clear old resource hints
        // Retain last observation time to explain expired data.
    }
    Timer {
        id: expiryTimer
        interval: 300000
        repeat: false
        running: false
        onTriggered: capacity.expireObserved()
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
