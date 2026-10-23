import QtQuick
import Quickshell
import Quickshell.Io
import "SolarFlarePolicy.js" as SolarFlarePolicy

// View-scoped NOAA GOES X-ray FLARE EVENTS, not a live X-ray flux sensor.
// This reader does not affect SpaceService's four established feeds.
Scope {
    id: flareService

    property bool active: true
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var latest: null
    property var events: []
    property int count24h: 0
    property int cPlus24h: 0
    property date lastUpdated

    readonly property bool loading: flareFetch.running
    readonly property string endpoint:
        "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json"

    function refresh() {
        if (active && !flareFetch.running)
            flareFetch.running = true;
    }

    function parseResponse(rawText) {
        try {
            const result = SolarFlarePolicy.parseFlares(
                JSON.parse(rawText), Date.now()
            );
            latest = result.latest;
            events = result.events;
            count24h = result.count24h;
            cPlus24h = result.cPlus24h;
            lastUpdated = new Date();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "GOES EVENT DATA UNAVAILABLE";
            console.log("SolarFlareService parse error:", error);
        }
    }

    Process {
        id: flareFetch
        command: ["curl", "-fsSL", "--compressed", "--max-time", "12",
                  flareService.endpoint]
        stdout: StdioCollector {
            onStreamFinished: flareService.parseResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                flareService.failed = true;
                flareService.errorText = "GOES EVENT REQUEST FAILED";
            }
        }
    }

    // Only while SPACE is loaded. One ~30 KB GOES event request per 15 min.
    Timer {
        interval: 900000
        repeat: true
        running: flareService.active
        onTriggered: flareService.refresh()
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
