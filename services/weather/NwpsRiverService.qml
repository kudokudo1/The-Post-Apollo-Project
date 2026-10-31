import QtQuick
import Quickshell
import Quickshell.Io
import "NwpsRiverPolicy.js" as RiverPolicy

// GROUND-only informational nearby river gauge lookup. The Weather location is
// used only to find nearby NWPS gauges; this service is not an emergency alert
// target and never replaces the explicitly pinned NWS alert point.
Scope {
    id: river

    property bool active: true
    property var latitude: ""
    property var longitude: ""

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var gauge: null
    property var nearbyGauges: []
    property date lastUpdated

    property bool stageflowReady: false
    property bool stageflowFailed: false
    property string stageflowErrorText: ""
    property var stageflow: ({
        "observed": RiverPolicy.normalizeStageflowProduct(null),
        "forecast": RiverPolicy.normalizeStageflowProduct(null)
    })
    property date stageflowLastUpdated
    property string stageflowGaugeId: ""
    property string inflightStageflowGaugeId: ""

    property bool contextReady: false
    property bool contextFailed: false
    property string contextErrorText: ""
    property var gaugeContext: ({
        "available": false,
        "thresholds": [],
        "impacts": [],
        "recentCrests": [],
        "historicCrests": [],
        "notes": []
    })
    property date contextLastUpdated
    property string contextGaugeId: ""
    property string inflightContextGaugeId: ""

    readonly property var requestBox:
        RiverPolicy.boundedBox(latitude, longitude, 0.6)
    readonly property bool configured: requestBox !== null
    readonly property bool loading: riverFetch.running
    readonly property bool stageflowLoading: stageflowFetch.running
    readonly property bool contextLoading: contextFetch.running
    readonly property string endpoint: {
        if (!requestBox)
            return "";
        return "https://api.water.noaa.gov/nwps/v1/gauges"
             + "?bbox.xmin=" + requestBox.xmin.toFixed(4)
             + "&bbox.ymin=" + requestBox.ymin.toFixed(4)
             + "&bbox.xmax=" + requestBox.xmax.toFixed(4)
             + "&bbox.ymax=" + requestBox.ymax.toFixed(4)
             + "&srid=EPSG_4326";
    }
    readonly property string stageflowEndpoint:
        gauge && gauge.lid
        ? "https://api.water.noaa.gov/nwps/v1/gauges/"
          + encodeURIComponent(gauge.lid) + "/stageflow"
        : ""


    function refresh() {
        if (!active || !configured || riverFetch.running)
            return false;
        riverFetch.running = true;
        return true;
    }

    function clearContext() {
        contextReady = false;
        contextFailed = false;
        contextErrorText = "";
        gaugeContext = {
            "available": false,
            "thresholds": [],
            "impacts": [],
            "recentCrests": [],
            "historicCrests": [],
            "notes": []
        };
        contextGaugeId = "";
    }

    function refreshContext() {
        if (!active || !gauge || !gauge.lid || contextFetch.running)
            return false;
        inflightContextGaugeId = String(gauge.lid);
        contextFetch.command = [
            "curl", "-fsSL", "--max-time", "12",
            "-H", "Accept: application/json",
            "-A", "Post-Apollo-WeatherStation/0.5",
            "https://api.water.noaa.gov/nwps/v1/gauges/"
              + encodeURIComponent(inflightContextGaugeId)
        ];
        contextFetch.running = true;
        return true;
    }

    function acceptContext(raw) {
        if (!gauge
                || String(gauge.lid || "") !== inflightContextGaugeId)
            return;
        try {
            gaugeContext = RiverPolicy.parseGaugeContext(
                JSON.parse(String(raw || ""))
            );
            contextGaugeId = inflightContextGaugeId;
            contextLastUpdated = new Date();
            contextReady = true;
            contextFailed = false;
            contextErrorText = "";
        } catch (error) {
            contextFailed = true;
            contextErrorText = "NWPS GAUGE CONTEXT UNAVAILABLE";
            console.log("NwpsRiverService context parse error:", error);
        }
    }

    function clearStageflow() {
        stageflowReady = false;
        stageflowFailed = false;
        stageflowErrorText = "";
        stageflow = {
            "observed": RiverPolicy.normalizeStageflowProduct(null),
            "forecast": RiverPolicy.normalizeStageflowProduct(null)
        };
        stageflowGaugeId = "";
    }

    function refreshStageflow() {
        if (!active || !gauge || !gauge.lid
                || stageflowFetch.running)
            return false;
        inflightStageflowGaugeId = String(gauge.lid);
        stageflowFetch.command = [
            "curl", "-fsSL", "--max-time", "12",
            "-H", "Accept: application/json",
            "-A", "Post-Apollo-WeatherStation/0.4",
            "https://api.water.noaa.gov/nwps/v1/gauges/"
              + encodeURIComponent(inflightStageflowGaugeId)
              + "/stageflow"
        ];
        stageflowFetch.running = true;
        return true;
    }

    function acceptStageflow(raw) {
        if (!gauge
                || String(gauge.lid || "")
                   !== inflightStageflowGaugeId)
            return;
        try {
            const parsed = RiverPolicy.parseStageflow(
                JSON.parse(String(raw || ""))
            );
            stageflow = parsed;
            stageflowGaugeId = inflightStageflowGaugeId;
            stageflowLastUpdated = new Date();
            stageflowReady = true;
            stageflowFailed = false;
            stageflowErrorText = "";
        } catch (error) {
            stageflowFailed = true;
            stageflowErrorText = "NWPS STAGEFLOW UNAVAILABLE";
            console.log("NwpsRiverService stageflow parse error:", error);
        }
    }

    function accept(raw) {
        try {
            const rows = RiverPolicy.nearestGauges(
                JSON.parse(String(raw || "")),
                latitude,
                longitude,
                4
            );
            const parsed = rows.length > 0 ? rows[0] : null;
            const nextId = parsed ? String(parsed.lid || "") : "";
            const previousId = gauge ? String(gauge.lid || "") : "";
            nearbyGauges = rows;
            gauge = parsed;
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date();

            if (nextId !== previousId) {
                clearStageflow();
                clearContext();
            }
            if (nextId !== "") {
                Qt.callLater(function() {
                    river.refreshStageflow();
                    river.refreshContext();
                });
            } else {
                clearStageflow();
                clearContext();
            }
        } catch (error) {
            failed = true;
            errorText = "NWPS GAUGE FEED UNAVAILABLE";
            console.log("NwpsRiverService parse error:", error);
        }
    }

    Process {
        id: riverFetch
        command: [
            "curl", "-fsSL", "--max-time", "12",
            "-H", "Accept: application/json",
            "-A", "Post-Apollo-WeatherStation/0.4",
            river.endpoint
        ]
        stdout: StdioCollector {
            onStreamFinished: river.accept(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                river.failed = true;
                river.errorText = "NWPS REQUEST FAILED";
            }
        }
    }

    Process {
        id: stageflowFetch
        command: []
        stdout: StdioCollector {
            onStreamFinished: river.acceptStageflow(text)
        }
        onExited: function(exitCode, exitStatus) {
            const currentId = river.gauge
                ? String(river.gauge.lid || "") : "";
            if (exitCode !== 0
                    && currentId === river.inflightStageflowGaugeId) {
                river.stageflowFailed = true;
                river.stageflowErrorText =
                    "NWPS STAGEFLOW REQUEST FAILED";
            }
            if (river.active && currentId !== ""
                    && currentId !== river.inflightStageflowGaugeId)
                Qt.callLater(function() {
                    river.refreshStageflow();
                });
        }
    }

    Process {
        id: contextFetch
        command: []
        stdout: StdioCollector {
            onStreamFinished: river.acceptContext(text)
        }
        onExited: function(exitCode, exitStatus) {
            const currentId = river.gauge
                ? String(river.gauge.lid || "") : "";
            if (exitCode !== 0
                    && currentId === river.inflightContextGaugeId) {
                river.contextFailed = true;
                river.contextErrorText =
                    "NWPS GAUGE CONTEXT REQUEST FAILED";
            }
            if (river.active && currentId !== ""
                    && currentId !== river.inflightContextGaugeId)
                Qt.callLater(function() {
                    river.refreshContext();
                });
        }
    }

    Timer {
        id: refreshClock
        interval: 900000
        repeat: true
        running: river.active && river.configured
        onTriggered: river.refresh()
    }

    Timer {
        id: locationDebounce
        interval: 250
        repeat: false
        onTriggered: river.refresh()
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
