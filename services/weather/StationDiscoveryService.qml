import QtQuick
import Quickshell
import Quickshell.Io
import "StationDiscoveryPolicy.js" as DiscoveryPolicy

// Mounted only by the selected MAP / NEWS / RADIO page.
// No polling while the other domains are selected or the menu is closed.
Scope {
    id: discovery

    property string domain: "map"
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
        if (domain === "map")
            return "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=30";
        if (domain === "news")
            return "https://api.gdeltproject.org/api/v2/doc/doc"
                   + "?query=(weather%20OR%20earthquake%20OR%20wildfire%20OR%20aurora)"
                   + "&mode=artlist&maxrecords=30&timespan=24h&format=json";
        if (domain === "radio")
            return "https://de1.api.radio-browser.info/json/stations/topvote/30"
                   + "?hidebroken=true";
        return "";
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
    function refresh() {
        if (!active || endpoint === "" || fetchProcess.running)
            return false;
        const now = Date.now();
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
    // Update retry availability, never automatically issue a failed request.
    // This timer is active only during a limited NEWS cooldown.
    Timer {
        interval: 5000
        repeat: true
        running: discovery.active && discovery.domain === "news"
                 && discovery.retryWaitSeconds > 0
        onTriggered: discovery.sourceClockMs = Date.now()
    }
    onActiveChanged: { if (active) refresh(); }
    Component.onCompleted: {
        restoreNewsCache();
        if (active) refresh();
    }
}
