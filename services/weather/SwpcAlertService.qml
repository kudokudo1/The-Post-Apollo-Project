import QtQuick
import Quickshell
import Quickshell.Io
import "SwpcAlertPolicy.js" as SwpcAlertPolicy

// SWPC-issued bulletin ARCHIVE only. Recent != active warning. This reader
// is mounted with SPACE, not an always-running system notification service.
Scope {
    id: alerts

    property bool active: true
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var bulletins: []
    property int count48h: 0
    property date lastUpdated
    property real receivedMs: 0
    property real clockMs: Date.now()

    readonly property bool loading: bulletinFetch.running
    readonly property bool fresh: ready && !failed && receivedMs > 0 &&
                                  clockMs - receivedMs <= 30 * 60000
    readonly property string endpoint:
        "https://services.swpc.noaa.gov/products/alerts.json"

    function refresh() {
        if (active && !bulletinFetch.running)
            bulletinFetch.running = true;
    }

    function parseResponse(raw) {
        try {
            const now = Date.now();
            const result = SwpcAlertPolicy.parseBulletins(
                JSON.parse(raw), now, 48, 3
            );
            bulletins = result.bulletins;
            count48h = result.count;
            receivedMs = now;
            clockMs = now;
            lastUpdated = new Date();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "NOAA BULLETIN DATA UNAVAILABLE";
            console.log("SwpcAlertService parse error:", error);
        }
    }

    Process {
        id: bulletinFetch
        command: ["curl", "-fsSL", "--compressed", "--max-time", "12",
                  alerts.endpoint]
        stdout: StdioCollector {
            onStreamFinished: alerts.parseResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                alerts.failed = true;
                alerts.errorText = "NOAA BULLETIN REQUEST FAILED";
            }
        }
    }

    // Ten-minute fetch cadence, only while SPACE is instantiated.
    Timer {
        interval: 600000
        repeat: true
        running: alerts.active
        onTriggered: alerts.refresh()
    }

    // UI freshness clock; no additional request.
    Timer {
        interval: 60000
        repeat: true
        running: alerts.active
        onTriggered: alerts.clockMs = Date.now()
    }

    onActiveChanged: {
        if (active)
            refresh();
    }
    Component.onCompleted: {
        if (active)
            refresh();
    }
}
