import QtQuick
import Quickshell
import Quickshell.Io

// Manual NOAA/NWS MRMS viewport frame owner with short-lived reboot cache.
// The cache stores actual PNG bytes plus the viewport metadata required to
// place them. It is operational fallback, never radar history.
Scope {
    id: radar

    property bool active: true
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property bool usingFrameCache: false
    property string processMode: ""

    property string imageUrl: ""
    property var snapshotBounds: null
    property int loadedHistoryMinutes: 0
    property double requestedTimeMs: 0
    property date lastUpdated

    readonly property string cacheRoot:
        Quickshell.dataDir + "/weather-frame-cache-v1"
    readonly property string scopeKey: "manual-radar"
    readonly property bool loading: frameProcess.running

    signal frameReady()

    function clear() {
        imageUrl = "";
        snapshotBounds = null;
        loadedHistoryMinutes = 0;
        requestedTimeMs = 0;
        ready = false;
        failed = false;
        errorText = "";
        usingFrameCache = false;
    }

    function applyFrame(raw, fromCache) {
        try {
            const parsed = JSON.parse(String(raw || ""));
            const context = parsed && parsed.context ? parsed.context : {};
            const bounds = context.bounds;
            if (!parsed || parsed.ok !== true
                    || String(parsed.sourceId || "") !== "mrms-radar"
                    || String(parsed.scopeKey || "") !== scopeKey
                    || !String(parsed.fileUrl || "").startsWith("file:")
                    || !bounds
                    || !(Number(bounds.west) < Number(bounds.east))
                    || !(Number(bounds.south) < Number(bounds.north)))
                throw new Error("invalid MRMS cache response");

            imageUrl = String(parsed.fileUrl);
            snapshotBounds = {
                "valid": true,
                "west": Number(bounds.west),
                "south": Number(bounds.south),
                "east": Number(bounds.east),
                "north": Number(bounds.north)
            };
            loadedHistoryMinutes =
                Math.max(0, Math.round(Number(context.loadedHistoryMinutes) || 0));
            requestedTimeMs = Number(parsed.observedAtMs) || 0;
            lastUpdated = new Date(Number(parsed.receivedAtMs));
            ready = true;
            failed = false;
            errorText = "";
            usingFrameCache = fromCache === true;
            frameReady();
            return true;
        } catch (error) {
            if (fromCache !== true) {
                failed = true;
                errorText = "NOAA MRMS FRAME UNAVAILABLE";
            }
            return false;
        }
    }

    function loadCache() {
        if (!active || frameProcess.running || ready)
            return false;
        processMode = "cache-load";
        frameProcess.command = [
            "python3", "-B",
            Quickshell.configDir + "/scripts/weather/weather_frame_cache.py",
            "load-single",
            "mrms-radar",
            cacheRoot,
            scopeKey,
            "7200000"
        ];
        frameProcess.running = true;
        return true;
    }

    function request(remoteUrl, bounds, historyMinutes, observedMs) {
        if (!active || frameProcess.running || !bounds)
            return false;
        const url = String(remoteUrl || "");
        if (!url.startsWith("https://mapservices.weather.noaa.gov/"))
            return false;
        const west = Number(bounds.west);
        const south = Number(bounds.south);
        const east = Number(bounds.east);
        const north = Number(bounds.north);
        if (!isFinite(west) || !isFinite(south)
                || !isFinite(east) || !isFinite(north)
                || !(west < east) || !(south < north))
            return false;

        processMode = "live";
        failed = false;
        errorText = "";
        frameProcess.command = [
            "python3", "-B",
            Quickshell.configDir + "/scripts/weather/weather_frame_cache.py",
            "fetch-single",
            "mrms-radar",
            cacheRoot,
            scopeKey,
            url,
            String(Math.max(0, Number(observedMs) || 0)),
            JSON.stringify({
                "bounds": {
                    "west": west,
                    "south": south,
                    "east": east,
                    "north": north
                },
                "loadedHistoryMinutes":
                    Math.max(0, Math.round(Number(historyMinutes) || 0))
            })
        ];
        frameProcess.running = true;
        return true;
    }

    Process {
        id: frameProcess
        command: []
        stdout: StdioCollector {
            onStreamFinished: {
                if (radar.processMode === "cache-load")
                    radar.applyFrame(text, true);
                else if (radar.processMode === "live")
                    radar.applyFrame(text, false);
            }
        }
        onExited: function(exitCode, exitStatus) {
            const mode = radar.processMode;
            radar.processMode = "";
            if (mode === "live" && exitCode !== 0) {
                radar.failed = true;
                radar.errorText = "NOAA MRMS FRAME REQUEST FAILED";
            }
        }
    }

    onActiveChanged: {
        if (active)
            loadCache();
    }
    Component.onCompleted: loadCache()
}
