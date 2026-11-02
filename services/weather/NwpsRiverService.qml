import QtQuick
import Quickshell
import Quickshell.Io
import "NwpsRiverPolicy.js" as RiverPolicy

// Weather-fix informational nearby river gauge lookup shared by GROUND and
// MAP. The Weather location is used only to find nearby NWPS gauges; this
// service is not an emergency alert target and never replaces the explicitly
// pinned NWS alert point.
Scope {
    id: river

    property var cacheStore: null
    property bool baseUsingPersistentCache: false
    property bool stageflowUsingPersistentCache: false
    property bool contextUsingPersistentCache: false
    readonly property bool usingPersistentCache:
        baseUsingPersistentCache
        || stageflowUsingPersistentCache
        || contextUsingPersistentCache
    property string loadedKey: ""
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

    readonly property string currentKey:
        RiverPolicy.requestKey(latitude, longitude)
    readonly property var requestBox:
        RiverPolicy.boundedBox(latitude, longitude, 0.6)
    readonly property bool configured:
        currentKey !== "" && requestBox !== null
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


    function clearLoadedState() {
        ready = false;
        failed = false;
        errorText = "";
        gauge = null;
        nearbyGauges = [];
        loadedKey = "";
        baseUsingPersistentCache = false;
        clearStageflow();
        clearContext();
    }

    function hydratePersistentCache() {
        if (!cacheStore || !configured || ready)
            return false;
        const saved = cacheStore.record("river", Date.now(), currentKey);
        if (!saved || !saved.payload || !saved.payload.gauge)
            return false;

        const expected = currentKey + "|"
            + String(saved.payload.gauge.lid || "");
        if (String(saved.requestKey || "") !== expected)
            return false;

        gauge = saved.payload.gauge;
        nearbyGauges = Array.isArray(saved.payload.nearbyGauges)
            ? saved.payload.nearbyGauges.slice() : [];
        stageflow = saved.payload.stageflow || {
            "observed": RiverPolicy.normalizeStageflowProduct(null),
            "forecast": RiverPolicy.normalizeStageflowProduct(null)
        };
        stageflowGaugeId = String(saved.payload.stageflowGaugeId || "");
        gaugeContext = saved.payload.gaugeContext || {
            "available": false,
            "thresholds": [],
            "impacts": [],
            "recentCrests": [],
            "historicCrests": [],
            "notes": []
        };
        contextGaugeId = String(saved.payload.contextGaugeId || "");

        lastUpdated = new Date(saved.receivedAtMs);
        ready = true;
        failed = false;
        errorText = "";
        loadedKey = currentKey;
        baseUsingPersistentCache = true;

        stageflowReady = stageflowGaugeId === String(gauge.lid || "")
            && ((stageflow.observed && stageflow.observed.available)
                || (stageflow.forecast && stageflow.forecast.available));
        if (stageflowReady) {
            stageflowLastUpdated = new Date(saved.receivedAtMs);
            stageflowUsingPersistentCache = true;
        }

        contextReady = contextGaugeId === String(gauge.lid || "")
            && gaugeContext && gaugeContext.available === true;
        if (contextReady) {
            contextLastUpdated = new Date(saved.receivedAtMs);
            contextUsingPersistentCache = true;
        }
        return true;
    }

    function persistRiver() {
        if (!cacheStore || !configured || !ready || !gauge
                || !lastUpdated)
            return false;
        const receivedAtMs = lastUpdated.getTime();
        if (!isFinite(receivedAtMs) || receivedAtMs <= 0)
            return false;
        const requestKey = currentKey + "|" + String(gauge.lid || "");
        return cacheStore.put(
            "river",
            receivedAtMs,
            {
                "locationKey": currentKey,
                "gauge": gauge,
                "nearbyGauges": nearbyGauges,
                "stageflow": stageflowUsingPersistentCache
                             ? null : stageflow,
                "stageflowGaugeId": stageflowUsingPersistentCache
                                    ? "" : stageflowGaugeId,
                "gaugeContext": contextUsingPersistentCache
                                ? null : gaugeContext,
                "contextGaugeId": contextUsingPersistentCache
                                  ? "" : contextGaugeId
            },
            currentKey,
            requestKey
        );
    }

    function reconcileLocationKey() {
        if (loadedKey !== "" && loadedKey !== currentKey)
            clearLoadedState();
        if (configured)
            hydratePersistentCache();
        if (active && configured)
            locationDebounce.restart();
    }

    Connections {
        target: river.cacheStore
        enabled: !!river.cacheStore
        function onStorageStateChanged() {
            if (!river.cacheStore)
                return;
            const state = String(river.cacheStore.storageState || "");
            if ((state === "ready" || state === "empty")
                    && river.configured)
                river.hydratePersistentCache();
        }
    }

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
        contextUsingPersistentCache = false;
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
            contextUsingPersistentCache = false;
            persistRiver();
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
        stageflowUsingPersistentCache = false;
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
            stageflowUsingPersistentCache = false;
            persistRiver();
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
            loadedKey = currentKey;
            baseUsingPersistentCache = false;

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
            persistRiver();
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
        if (active && configured) {
            hydratePersistentCache();
            locationDebounce.restart();
        }
    }
    onCurrentKeyChanged: reconcileLocationKey()
    Component.onCompleted: {
        hydratePersistentCache();
        if (active && configured)
            locationDebounce.restart();
    }
}
