import QtQuick
import Quickshell
import Quickshell.Io
import "ForestResidencyPolicy.js" as ResidencyPolicy

// UI-owned, one-shot P0 observer. Same local Ollama provider as B0.
// There is ONE instance shared by header + model popup. No polling, POST,
// model load, inference, private session, permission or host control.
Scope {
    id: residency
    property bool scanning: false
    property string status: "NOT_CHECKED"
    property string reason: ""
    // Local display metadata only. This clock is NOT an Ollama status source.
    property string lastObservedLocalTime: ""
    property var models: []
    property var records: [] // The same P0 snapshot, no extra query.
    property var scanState: ResidencyPolicy.beginScan()

    function scanResidency() {
        if (scanning || residencyProcess.running)
            return false;
        expiryTimer.stop();
        scanState = ResidencyPolicy.beginScan();
        scanning = true;
        status = "CHECKING";
        reason = "";
        lastObservedLocalTime = "";
        models = []; // A previous scan cannot appear current during refresh.
        records = [];
        residencyProcess.exec([
            "python3",
            Quickshell.shellPath("scripts/forest/performance_snapshot_p0.py"),
            "snapshot"
        ]);
        return true;
    }
    function invalidate() {
        if (scanning || residencyProcess.running)
            return;
        expiryTimer.stop();
        status = "UNAVAILABLE";
        reason = "REFRESH_NOT_STARTED";
        lastObservedLocalTime = "";
        models = [];
        records = [];
    }
    function acceptProgress(next) {
        if (!scanning || !next)
            return;
        scanState = next;
        if (!next.complete)
            return;
        status = next.status;
        reason = next.reason;
        models = next.models;
        records = next.records;
        scanning = false;
        if (next.status === "OBSERVED") {
            // Stamp only a successfully validated, fully exited P0 scan.
            lastObservedLocalTime = Qt.formatTime(new Date(), "HH:mm:ss");
            expiryTimer.restart(); // one-shot local expiry, no re-probe
        } else {
            lastObservedLocalTime = "";
            expiryTimer.stop();
        }
    }
    function expireObserved() {
        if (scanning || status !== "OBSERVED")
            return;
        // Cached model residency expires, it is NOT remeasured.
        status = "STALE";
        reason = "SNAPSHOT_EXPIRED";
        models = [];
        records = [];
        // Keep the former observation time visible to explain staleness.
    }
    Timer {
        id: expiryTimer
        interval: 300000 // five minutes; no repeating or background GET
        repeat: false
        running: false
        onTriggered: residency.expireObserved()
    }
    Process {
        id: residencyProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                residency.acceptProgress(ResidencyPolicy.captureStdout(
                    residency.scanState, String(this.text || "")));
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                residency.acceptProgress(ResidencyPolicy.captureStderr(
                    residency.scanState, String(this.text || "")));
            }
        }
        onExited: function(code, exitStatus) {
            residency.acceptProgress(ResidencyPolicy.captureExit(
                residency.scanState, code, exitStatus));
        }
    }
}
