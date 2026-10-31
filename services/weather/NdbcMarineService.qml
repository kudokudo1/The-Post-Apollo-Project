import QtQuick
import Quickshell
import Quickshell.Io
import "NdbcMarinePolicy.js" as MarinePolicy

// GROUND-only nearest reporting NDBC observation. The all-station latest file
// is fetched once, then nearest selection is local. Distance is always exposed
// because "nearest marine station" is not the same thing as "local coast."
Scope {
    id: marine

    property bool active: true
    property var latitude: ""
    property var longitude: ""

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var station: null
    property int reportingStations: 0
    property date lastUpdated

    property string inflightKey: ""
    readonly property string currentKey:
        MarinePolicy.requestKey(latitude, longitude)
    readonly property bool configured: currentKey !== ""
    readonly property bool loading: marineFetch.running
    readonly property string endpoint:
        "https://www.ndbc.noaa.gov/data/latest_obs/latest_obs.txt"

    function refresh() {
        if (!active || !configured || marineFetch.running)
            return false;
        inflightKey = currentKey;
        marineFetch.running = true;
        return true;
    }

    function accept(raw) {
        if (!configured || currentKey !== inflightKey)
            return;
        try {
            const rows = MarinePolicy.parseLatest(String(raw || ""));
            station = MarinePolicy.nearest(rows, latitude, longitude);
            reportingStations = rows.length;
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date();
        } catch (error) {
            failed = true;
            errorText = "NDBC MARINE OBSERVATIONS UNAVAILABLE";
            console.log("NdbcMarineService parse error:", error);
        }
    }

    Process {
        id: marineFetch
        command: [
            "curl", "-fsSL", "--max-time", "12",
            "--proto", "=https", "--proto-redir", "=https",
            "-A", "Post-Apollo-WeatherStation/0.6",
            marine.endpoint
        ]
        stdout: StdioCollector {
            onStreamFinished: marine.accept(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && marine.currentKey === marine.inflightKey) {
                marine.failed = true;
                marine.errorText = "NDBC MARINE REQUEST FAILED";
            }
            if (marine.active && marine.configured
                    && marine.currentKey !== marine.inflightKey)
                Qt.callLater(function() { marine.refresh(); });
        }
    }

    Timer {
        interval: 600000
        repeat: true
        running: marine.active && marine.configured
        onTriggered: marine.refresh()
    }

    Timer {
        id: locationDebounce
        interval: 250
        repeat: false
        onTriggered: marine.refresh()
    }

    onActiveChanged: {
        if (active && configured)
            locationDebounce.restart();
    }
    onLatitudeChanged: {
        if (active && configured)
            locationDebounce.restart();
    }
    onLongitudeChanged: {
        if (active && configured)
            locationDebounce.restart();
    }
    Component.onCompleted: {
        if (active && configured)
            locationDebounce.restart();
    }
}
