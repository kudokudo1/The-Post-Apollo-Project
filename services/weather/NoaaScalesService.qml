import QtQuick
import Quickshell
import Quickshell.Io
import "NoaaScalesPolicy.js" as ScalesPolicy

// SPACE-only official NOAA Space Weather Scales snapshot.
// Do not synthesize G/R/S values from Kp, X-ray or proton measurements here.
Scope {
    id: scales

    property bool active: true
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var current: ScalesPolicy.emptyCurrent()
    property date lastUpdated

    readonly property bool loading: scalesFetch.running
    readonly property string endpoint:
        "https://services.swpc.noaa.gov/products/noaa-scales.json"

    function refresh() {
        if (!active || scalesFetch.running)
            return false;
        scalesFetch.running = true;
        return true;
    }

    function accept(raw) {
        try {
            current = ScalesPolicy.parseCurrent(
                JSON.parse(String(raw || ""))
            );
            lastUpdated = new Date();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "NOAA SPACE-WEATHER SCALES UNAVAILABLE";
            console.log("NoaaScalesService parse error:", error);
        }
    }

    Process {
        id: scalesFetch
        command: [
            "curl", "-fsSL", "--max-time", "10",
            "--proto", "=https", "--proto-redir", "=https",
            "-H", "Accept: application/json",
            "-A", "Post-Apollo-WeatherStation/0.7",
            scales.endpoint
        ]

        stdout: StdioCollector {
            onStreamFinished: scales.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                scales.failed = true;
                scales.errorText = "NOAA SPACE-WEATHER SCALES REQUEST FAILED";
            }
        }
    }

    Timer {
        interval: 300000
        repeat: true
        running: scales.active
        onTriggered: scales.refresh()
    }

    onActiveChanged: {
        if (active)
            Qt.callLater(function() { scales.refresh(); });
    }

    Component.onCompleted: {
        if (active)
            Qt.callLater(function() { scales.refresh(); });
    }
}
