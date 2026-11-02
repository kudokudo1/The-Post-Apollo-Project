import QtQuick
import Quickshell
import Quickshell.Io
import "NdbcMarinePolicy.js" as MarinePolicy

// GROUND-only nearest reporting NDBC observation. The all-station latest file
// is fetched once, then nearest selection is local. Distance is always exposed
// because "nearest marine station" is not the same thing as "local coast."
Scope {
    id: marine

    property var cacheStore: null
    property bool usingPersistentCache: false
    property string loadedKey: ""
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

    function clearLoadedState() {
        ready = false;
        failed = false;
        errorText = "";
        station = null;
        reportingStations = 0;
        loadedKey = "";
        usingPersistentCache = false;
    }

    function hydratePersistentCache() {
        if (!cacheStore || !configured || ready)
            return false;
        const saved = cacheStore.record("marine", Date.now(), currentKey);
        if (!saved || !saved.payload || !saved.payload.station)
            return false;
        const expected = currentKey + "|"
            + String(saved.payload.station.stationId || "");
        if (String(saved.requestKey || "") !== expected)
            return false;

        station = saved.payload.station;
        reportingStations = Number(saved.payload.reportingStations || 0);
        lastUpdated = new Date(saved.receivedAtMs);
        ready = true;
        failed = false;
        errorText = "";
        loadedKey = currentKey;
        usingPersistentCache = true;
        return true;
    }

    function persistStation(receivedAtMs) {
        if (!cacheStore || !ready || !station || !configured)
            return false;
        const requestKey = currentKey + "|"
            + String(station.stationId || "");
        return cacheStore.put(
            "marine",
            receivedAtMs,
            {
                "locationKey": currentKey,
                "station": station,
                "reportingStations": reportingStations
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
        target: marine.cacheStore
        enabled: !!marine.cacheStore
        function onStorageStateChanged() {
            if (!marine.cacheStore)
                return;
            const state = String(marine.cacheStore.storageState || "");
            if ((state === "ready" || state === "empty")
                    && marine.configured)
                marine.hydratePersistentCache();
        }
    }

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
            loadedKey = inflightKey;
            usingPersistentCache = false;
            persistStation(lastUpdated.getTime());
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

    // NDBC asks clients to minimize retrievals; most stations report hourly.
    // Location changes still fetch immediately, while steady-state refreshes
    // use a thirty-minute cadence.
    Timer {
        interval: 1800000
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
