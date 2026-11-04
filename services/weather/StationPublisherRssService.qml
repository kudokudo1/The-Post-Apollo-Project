import QtQuick
import Quickshell
import Quickshell.Io
import "StationPublisherRssPolicy.js" as RssPolicy

// One fixed publisher source per instance. On-demand network only.
// Cache is session-only in the policy, separately keyed per publisher.
Scope {
    id: rss

    property string feedId: ""
    property bool active: false
    property bool ready: false
    property bool usingCache: false
    property bool failed: false
    property string errorText: ""
    property var rows: []
    property date lastUpdated
    property double clockMs: Date.now()

    readonly property string publisher: RssPolicy.publisher(feedId)
    readonly property bool loading: fetchProcess.running
    readonly property int retryWaitSeconds:
        Math.ceil(RssPolicy.waitMs(feedId, clockMs) / 1000)
    readonly property bool canRequest:
        active && RssPolicy.validId(feedId) && !loading
        && retryWaitSeconds === 0
    readonly property string sourceState:
        loading ? "RECEIVING"
        : failed ? (ready ? "LAST GOOD " + rows.length + " // REQUEST FAILED"
                         : "REQUEST FAILED")
        : ready ? (usingCache ? "CACHED " : "ARTICLES ") + rows.length
        : "MANUAL READY"

    function restoreLastGood() {
        const saved = RssPolicy.snapshot(feedId);
        if (saved.updatedAtMs <= 0) return;
        rows = saved.rows;
        lastUpdated = new Date(saved.updatedAtMs);
        ready = true;
        usingCache = true;
        failed = false;
        errorText = "";
    }

    function request() {
        const now = Date.now();
        clockMs = now;
        if (!canRequest || !RssPolicy.reserve(feedId, now))
            return false;
        failed = false;
        errorText = "";
        // Fixed feed ID, no external URL, credentials or arbitrary shell input.
        fetchProcess.exec([
            "python3", "-B",
            Quickshell.configDir + "/scripts/weather/station_publisher_rss.py",
            feedId
        ]);
        return true;
    }

    function acceptResponse(raw) {
        try {
            const data = JSON.parse(String(raw || ""));
            if (!data || data.ok !== true || data.feedId !== feedId
                    || !Array.isArray(data.rows) || data.rows.length === 0)
                throw new Error("Invalid publisher RSS response");
            const now = Date.now();
            if (!RssPolicy.store(feedId, data.rows, now))
                throw new Error("Publisher RSS cache unavailable");
            rows = RssPolicy.snapshot(feedId).rows;
            lastUpdated = new Date(now);
            clockMs = now;
            ready = true;
            usingCache = false;
            failed = false;
            errorText = "";
        } catch (error) {
            failed = true;
            errorText = "PUBLISHER RSS UNAVAILABLE";
        }
    }

    Process {
        id: fetchProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: rss.acceptResponse(this.text)
        }
        onExited: function(exitCode, exitStatus) {
            rss.clockMs = Date.now();
            if (exitCode !== 0 && !rss.failed) {
                rss.failed = true;
                rss.errorText = "PUBLISHER REQUEST FAILED";
            }
        }
    }

    // Readout countdown only. It performs no requests.
    Timer {
        interval: 1000
        repeat: true
        running: rss.active && rss.retryWaitSeconds > 0
        onTriggered: rss.clockMs = Date.now()
    }

    onFeedIdChanged: restoreLastGood()
    onActiveChanged: {
        if (active && !loading)
            restoreLastGood();
    }
    Component.onCompleted: restoreLastGood()
}
