import QtQuick
import Quickshell
import Quickshell.Io
import "GdacsPolicy.js" as GdacsPolicy

// Weather Station owner for the GDACS recent multi-hazard collection.
// MAP consumes one retained event set. It is context for disaster awareness,
// not a substitute for competent local/national emergency instructions.
Scope {
    id: gdacs

    property bool active: true
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var events: []
    property date lastUpdated
    property double lastFetchMs: 0

    readonly property int cacheMs: 900000
    readonly property string endpoint:
        "https://www.gdacs.org/gdacsapi/api/events/geteventlist/events4app"
    readonly property bool loading: fetchProcess.running

    function refresh(force) {
        if (!active || fetchProcess.running)
            return false;
        const now = Date.now();
        if (!force && ready && lastFetchMs > 0
                && now - lastFetchMs < cacheMs)
            return false;
        fetchProcess.running = true;
        return true;
    }

    function parseResponse(raw) {
        try {
            const parsed = GdacsPolicy.parseEventList(JSON.parse(raw), 100);
            events = parsed;
            lastFetchMs = Date.now();
            lastUpdated = new Date(lastFetchMs);
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "GDACS FEED UNAVAILABLE";
            console.log("GdacsService parse error:", error);
        }
    }

    Process {
        id: fetchProcess
        command: [
            "curl", "-fsSL", "--compressed", "--max-time", "14",
            "-A", "Post-Apollo-WeatherStation/0.1",
            gdacs.endpoint
        ]
        stdout: StdioCollector {
            onStreamFinished: gdacs.parseResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                gdacs.failed = true;
                gdacs.errorText = "GDACS REQUEST FAILED";
            }
        }
    }

    // GDACS recommends caching collection responses. Weather Station refreshes
    // at a deliberately modest 15-minute cadence only while MAP owns this feed.
    Timer {
        interval: gdacs.cacheMs
        repeat: true
        running: gdacs.active
        onTriggered: gdacs.refresh(false)
    }

    onActiveChanged: {
        if (active)
            refresh(false);
    }

    Component.onCompleted: {
        if (active)
            refresh(false);
    }
}
