import QtQuick
import Quickshell
import Quickshell.Io

// GROUND-only local NOAA nowCOAST lightning-density snapshot. The helper
// discovers the public WMS layer at runtime so the UI does not pin an opaque
// provider layer id. No raw Vaisala strike records are requested or stored.
Scope {
    id: lightning

    property bool active: true
    property var latitude: ""
    property var longitude: ""
    property bool usingFrameCache: false
    property string loadedKey: ""
    property string processMode: ""

    readonly property string cacheRoot:
        Quickshell.dataDir + "/weather-frame-cache-v1"

    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property string imageUrl: ""
    property string layerName: ""
    property string layerTitle: ""
    property string latestTime: ""
    property int windowMinutes: 15
    property int resolutionKm: 8
    property real radiusKm: 320
    property var bbox: null
    property date lastUpdated
    property string inflightKey: ""

    readonly property string currentKey: {
        const lat = Number(latitude);
        const lon = Number(longitude);
        if (!isFinite(lat) || !isFinite(lon)
                || lat < -90 || lat > 90 || lon < -180 || lon > 180)
            return "";
        return lat.toFixed(3) + "|" + lon.toFixed(3);
    }
    readonly property bool configured: currentKey !== ""
    readonly property bool loading:
        fetchProcess.running && processMode === "live"

    function clearLoadedState() {
        ready = false;
        failed = false;
        errorText = "";
        imageUrl = "";
        layerName = "";
        layerTitle = "";
        latestTime = "";
        windowMinutes = 15;
        resolutionKm = 8;
        radiusKm = 320;
        bbox = null;
        lastUpdated = new Date(0);
        loadedKey = "";
        usingFrameCache = false;
    }

    function loadCache() {
        if (!active || !configured || fetchProcess.running)
            return false;
        inflightKey = currentKey;
        processMode = "cache-load";
        fetchProcess.command = [
            "python3", "-B",
            Quickshell.configDir
                + "/scripts/weather/weather_frame_cache.py",
            "load-single",
            "lightning",
            cacheRoot,
            currentKey,
            "7200000"
        ];
        fetchProcess.running = true;
        return true;
    }

    function refresh() {
        if (!active || !configured || fetchProcess.running)
            return false;
        inflightKey = currentKey;
        processMode = "live";
        failed = false;
        errorText = "";
        fetchProcess.command = [
            "python3", "-B",
            Quickshell.configDir
                + "/scripts/weather/nowcoast_lightning_snapshot.py",
            String(latitude), String(longitude), cacheRoot
        ];
        fetchProcess.running = true;
        return true;
    }

    function acceptCacheResponse(raw) {
        if (!configured || currentKey !== inflightKey)
            return;
        try {
            const parsed = JSON.parse(String(raw || ""));
            const context = parsed && parsed.context ? parsed.context : {};
            if (!parsed || parsed.ok !== true
                    || String(parsed.sourceId || "") !== "lightning"
                    || String(parsed.scopeKey || "") !== currentKey
                    || !String(parsed.fileUrl || "").startsWith("file:")
                    || !context.bbox)
                return;

            imageUrl = String(parsed.fileUrl);
            layerName = String(context.layer || "");
            layerTitle = String(context.layerTitle || "");
            latestTime = String(context.latestTime || "LATEST");
            windowMinutes = Number(context.windowMinutes || 15);
            resolutionKm = Number(context.resolutionKm || 8);
            radiusKm = Number(context.radiusKm || 320);
            bbox = context.bbox;
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date(Number(parsed.receivedAtMs));
            loadedKey = currentKey;
            usingFrameCache = true;
        } catch (error) {
            // Missing/expired/corrupt cache is simply no cache.
        }
    }

    function acceptResponse(raw) {
        if (!configured || currentKey !== inflightKey)
            return;
        try {
            const parsed = JSON.parse(String(raw || ""));
            if (!parsed || parsed.error
                    || String(parsed.source || "") !== "NOAA nowCOAST"
                    || String(parsed.product || "")
                       !== "LIGHTNING STRIKE DENSITY"
                    || parsed.frameCached !== true
                    || !String(parsed.imageUrl || "").startsWith("file:")
                    || !parsed.bbox)
                throw new Error("invalid nowCOAST lightning response");

            imageUrl = String(parsed.imageUrl);
            layerName = String(parsed.layer || "");
            layerTitle = String(parsed.layerTitle || "");
            latestTime = String(parsed.latestTime || "LATEST");
            windowMinutes = Number(parsed.windowMinutes || 15);
            resolutionKm = Number(parsed.resolutionKm || 8);
            radiusKm = Number(parsed.radiusKm || 320);
            bbox = parsed.bbox;
            ready = true;
            failed = false;
            errorText = "";
            lastUpdated = new Date(Number(parsed.receivedAtMs) || Date.now());
            loadedKey = currentKey;
            usingFrameCache = false;
        } catch (error) {
            failed = true;
            errorText = "NOWCOAST LIGHTNING UNAVAILABLE";
        }
    }

    function reconcileLocation() {
        if (loadedKey !== "" && loadedKey !== currentKey)
            clearLoadedState();
        if (active && configured)
            locationDebounce.restart();
    }

    Process {
        id: fetchProcess
        command: []
        stdout: StdioCollector {
            onStreamFinished: {
                if (lightning.processMode === "cache-load")
                    lightning.acceptCacheResponse(text);
                else if (lightning.processMode === "live")
                    lightning.acceptResponse(text);
            }
        }
        onExited: function(exitCode, exitStatus) {
            const mode = lightning.processMode;
            lightning.processMode = "";

            if (mode === "live" && exitCode !== 0
                    && lightning.currentKey === lightning.inflightKey) {
                lightning.failed = true;
                lightning.errorText = "NOWCOAST LIGHTNING REQUEST FAILED";
            }

            if (!lightning.active || !lightning.configured)
                return;

            if (lightning.currentKey !== lightning.inflightKey) {
                lightning.locationDebounce.restart();
                return;
            }

            if (mode === "cache-load")
                Qt.callLater(function() { lightning.refresh(); });
        }
    }

    Timer {
        interval: 900000
        repeat: true
        running: lightning.active && lightning.configured
        onTriggered: lightning.refresh()
    }

    Timer {
        id: locationDebounce
        interval: 250
        repeat: false
        onTriggered: {
            if (!lightning.ready || lightning.loadedKey !== lightning.currentKey)
                lightning.loadCache();
            else
                lightning.refresh();
        }
    }

    onActiveChanged: {
        if (active)
            reconcileLocation();
    }
    onLatitudeChanged: reconcileLocation()
    onLongitudeChanged: reconcileLocation()
    Component.onCompleted: reconcileLocation()
}
