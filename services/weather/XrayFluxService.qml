import QtQuick
import Quickshell
import Quickshell.Io
import "XrayFluxPolicy.js" as XrayFluxPolicy

// View-scoped six-hour NOAA GOES XRS measurements, separate from flare
// EVENT records and official NOAA alerts. No global polling when SPACE exits.
Scope {
    id: xray

    property bool active: true
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property real fluxLong: -1
    property real fluxShort: -1
    property string satellite: ""
    property real sampleTimeMs: 0
    property string sampleUtc: "-- UTC"
    property var classEquivalent: ({letter: "", label: "--"})
    property var trend: []
    property date lastUpdated
    property real clockMs: Date.now()

    readonly property bool loading: xrayFetch.running
    readonly property bool sampleFresh:
        ready && !failed && sampleTimeMs > 0 &&
        sampleTimeMs <= clockMs + 300000 &&
        clockMs - sampleTimeMs <= 600000

    readonly property string endpoint:
        "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json"

    function refresh() {
        if (active && !xrayFetch.running)
            xrayFetch.running = true;
    }

    function parseResponse(rawText) {
        try {
            const parsed = XrayFluxPolicy.parseXraySeries(
                JSON.parse(rawText), Date.now()
            );
            fluxLong = parsed.fluxLong;
            fluxShort = parsed.fluxShort;
            satellite = parsed.satellite;
            sampleTimeMs = parsed.sampleTimeMs;
            sampleUtc = parsed.sampleUtc;
            classEquivalent = parsed.classEquivalent;
            trend = parsed.trend;
            lastUpdated = new Date();
            clockMs = Date.now();
            ready = true;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "GOES X-RAY DATA UNAVAILABLE";
            console.log("XrayFluxService parse error:", error);
        }
    }

    Process {
        id: xrayFetch
        command: ["curl", "-fsSL", "--compressed", "--max-time", "12",
                  xray.endpoint]
        stdout: StdioCollector {
            onStreamFinished: xray.parseResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                xray.failed = true;
                xray.errorText = "GOES X-RAY REQUEST FAILED";
            }
        }
    }

    // Five minutes, while SPACE view exists. The primary feed is ~160 KB.
    Timer {
        interval: 300000
        repeat: true
        running: xray.active
        onTriggered: xray.refresh()
    }

    // Update stale label without network traffic.
    Timer {
        interval: 60000
        repeat: true
        running: xray.active
        onTriggered: xray.clockMs = Date.now()
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
