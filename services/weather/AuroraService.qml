import QtQuick
import Quickshell
import Quickshell.Io
import "AuroraPolicy.js" as AuroraPolicy

// Loaded only by StationSpace. Keeps the ~900KB NOAA grid and the 15-minute
// polling loop out of all other Weather Station views.
Scope {
    id: aurora

    property bool active: true
    property string targetLatitude: ""
    property string targetLongitude: ""
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property real northPeak: -1
    property real southPeak: -1
    property real observationTimeMs: 0
    property real forecastTimeMs: 0
    property bool localReady: false
    property real localIntensity: -1
    property real localCellLatitude: 0
    property real localCellLongitude: 0
    property real localCellDistanceKm: -1
    property date lastUpdated
    property real clockMs: Date.now()

    readonly property bool loading: forecastFetch.running
    readonly property bool forecastFresh:
        ready && forecastTimeMs > 0 && forecastTimeMs + 3600000 >= clockMs
    readonly property string observationLabel:
        AuroraPolicy.utcLabel(observationTimeMs)
    readonly property string forecastLabel:
        AuroraPolicy.utcLabel(forecastTimeMs)

    readonly property string endpoint:
        "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"

    function refresh() {
        if (active && !forecastFetch.running)
            forecastFetch.running = true;
    }

    function parseResponse(raw) {
        try {
            const parsed = AuroraPolicy.parseOvation(
                JSON.parse(raw), targetLatitude, targetLongitude
            );
            northPeak = parsed.northPeak;
            southPeak = parsed.southPeak;
            localReady = parsed.localReady;
            localIntensity = parsed.localIntensity;
            localCellLatitude = parsed.localLatitude;
            localCellLongitude = parsed.localLongitude;
            localCellDistanceKm = parsed.localDistanceKm;
            observationTimeMs = parsed.observationTimeMs;
            forecastTimeMs = parsed.forecastTimeMs;
            lastUpdated = new Date();
            clockMs = Date.now();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "NOAA OVATION DATA UNAVAILABLE";
            console.log("AuroraService parse error:", error);
        }
    }

    Process {
        id: forecastFetch
        command: ["curl", "-fsSL", "--compressed", "--max-time", "12",
                  aurora.endpoint]
        stdout: StdioCollector {
            onStreamFinished: aurora.parseResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                aurora.failed = true;
                aurora.errorText = "NOAA OVATION REQUEST FAILED";
            }
        }
    }

    Timer {
        interval: 900000
        repeat: true
        running: aurora.active
        onTriggered: aurora.refresh()
    }

    // Local freshness clock only; no additional network traffic.
    Timer {
        interval: 60000
        repeat: true
        running: aurora.active
        onTriggered: aurora.clockMs = Date.now()
    }

    onActiveChanged: {
        if (active)
            refresh();
    }

    // A changed Weather fix invalidates the old local-cell projection.
    // The next already-scheduled OVATION response recomputes it. Do not spend
    // an extra NOAA request merely because the target coordinate changed.
    onTargetLatitudeChanged: localReady = false
    onTargetLongitudeChanged: localReady = false
    Component.onCompleted: {
        if (active)
            refresh();
    }
}
