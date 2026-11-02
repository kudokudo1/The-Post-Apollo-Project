import QtQuick
import Quickshell
import Quickshell.Io
import "RainViewerRadarPolicy.js" as RainViewerPolicy

// Manual RainViewer fallback for MAP radar. Metadata and tile plans are only
// refreshed on operator request. The latest selected tile set is cached as
// short-lived local PNG bytes so a restart can restore it without pretending
// the snapshot is live. No provider timer, no pan/zoom auto-fetch.
Scope {
    id: rainViewer

    readonly property string sourceName:
        "RAINVIEWER // PAST RADAR FALLBACK"
    readonly property string endpoint:
        "https://api.rainviewer.com/public/weather-maps.json"
    readonly property string cacheRoot:
        Quickshell.dataDir + "/weather-frame-cache-v1"
    readonly property string cacheScopeKey: "manual-radar"
    readonly property bool loading:
        metadataFetch.running || frameCacheProcess.running

    property bool metadataReady: false
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property bool usingFrameCache: false
    property string frameCacheMode: ""
    property string host: ""
    property var frames: []
    property int generated: 0
    property date lastUpdated

    property var strips: []
    property var snapshotBounds: null
    property int tileZoom: 0
    property int tileCount: 0
    property int stripCount: 0
    property int requestedHistoryMinutes: 0
    property int actualHistoryMinutes: 0
    property int selectedFrameTime: 0

    property double lastMetadataMs: 0
    property double lastRequestMs: 0
    property int pendingHistoryMinutes: 0
    property var pendingBounds: null
    property var pendingLivePlan: null
    property var pendingLiveFrame: null

    signal overlayReady()

    function metadataFresh(nowMs) {
        return metadataReady
               && lastMetadataMs > 0
               && nowMs - lastMetadataMs < 10 * 60 * 1000;
    }

    function clear() {
        strips = [];
        snapshotBounds = null;
        tileZoom = 0;
        tileCount = 0;
        stripCount = 0;
        requestedHistoryMinutes = 0;
        actualHistoryMinutes = 0;
        selectedFrameTime = 0;
        ready = false;
        failed = false;
        errorText = "";
        usingFrameCache = false;
    }

    function applyCachedOverlay(raw, fromCache) {
        try {
            const parsed = JSON.parse(String(raw || ""));
            const context = parsed && parsed.context ? parsed.context : {};
            const bounds = context.snapshotBounds;
            if (!parsed || parsed.ok !== true
                    || String(parsed.sourceId || "") !== "rainviewer"
                    || !Array.isArray(parsed.strips)
                    || parsed.strips.length === 0
                    || !bounds)
                throw new Error("invalid RainViewer frame cache");

            strips = parsed.strips;
            snapshotBounds = bounds;
            tileZoom = Math.max(0, Math.round(Number(context.tileZoom) || 0));
            tileCount = Math.max(0, Math.round(Number(context.tileCount) || 0));
            stripCount = strips.length;
            requestedHistoryMinutes =
                Math.max(0, Math.round(Number(context.requestedHistoryMinutes) || 0));
            actualHistoryMinutes =
                Math.max(0, Math.round(Number(context.actualHistoryMinutes) || 0));
            selectedFrameTime =
                Math.max(0, Math.round(Number(context.selectedFrameTime) || 0));
            lastUpdated = new Date(Number(parsed.receivedAtMs));
            ready = true;
            failed = false;
            errorText = "";
            usingFrameCache = fromCache === true;
            pendingLivePlan = null;
            pendingLiveFrame = null;
            overlayReady();
            return true;
        } catch (error) {
            return false;
        }
    }

    function loadFrameCache() {
        if (ready || frameCacheProcess.running)
            return false;
        frameCacheMode = "cache-load";
        frameCacheProcess.command = [
            "python3", "-B",
            Quickshell.configDir + "/scripts/weather/weather_frame_cache.py",
            "load-tiles",
            "rainviewer",
            cacheRoot,
            "7200000"
        ];
        frameCacheProcess.running = true;
        return true;
    }

    function cacheOverlay(plan, frame) {
        if (!plan || !plan.valid || !frame || frameCacheProcess.running)
            return false;
        frameCacheMode = "fetch";
        frameCacheProcess.command = [
            "python3", "-B",
            Quickshell.configDir + "/scripts/weather/weather_frame_cache.py",
            "fetch-tiles",
            "rainviewer",
            cacheRoot,
            cacheScopeKey,
            String(Math.max(0, Number(frame.time) * 1000 || 0)),
            JSON.stringify({
                "snapshotBounds": pendingBounds,
                "tileZoom": plan.zoom,
                "tileCount": plan.tileCount,
                "requestedHistoryMinutes": frame.requestedMinutes,
                "actualHistoryMinutes": frame.actualMinutes,
                "selectedFrameTime": frame.time
            }),
            JSON.stringify(plan.strips)
        ];
        frameCacheProcess.running = true;
        return true;
    }

    function applyRemotePlan(plan, frame) {
        if (!plan || !plan.valid || !frame)
            return false;
        snapshotBounds = JSON.parse(JSON.stringify(pendingBounds));
        strips = plan.strips;
        tileZoom = plan.zoom;
        tileCount = plan.tileCount;
        stripCount = plan.stripCount;
        requestedHistoryMinutes = frame.requestedMinutes;
        actualHistoryMinutes = frame.actualMinutes;
        selectedFrameTime = frame.time;
        ready = true;
        failed = false;
        errorText = "";
        usingFrameCache = false;
        overlayReady();
        return true;
    }

    function finalizeOverlay() {
        const frame = RainViewerPolicy.selectFrame(
            frames,
            pendingHistoryMinutes
        );
        if (!frame) {
            failed = true;
            errorText = "RAINVIEWER FRAME UNAVAILABLE";
            ready = false;
            return false;
        }

        const plan = RainViewerPolicy.buildPlan(
            pendingBounds,
            host,
            frame.path,
            9,
            4
        );
        if (!plan.valid) {
            failed = true;
            errorText = plan.reason;
            ready = false;
            return false;
        }

        pendingLivePlan = plan;
        pendingLiveFrame = frame;
        if (!cacheOverlay(plan, frame)) {
            applyRemotePlan(plan, frame);
            pendingLivePlan = null;
            pendingLiveFrame = null;
        }
        return true;
    }

    function request(minutesAgo, bounds) {
        if (metadataFetch.running || frameCacheProcess.running)
            return false;

        const requested =
            RainViewerPolicy.normalizeHistoryMinutes(minutesAgo);
        if (requested < 0) {
            failed = true;
            errorText = "RAINVIEWER HISTORY LIMITED TO 2H";
            return false;
        }
        if (!bounds || !bounds.valid) {
            failed = true;
            errorText = "RAINVIEWER MAP VIEW UNAVAILABLE";
            return false;
        }

        const now = Date.now();
        // One manual fallback frame can fan out into several cached PNG tile
        // requests. Keep loads spaced to stay comfortably below the provider
        // ceiling even if clipped strips miss Qt's shared image cache.
        if (lastRequestMs > 0 && now - lastRequestMs < 30000) {
            failed = true;
            errorText = "RAINVIEWER REQUEST COOLDOWN";
            return false;
        }

        pendingHistoryMinutes = requested;
        pendingBounds = JSON.parse(JSON.stringify(bounds));
        lastRequestMs = now;
        failed = false;
        errorText = "";

        if (metadataFresh(now))
            return finalizeOverlay();

        metadataFetch.running = true;
        return true;
    }

    function acceptMetadata(raw) {
        try {
            const parsed =
                RainViewerPolicy.parseMetadata(JSON.parse(String(raw || "")));
            host = parsed.host;
            frames = parsed.frames;
            generated = parsed.generated;
            metadataReady = true;
            lastMetadataMs = Date.now();
            lastUpdated = new Date(lastMetadataMs);
            failed = false;
            errorText = "";
            finalizeOverlay();
        } catch (error) {
            failed = true;
            if (!ready)
                ready = false;
            errorText = "RAINVIEWER METADATA UNAVAILABLE";
        }
    }

    Process {
        id: metadataFetch
        command: [
            "curl", "-fsSL", "--compressed", "--max-time", "12",
            "-A", "Post-Apollo-WeatherStation/0.1",
            rainViewer.endpoint
        ]
        stdout: StdioCollector {
            onStreamFinished: rainViewer.acceptMetadata(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && !rainViewer.failed) {
                rainViewer.failed = true;
                rainViewer.errorText = "RAINVIEWER REQUEST FAILED";
            }
        }
    }

    Process {
        id: frameCacheProcess
        command: []
        stdout: StdioCollector {
            onStreamFinished: {
                if (rainViewer.frameCacheMode === "cache-load") {
                    rainViewer.applyCachedOverlay(text, true);
                } else if (rainViewer.frameCacheMode === "fetch") {
                    if (!rainViewer.applyCachedOverlay(text, false)
                            && rainViewer.pendingLivePlan
                            && rainViewer.pendingLiveFrame) {
                        rainViewer.applyRemotePlan(
                            rainViewer.pendingLivePlan,
                            rainViewer.pendingLiveFrame
                        );
                        rainViewer.pendingLivePlan = null;
                        rainViewer.pendingLiveFrame = null;
                    }
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            const mode = rainViewer.frameCacheMode;
            rainViewer.frameCacheMode = "";
            if (mode === "fetch" && exitCode !== 0
                    && rainViewer.pendingLivePlan
                    && rainViewer.pendingLiveFrame) {
                rainViewer.applyRemotePlan(
                    rainViewer.pendingLivePlan,
                    rainViewer.pendingLiveFrame
                );
                rainViewer.pendingLivePlan = null;
                rainViewer.pendingLiveFrame = null;
            }
        }
    }

    Component.onCompleted: loadFrameCache()
}
