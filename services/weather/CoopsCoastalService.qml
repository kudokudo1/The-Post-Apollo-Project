import QtQuick
import Quickshell
import Quickshell.Io
import "CoopsCoastalPolicy.js" as CoastalPolicy

// GROUND-only coastal observations + predictions. National station catalogs
// are cached in the QML JS library for the current Quickshell session so
// remounting GROUND does not repeatedly recrawl NOAA station lists.
Scope {
    id: coastal

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
            lastUpdated = new Date();
            ready = waterReady || tideReady;
            failed = false;
            errorText = "";
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
            lastUpdated = new Date();
            ready = waterReady || tideReady;
            failed = false;
            errorText = "";
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
