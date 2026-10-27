import QtQuick
import Quickshell
import Quickshell.Io
import "StationDiscoveryPolicy.js" as DiscoveryPolicy

// Mounted only by the selected MAP / NEWS / RADIO page.
// No polling while the other domains are selected or the menu is closed.
Scope {
    id: discovery

    property string domain: "map"
    property string mapCategory: ""
    property bool active: true
    property bool ready: false
    property bool usingCache: false
    property bool failed: false
    property string errorText: ""
    property var rows: []
    property date lastUpdated

    property double sourceClockMs: Date.now()
    readonly property bool loading: fetchProcess.running
    readonly property int retryWaitSeconds:
        domain === "news"
        ? Math.ceil(DiscoveryPolicy.newsWaitMs(sourceClockMs) / 1000) : 0
    readonly property bool canRetry:
        active && !loading && retryWaitSeconds === 0
    readonly property string endpoint: {
        if (domain === "map") {
            const category = String(mapCategory || "").trim();
            return "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=40"
                   + (category !== "" ? "&category=" + category : "");
        }
        if (domain === "news")
            return "https://api.gdeltproject.org/api/v2/doc/doc"
                   + "?query=(weather%20OR%20earthquake%20OR%20wildfire%20OR%20aurora)"
                   + "&mode=artlist&maxrecords=30&timespan=24h&format=json";
        if (domain === "radio")
            return "https://de1.api.radio-browser.info/json/stations/topvote/30"
                   + "?hidebroken=true";
        return "";
    }
    function restoreMapCache(allowRefresh) {
        if (domain !== "map")
            return false;
        const snapshot = DiscoveryPolicy.cachedMapRows(mapCategory, Date.now());
        if (snapshot.updatedAtMs <= 0)
            return false;
        rows = snapshot.rows;
        lastUpdated = new Date(snapshot.updatedAtMs);
        ready = true;
        usingCache = true;
        failed = false;
        errorText = "";
        if (allowRefresh && !snapshot.fresh)
            Qt.callLater(function() { discovery.refresh(); });
        return snapshot.fresh;
    }

    function changeMapCategory() {
        if (domain !== "map" || fetchProcess.running)
            return;
        const snapshot = DiscoveryPolicy.cachedMapRows(mapCategory, Date.now());
        if (snapshot.updatedAtMs > 0) {
            rows = snapshot.rows;
            lastUpdated = new Date(snapshot.updatedAtMs);
            ready = true;
            usingCache = true;
            failed = false;
            errorText = "";
            if (snapshot.fresh)
                return;
        } else {
            rows = [];
            ready = false;
            usingCache = false;
            failed = false;
            errorText = "";
        }
        refresh();
    }

    function restoreNewsCache() {
        if (domain !== "news") return;
        const snapshot = DiscoveryPolicy.cachedNewsRows();
        if (snapshot.updatedAtMs > 0) {
            rows = snapshot.rows;
            lastUpdated = new Date(snapshot.updatedAtMs);
            ready = true;
            usingCache = true;
        }
    }
    function refresh(manual) {
        if (!active || endpoint === "" || fetchProcess.running)
            return false;
        const now = Date.now();
        // After a 429, do not auto-retry on tab remount or the periodic timer.
        // Only an explicit operator click may attempt another fetch when due.
        if (domain === "news"
                && !manual && DiscoveryPolicy.newsManualRetryRequired()) {
            sourceClockMs = now;
            failed = true;
            errorText = "RATE LIMITED";
            return false;
        }
        sourceClockMs = now;
        if (domain === "news" && !DiscoveryPolicy.reserveNewsRequest(now)) {
            if (DiscoveryPolicy.newsThrottled(now)) {
                failed = true;
                errorText = "RATE LIMITED";
            } else if (!ready) {
                failed = false;
                errorText = "";
            }
            return false;
        }
        failed = false;
        errorText = "";
        fetchProcess.running = true;
        return true;
    }
    function parseResponse(rawText) {
        const received = DiscoveryPolicy.splitHttpResponse(rawText);
        const now = Date.now();
        sourceClockMs = now;
        if (received.status === 429) {
            if (domain === "news")
                DiscoveryPolicy.recordNewsThrottle(now);
            failed = true;
            errorText = "RATE LIMITED";
            // _newsNextAllowedMs is shared JS state, not a notifying QML
            // property. Force an observable clock write after changing it.
            sourceClockMs = Date.now();
            return;
        }
        if (received.status < 200 || received.status >= 300) {
            failed = true;
            errorText = received.status
                        ? "HTTP " + received.status + " // SOURCE FAILED"
                        : "SOURCE RESPONSE UNAVAILABLE";
            return;
        }
        try {
            const parsed = DiscoveryPolicy.parse(domain, JSON.parse(received.body));
            rows = parsed;
            ready = true;
            usingCache = false;
            failed = false;
            errorText = "";
            lastUpdated = new Date(now);
            if (domain === "map")
                DiscoveryPolicy.storeMapRows(mapCategory, parsed, now);
            if (domain === "news")
                DiscoveryPolicy.storeNewsRows(parsed, now);
        } catch (error) {
            failed = true;
            errorText = "SOURCE RESPONSE UNAVAILABLE";
            console.log("StationDiscoveryService", domain, error);
        }
    }
    Process {
        id: fetchProcess
        // Preserve HTTP error responses (not -f): distinguish 429 from
        // malformed JSON and from connection failure without retry storms.
        command: ["curl", "-sSL", "--compressed", "--max-time", "14",
                  "-w", "\\n__POST_APOLLO_HTTP__:%{http_code}",
                  "-A", "Post-Apollo-WeatherStation/0.1", discovery.endpoint]
        stdout: StdioCollector {
            onStreamFinished: discovery.parseResponse(text)
        }
        onExited: function(exitCode, exitStatus) {
            discovery.sourceClockMs = Date.now();
            if (exitCode !== 0 && !discovery.failed) {
                discovery.failed = true;
                discovery.errorText = "SOURCE REQUEST FAILED";
            }
        }
    }
    Timer {
        interval: 900000
        repeat: true
        running: discovery.active
        onTriggered: discovery.refresh()
    }
    // Always tick while NEWS is visible. A timer gated by retryWaitSeconds
    // can stop when the countdown reaches zero, or fail to restart because
    // the underlying pragma-library deadline does not send QML change signals.
    // A steady one-second clock drives the panel and header independently
    // of switching modes, with *no* network requests in this timer.
    Timer {
        interval: 1000
        repeat: true
        running: discovery.active && discovery.domain === "news"
        onTriggered: discovery.sourceClockMs = Date.now()
    }
    onActiveChanged: {
        if (!active)
            return;
        if (domain === "map" && restoreMapCache(false))
            return;
        refresh();
    }

    onMapCategoryChanged: {
        if (domain === "map")
            changeMapCategory();
    }

    Component.onCompleted: {
        const mapFresh = restoreMapCache(false);
        restoreNewsCache();
        if (domain === "news" && DiscoveryPolicy.newsManualRetryRequired()) {
            // Preserve the provider refusal across page reconstruction.
            failed = true;
            errorText = "RATE LIMITED";
            sourceClockMs = Date.now();
        } else if (active && !(domain === "map" && mapFresh)) {
            refresh();
        }
    }
}
