import QtQuick
import Quickshell
import Quickshell.Io
import "UsnoCelnavPolicy.js" as CelnavPolicy

// SKY-only current-object astronomy. USNO CelNav returns bodies above its
// service display thresholds for a coordinate/time; it does not guarantee
// naked-eye visibility through daylight, glare, terrain or clouds.
Scope {
    id: celnav

    property bool active: true
    property var latitude: ""
    property var longitude: ""

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var snapshot: CelnavPolicy.emptyResult()
    property date lastUpdated

    property real sampleClockMs: Date.now()
    property string loadedKey: ""
    property string inflightKey: ""

    readonly property var request:
        CelnavPolicy.requestInfo(sampleClockMs, latitude, longitude)
    readonly property bool configured: request.valid
    readonly property bool loading: celnavFetch.running

    function refresh() {
        if (!active || celnavFetch.running)
            return false;

        sampleClockMs = Date.now();
        const next = CelnavPolicy.requestInfo(
            sampleClockMs, latitude, longitude
        );
        if (!next.valid)
            return false;

        inflightKey = next.key;
        celnavFetch.command = [
            "curl", "-fsSL", "--max-time", "12",
            "--proto", "=https", "--proto-redir", "=https",
            "-H", "Accept: application/json",
            "-A", "Post-Apollo-WeatherStation/0.6",
            next.endpoint
        ];
        celnavFetch.running = true;
        return true;
    }

    function accept(raw) {
        const current = CelnavPolicy.requestInfo(
            sampleClockMs, latitude, longitude
        );
        if (!current.valid || current.key !== inflightKey)
            return;
        try {
            snapshot = CelnavPolicy.parse(
                JSON.parse(String(raw || ""))
            );
            loadedKey = inflightKey;
            lastUpdated = new Date();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "USNO CURRENT-SKY DATA UNAVAILABLE";
            console.log("UsnoCelnavService parse error:", error);
        }
    }

    Process {
        id: celnavFetch
        command: []

        stdout: StdioCollector {
            onStreamFinished: celnav.accept(text)
        }

        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                celnav.failed = true;
                celnav.errorText = "USNO CURRENT-SKY REQUEST FAILED";
            }
        }
    }

    Timer {
        id: refreshClock
        interval: 300000
        repeat: true
        running: celnav.active && celnav.configured
        onTriggered: celnav.refresh()
    }

    Timer {
        id: locationDebounce
        interval: 250
        repeat: false
        onTriggered: celnav.refresh()
    }

    onActiveChanged: {
        if (active)
            locationDebounce.restart();
    }
    onLatitudeChanged: {
        if (active)
            locationDebounce.restart();
    }
    onLongitudeChanged: {
        if (active)
            locationDebounce.restart();
    }
    Component.onCompleted: {
        if (active)
            locationDebounce.restart();
    }
}
