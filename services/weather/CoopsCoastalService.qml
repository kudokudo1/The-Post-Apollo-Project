import QtQuick
import Quickshell
import Quickshell.Io
import "CoopsCoastalPolicy.js" as CoastalPolicy

// GROUND-only coastal observations + predictions. National station catalogs
// are cached in the QML JS library for the current Quickshell session so
// remounting GROUND does not repeatedly recrawl NOAA station lists.
Scope {
    id: coastal

    property var cacheStore: null
    property var historyStore: null
    property bool waterUsingPersistentCache: false
    property bool tideUsingPersistentCache: false
    readonly property bool usingPersistentCache:
        waterUsingPersistentCache || tideUsingPersistentCache
    property string loadedKey: ""
    property bool active: true
    property var latitude: ""
    property var longitude: ""

    property bool ready: false
    property bool failed: false
    property string errorText: ""

    property var waterStation: null
    property var tideStation: null
    property var waterLevel: null
    property var tidePredictions: []

    property bool catalogReady: false
    property bool waterReady: false
    property bool tideReady: false
    property bool waterFailed: false
    property bool tideFailed: false
    property string waterErrorText: ""
    property string tideErrorText: ""
    property date lastUpdated
    property date waterLastUpdated
    property date tideLastUpdated

    property var waterCatalog: []
    property var tideCatalog: []
    property string catalogKind: ""
    property string inflightCatalogKind: ""
    property string inflightWaterKey: ""
    property string inflightTideKey: ""

    readonly property string currentKey:
        CoastalPolicy.requestKey(latitude, longitude)
    readonly property bool configured: currentKey !== ""
    readonly property bool loading:
        catalogFetch.running || waterFetch.running || tideFetch.running
    readonly property int catalogTtlMs: 86400000

    function clearLoadedState() {
        ready = false;
        failed = false;
        errorText = "";
        waterReady = false;
        tideReady = false;
        waterFailed = false;
        tideFailed = false;
        waterErrorText = "";
        tideErrorText = "";
        waterStation = null;
        tideStation = null;
        waterLevel = null;
        tidePredictions = [];
        loadedKey = "";
        waterUsingPersistentCache = false;
        tideUsingPersistentCache = false;
    }

    function hydratePersistentCache() {
        if (!cacheStore || !configured || ready)
            return false;
        const saved = cacheStore.record("coastal", Date.now(), currentKey);
        if (!saved || !saved.payload
                || !saved.payload.waterStation
                || !saved.payload.tideStation)
            return false;

        const expected = currentKey + "|"
            + String(saved.payload.waterStation.id || "") + "|"
            + String(saved.payload.tideStation.id || "");
        if (String(saved.requestKey || "") !== expected)
            return false;

        waterStation = saved.payload.waterStation;
        tideStation = saved.payload.tideStation;
        waterLevel = saved.payload.waterLevel || null;
        tidePredictions = Array.isArray(saved.payload.tidePredictions)
            ? saved.payload.tidePredictions.slice() : [];
        waterReady = !!waterLevel;
        tideReady = tidePredictions.length > 0;
        if (!waterReady && !tideReady)
            return false;

        waterLastUpdated = waterReady
            ? new Date(saved.receivedAtMs) : waterLastUpdated;
        tideLastUpdated = tideReady
            ? new Date(saved.receivedAtMs) : tideLastUpdated;
        lastUpdated = new Date(saved.receivedAtMs);
        ready = true;
        failed = false;
        errorText = "";
        loadedKey = currentKey;
        waterUsingPersistentCache = waterReady;
        tideUsingPersistentCache = tideReady;
        return true;
    }

    function persistProducts() {
        if (!cacheStore || !configured || !ready
                || !waterStation || !tideStation)
            return false;

        const waterMs = waterReady && waterLastUpdated
            ? waterLastUpdated.getTime() : -1;
        const tideMs = tideReady && tideLastUpdated
            ? tideLastUpdated.getTime() : -1;
        let receivedAtMs = Math.max(waterMs, tideMs);
        if (waterMs > 0 && tideMs > 0)
            receivedAtMs = Math.min(waterMs, tideMs);
        if (!isFinite(receivedAtMs) || receivedAtMs <= 0)
            return false;

        const requestKey = currentKey + "|"
            + String(waterStation.id || "") + "|"
            + String(tideStation.id || "");
        return cacheStore.put(
            "coastal",
            receivedAtMs,
            {
                "locationKey": currentKey,
                "waterStation": waterStation,
                "tideStation": tideStation,
                "waterLevel": waterLevel,
                "tidePredictions": tidePredictions
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
        target: coastal.cacheStore
        enabled: !!coastal.cacheStore
        function onStorageStateChanged() {
            if (!coastal.cacheStore)
                return;
            const state = String(coastal.cacheStore.storageState || "");
            if ((state === "ready" || state === "empty")
                    && coastal.configured)
                coastal.hydratePersistentCache();
        }
    }

    function catalogEndpoint(kind) {
        return "https://api.tidesandcurrents.noaa.gov/mdapi/prod/"
             + "webapi/stations.json?type=" + kind
             + "&units=english";
    }

    function curlCommand(endpoint, timeoutSeconds) {
        return [
            "curl", "-fsSL", "--max-time", String(timeoutSeconds || 12),
            "--proto", "=https", "--proto-redir", "=https",
            "-H", "Accept: application/json",
            "-A", "Post-Apollo-WeatherStation/0.7",
            endpoint
        ];
    }

    function restoreCatalogs() {
        const now = Date.now();
        waterCatalog = CoastalPolicy.cacheGet(
            "waterlevels", now, catalogTtlMs
        );
        tideCatalog = CoastalPolicy.cacheGet(
            "tidepredictions", now, catalogTtlMs
        );
        catalogReady = waterCatalog.length > 0
            && tideCatalog.length > 0;
    }

    function prepare() {
        if (!active || !configured)
            return false;
        restoreCatalogs();
        if (catalogReady) {
            selectStationsAndRefresh();
            return true;
        }
        if (!catalogFetch.running) {
            catalogKind = waterCatalog.length === 0
                ? "waterlevels" : "tidepredictions";
            inflightCatalogKind = catalogKind;
            catalogFetch.command = curlCommand(
                catalogEndpoint(catalogKind), 15
            );
            catalogFetch.running = true;
        }
        return true;
    }

    function acceptCatalog(raw) {
        const completedKind = inflightCatalogKind;
        if (completedKind !== "waterlevels"
                && completedKind !== "tidepredictions")
            return;
        try {
            const rows = CoastalPolicy.parseStationCatalog(
                JSON.parse(String(raw || ""))
            );
            CoastalPolicy.cachePut(completedKind, rows, Date.now());
            if (completedKind === "waterlevels")
                waterCatalog = rows;
            else
                tideCatalog = rows;

            if (waterCatalog.length > 0 && tideCatalog.length > 0) {
                catalogReady = true;
                failed = false;
                errorText = "";
                selectStationsAndRefresh();
            }
        } catch (error) {
            failed = true;
            errorText = "CO-OPS STATION CATALOG UNAVAILABLE";
            console.log("CoopsCoastalService catalog parse error:", error);
        }
    }

    function selectStationsAndRefresh() {
        if (!configured || !catalogReady)
            return false;
        waterStation = CoastalPolicy.nearestStation(
            waterCatalog, latitude, longitude
        );
        tideStation = CoastalPolicy.nearestStation(
            tideCatalog, latitude, longitude
        );
        return refreshProducts();
    }

    function waterEndpoint() {
        if (!waterStation)
            return "";
        return "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
             + "?date=latest"
             + "&station=" + encodeURIComponent(waterStation.id)
             + "&product=water_level"
             + "&datum=" + CoastalPolicy.observationDatum(waterStation)
             + "&time_zone=gmt"
             + "&units=english"
             + "&application=PostApolloWeatherStation"
             + "&format=json";
    }

    function tideEndpoint() {
        if (!tideStation)
            return "";
        const window = CoastalPolicy.predictionWindow(Date.now());
        if (!window.beginDate || !window.endDate)
            return "";
        return "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
             + "?begin_date=" + window.beginDate
             + "&end_date=" + window.endDate
             + "&station=" + encodeURIComponent(tideStation.id)
             + "&product=predictions"
             + "&datum=MLLW"
             + "&time_zone=gmt"
             + "&units=english"
             + "&interval=hilo"
             + "&application=PostApolloWeatherStation"
             + "&format=json";
    }

    function refreshProducts() {
        if (!active || !configured || !catalogReady)
            return false;
        let started = false;
        if (waterStation && !waterFetch.running) {
            const endpoint = waterEndpoint();
            if (endpoint !== "") {
                inflightWaterKey = currentKey + "|" + waterStation.id;
                waterFetch.command = curlCommand(endpoint, 12);
                waterFetch.running = true;
                started = true;
            }
        }
        if (tideStation && !tideFetch.running) {
            const endpoint = tideEndpoint();
            if (endpoint !== "") {
                inflightTideKey = currentKey + "|" + tideStation.id;
                tideFetch.command = curlCommand(endpoint, 12);
                tideFetch.running = true;
                started = true;
            }
        }
        return started;
    }

    function refresh() {
        if (!active || !configured)
            return false;
        restoreCatalogs();
        if (!catalogReady)
            return prepare();
        return selectStationsAndRefresh();
    }

    function captureWaterHistory(receivedAtMs) {
        if (!historyStore || !configured || !waterStation || !waterLevel)
            return false;
        return historyStore.append(
            "coastal-water",
            currentKey,
            Number(waterLevel.sampleMillis),
            receivedAtMs,
            {
                "stationId": String(waterStation.id || ""),
                "sampleMillis": Number(waterLevel.sampleMillis),
                "waterLevel": Number(waterLevel.value),
                "sigma": waterLevel.sigma,
                "quality": String(waterLevel.quality || "")
            }
        );
    }

    function acceptWater(raw) {
        if (!configured || !waterStation
                || inflightWaterKey !== currentKey + "|" + waterStation.id)
            return;
        try {
            waterLevel = CoastalPolicy.parseWaterLevel(
                JSON.parse(String(raw || ""))
            );
            waterReady = true;
            waterFailed = false;
            waterErrorText = "";
            waterLastUpdated = new Date();
            lastUpdated = waterLastUpdated;
            ready = waterReady || tideReady;
            failed = false;
            errorText = "";
            loadedKey = currentKey;
            waterUsingPersistentCache = false;
            persistProducts();
            captureWaterHistory(waterLastUpdated.getTime());
        } catch (error) {
            waterFailed = true;
            waterErrorText = "CO-OPS WATER LEVEL UNAVAILABLE";
            console.log("CoopsCoastalService water parse error:", error);
        }
    }

    function acceptTides(raw) {
        if (!configured || !tideStation
                || inflightTideKey !== currentKey + "|" + tideStation.id)
            return;
        try {
            tidePredictions = CoastalPolicy.parsePredictions(
                JSON.parse(String(raw || "")), Date.now(), 6
            );
            tideReady = true;
            tideFailed = false;
            tideErrorText = "";
            tideLastUpdated = new Date();
            lastUpdated = tideLastUpdated;
            ready = waterReady || tideReady;
            failed = false;
            errorText = "";
            loadedKey = currentKey;
            tideUsingPersistentCache = false;
            persistProducts();
        } catch (error) {
            tideFailed = true;
            tideErrorText = "CO-OPS TIDE PREDICTIONS UNAVAILABLE";
            console.log("CoopsCoastalService tide parse error:", error);
        }
    }

    Process {
        id: catalogFetch
        command: []
        stdout: StdioCollector {
            onStreamFinished: coastal.acceptCatalog(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                coastal.failed = true;
                coastal.errorText = "CO-OPS STATION CATALOG REQUEST FAILED";
            } else if (!coastal.catalogReady && coastal.active) {
                Qt.callLater(function() { coastal.prepare(); });
            }
        }
    }

    Process {
        id: waterFetch
        command: []
        stdout: StdioCollector {
            onStreamFinished: coastal.acceptWater(text)
        }
        onExited: function(exitCode, exitStatus) {
            const selectedKey = coastal.waterStation
                ? coastal.currentKey + "|" + coastal.waterStation.id : "";
            if (exitCode !== 0 && selectedKey === coastal.inflightWaterKey) {
                coastal.waterFailed = true;
                coastal.waterErrorText = "CO-OPS WATER LEVEL REQUEST FAILED";
            }
            if (coastal.active && coastal.configured
                    && selectedKey !== "" && selectedKey !== coastal.inflightWaterKey)
                Qt.callLater(function() { coastal.refreshProducts(); });
        }
    }

    Process {
        id: tideFetch
        command: []
        stdout: StdioCollector {
            onStreamFinished: coastal.acceptTides(text)
        }
        onExited: function(exitCode, exitStatus) {
            const selectedKey = coastal.tideStation
                ? coastal.currentKey + "|" + coastal.tideStation.id : "";
            if (exitCode !== 0 && selectedKey === coastal.inflightTideKey) {
                coastal.tideFailed = true;
                coastal.tideErrorText = "CO-OPS TIDE REQUEST FAILED";
            }
            if (coastal.active && coastal.configured
                    && selectedKey !== "" && selectedKey !== coastal.inflightTideKey)
                Qt.callLater(function() { coastal.refreshProducts(); });
        }
    }

    Timer {
        interval: 900000
        repeat: true
        running: coastal.active && coastal.configured && coastal.catalogReady
        onTriggered: coastal.refreshProducts()
    }

    Timer {
        id: locationDebounce
        interval: 250
        repeat: false
        onTriggered: coastal.refresh()
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
