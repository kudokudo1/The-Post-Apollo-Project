import QtQuick
import Quickshell
import Quickshell.Io
import "SeismicPolicy.js" as SeismicPolicy

// Weather Station shared owner for recent USGS M2.5+ earthquakes.
// GROUND and MAP consume the same retained event set; no duplicate fetcher.
Scope {
    id: seismic

    property var cacheStore: null
    property bool usingPersistentCache: false
    property bool active: true
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var events: []
    property date lastUpdated

    readonly property string endpoint:
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
    readonly property bool loading: quakeFetch.running

    function hydratePersistentCache() {
        if (!cacheStore || ready)
            return false;
        const saved = cacheStore.record("seismic", Date.now());
        if (!saved || !saved.payload
                || !Array.isArray(saved.payload.events)
                || saved.payload.events.length === 0)
            return false;

        events = saved.payload.events.slice();
        lastUpdated = new Date(saved.receivedAtMs);
        ready = true;
        failed = false;
        errorText = "";
        usingPersistentCache = true;
        return true;
    }

    function persistEvents(receivedAtMs) {
        if (!cacheStore || !ready || !Array.isArray(events)
                || events.length === 0)
            return false;
        return cacheStore.put("seismic", receivedAtMs, {
            "events": events
        });
    }

    Connections {
        target: seismic.cacheStore
        enabled: !!seismic.cacheStore
        function onStorageStateChanged() {
            if (!seismic.cacheStore)
                return;
            const state = String(seismic.cacheStore.storageState || "");
            if (state === "ready" || state === "empty")
                seismic.hydratePersistentCache();
        }
    }

    function refresh() {
        if (active && !quakeFetch.running)
            quakeFetch.running = true;
    }

    function parseResponse(raw) {
        try {
            const parsed = SeismicPolicy.parseFeed(JSON.parse(raw), 100);
            events = parsed;
            lastUpdated = new Date();
            ready = true;
            failed = false;
            errorText = "";
            usingPersistentCache = false;
            persistEvents(lastUpdated.getTime());
        } catch (error) {
            failed = true;
            errorText = "USGS FEED UNAVAILABLE";
            console.log("SeismicService parse error:", error);
        }
    }

    Process {
        id: quakeFetch
        command: ["curl", "-fsSL", "--max-time", "12", seismic.endpoint]
        stdout: StdioCollector {
            onStreamFinished: seismic.parseResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0) {
                seismic.failed = true;
                seismic.errorText = "USGS REQUEST FAILED";
            }
        }
    }

    // USGS publishes frequent updates; Weather Station intentionally polls at
    // a slower 15-minute cadence only while GROUND or MAP owns seismic use.
    Timer {
        interval: 900000
        repeat: true
        running: seismic.active
        onTriggered: seismic.refresh()
    }

    onActiveChanged: {
        if (active)
            refresh();
    }
    Component.onCompleted: {
        hydratePersistentCache();
        if (active)
            refresh();
    }
}
