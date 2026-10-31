import QtQuick
import Quickshell
import Quickshell.Io
import "CoopsCoastalPolicy.js" as CoastalPolicy

// GROUND-only coastal observations + predictions. Station capability catalogs
// are session-cached for 24h so remounting GROUND does not recrawl national
// station lists. Product refreshes target only the selected nearest stations.
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
    property string inflightKey: ""

    readonly property string currentKey:
        CoastalPolicy.requestKey(latitude, longitude)
    readonly property bool configured: currentKey !== ""
    readonly property bool loading:
        catalogFetch.running || waterFetch.running || tideFetch.running
    readonly property int catalogTtlMs: 86400000

    function catalogEndpoint(kind) {
        return "https://api.tidesandcurrents.noaa.gov/mdapi/prod/"
             + "webapi/stations.json?type=" + kind;
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
            catalogFetch.command = [
                "curl", "-fsSL", "--max-time", "15",
                "--proto", "=https", "--proto-redir", "=https",
                "-H", "Accept: application/json",
                "-A", "Post-Apollo-WeatherStation/0.6",
                catalogEndpoint(catalogKind)
            ];
            catalogFetch.running = true;
        }
        return true;
    }

    function acceptCatalog(raw) {
        try {
            const rows = CoastalPolicy.parseStationCatalog(
                JSON.parse(String(raw || ""))
            );
            CoastalPolicy.cachePut(catalogKind, rows, Date.now());
            if (catalogKind === "waterlevels")
                waterCatalog = rows;
            else if (catalogKind === "tidepredictions")
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
            return;
        waterStation = CoastalPolicy.nearestStation(
            waterCatalog, latitude, longitude
        );
        tideStation = CoastalPolicy.nearestStation(
            tideCatalog, latitude, longitude
        );
        inflightKey = currentKey;
        refreshProducts();
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
             + "&application=PostApolloWeather"
             + "&format=json";
    }

    function tideEndpoint() {
        if (!tideStation)
            return "";
        return "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
             + "?date=today"
             + "&station=" + encodeURIComponent(tideStation.id)
             + "&product=predictions"
             + "&datum=MLLW"
             + "&time_zone=gmt"
             + "&units=english"
             + "&interval=hilo"
             + "&application=PostApolloWeather"
             + "&format=json";
    }

    function refreshProducts() {
        if (!active || !configured || !catalogReady)
            return false;
        inflightKey = currentKey;
        if (waterStation && !waterFetch.running) {
            waterFetch.command = [
                "curl", "-fsSL", "--max-time", "12",
                "--proto", "=https", "--proto-redir", "=https",
                "-H", "Accept: application/json",
                "-A", "Post-Apollo-WeatherStation/0.6",
                waterEndpoint()
            ];
            waterFetch.running = true;
        }
        if (tideStation && !tideFetch.running) {
            tideFetch.command = [
                "curl", "-fsSL", "--max-time", "12",
                "--proto", "=https", "--proto-redir", "=https",
                "-H", "Accept: application/json",
                "-A", "Post-Apollo-WeatherStation/0.6",
                tideEndpoint()
            ];
            tideFetch.running = true;
        }
        return true;
    }

    function acceptWater(raw) {
        if (!configured || currentKey !== inflightKey)
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
        } catch (error) {
            waterFailed = true;
            waterErrorText = "CO-OPS WATER LEVEL UNAVAILABLE";
            console.log("CoopsCoastalService water parse error:", error);
        }
    }

    function acceptTides(raw) {
        if (!configured || currentKey !== inflightKey)
            return;
        try {
            tidePredictions = CoastalPolicy.parsePredictions(
                JSON.parse(String(raw || ""))
            );
            tideReady = true;
            tideFailed = false;
            tideErrorText = "";
            lastUpdated = new Date();
            ready = waterReady || tideReady;
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
            if (exitCode !== 0 && coastal.currentKey === coastal.inflightKey) {
                coastal.waterFailed = true;
                coastal.waterErrorText = "CO-OPS WATER LEVEL REQUEST FAILED";
            }
        }
    }

    Process {
        id: tideFetch
        command: []
        stdout: StdioCollector {
            onStreamFinished: coastal.acceptTides(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && coastal.currentKey === coastal.inflightKey) {
                coastal.tideFailed = true;
                coastal.tideErrorText = "CO-OPS TIDE REQUEST FAILED";
            }
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
        onTriggered: coastal.prepare()
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
