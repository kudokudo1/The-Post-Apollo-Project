import QtQuick
import Quickshell
import Quickshell.Io

// FinanceW Research M1: read-only bridge to a saved local Scrapy JSON export.
// Does not launch Scrapy, enter Toolbox, poll the network, or write files.
Scope {
    id: crawlFeed
    property bool monitoring: false
    property string state: "idle"
    property string message: "Open RESEARCH to inspect the saved crawl."
    property var snapshot: null
    readonly property bool loading: state === "loading"

    onMonitoringChanged: {
        if (monitoring && state === "idle")
            refresh();
    }

    function refresh() {
        if (!monitoring || reader.running || loading)
            return false;
        snapshot = null;
        state = "loading";
        message = "Reading saved Scrapy crawl.";
        reader.exec(["/usr/bin/env", "node",
                     Quickshell.shellPath("scripts/finance/read_scrapy_crawl.mjs")]);
        return true;
    }

    function acceptOutput(raw) {
        const lines = String(raw || "").split(/\r?\n/);
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.indexOf("FINANCE_CRAWL_ERROR ") === 0) {
                snapshot = null;
                state = "missing";
                message = line.indexOf("missing-export") >= 0
                    ? "NO SAVED CRAWL // RUN THE TOOLBOX SPIDER FIRST"
                    : "INVALID CRAWL FILE // CHECK EXPORT";
                return;
            }
            if (line.indexOf("FINANCE_CRAWL_SNAPSHOT ") !== 0)
                continue;
            try {
                const payload = JSON.parse(line.slice("FINANCE_CRAWL_SNAPSHOT ".length));
                if (!payload || payload.schemaVersion !== 1
                        || payload.source !== "finance-demo-scrapy"
                        || payload.readOnly !== true
                        || !Array.isArray(payload.pages)
                        || payload.pages.length > 6
                        || payload.pageCount !== payload.pages.length
                        || !Number.isSafeInteger(payload.linkCount)
                        || payload.linkCount < 0 || payload.linkCount > 192
                        || !payload.pages.every(function(p) {
                            return p && typeof p.url === "string"
                                && p.url.indexOf("https://quotes.toscrape.com/") === 0
                                && typeof p.title === "string" && p.title.length <= 150
                                && typeof p.snippet === "string" && p.snippet.length <= 450
                                && typeof p.observedAt === "string"
                                && Array.isArray(p.links) && p.links.length <= 32
                                && p.links.every(function(link) {
                                    return typeof link === "string"
                                        && link.indexOf("https://quotes.toscrape.com/") === 0;
                                });
                        }))
                    throw new Error("bad snapshot");
                snapshot = payload;
                state = "ready";
                message = payload.pages.length
                    ? "SAVED CRAWL // NOT A LIVE SOURCE"
                    : "EMPTY CRAWL // CHECK ROBOTS AND NETWORK";
            } catch (error) {
                snapshot = null;
                state = "failed";
                message = "Could not validate saved crawl.";
            }
            return;
        }
    }

    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: crawlFeed.acceptOutput(text)
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                if (crawlFeed.state === "loading") {
                    crawlFeed.state = "failed";
                    crawlFeed.message = "Could not read local Scrapy data.";
                    crawlFeed.snapshot = null;
                }
            });
        }
    }
}
