import QtQuick
import Quickshell
import Quickshell.Io

// M1 public read-only Market feed. Never starts at shell boot or polls.
// One child process per explicit refresh / first opened Market view.
Scope {
    id: marketFeed
    property bool monitoring: false
    property string state: "idle"
    property string message: "Open Market or press REFRESH."
    property var snapshot: null
    readonly property bool loading: state === "loading"
    readonly property bool live: state === "ready" && snapshot !== null
    onMonitoringChanged: {
        if (monitoring && state === "idle")
            refresh();
    }

    function refresh() {
        if (!monitoring || reader.running || loading)
            return false;
        snapshot = null;
        state = "loading";
        message = "Reading public Polymarket markets.";
        reader.exec(["/usr/bin/env", "node",
                     Quickshell.shellPath("scripts/finance/read_polymarket.mjs")]);
        return true;
    }

    function acceptOutput(raw) {
        const lines = String(raw || "").split(/\r?\n/);
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.indexOf("FINANCE_MARKET_ERROR ") === 0) {
                state = "failed";
                message = "Public market feed unavailable. Use REFRESH to retry.";
                snapshot = null;
                return;
            }
            if (line.indexOf("FINANCE_MARKET_SNAPSHOT ") !== 0)
                continue;
            try {
                const payload = JSON.parse(line.slice("FINANCE_MARKET_SNAPSHOT ".length));
                if (!payload || payload.schemaVersion !== 1
                        || payload.source !== "polymarket-gamma"
                        || payload.readOnly !== true
                        || typeof payload.retrievedAt !== "string"
                        || !Array.isArray(payload.markets)
                        || payload.markets.length > 24
                        || !payload.markets.every(function(m) {
                            return m && typeof m.id === "string"
                                && /^[0-9]{1,24}$/.test(m.id)
                                && typeof m.question === "string"
                                && m.question.length <= 180
                                && typeof m.yesPct === "number"
                                && m.yesPct >= 0 && m.yesPct <= 100
                                && typeof m.noPct === "number"
                                && m.noPct >= 0 && m.noPct <= 100
                                && (m.volume24h === null || Number.isSafeInteger(m.volume24h))
                                && (m.liquidity === null || Number.isSafeInteger(m.liquidity))
                                && (m.change24hPct === null
                                    || (typeof m.change24hPct === "number"
                                        && m.change24hPct >= -100 && m.change24hPct <= 100));
                        }))
                    throw new Error("format");
                snapshot = payload;
                state = "ready";
                message = payload.markets.length
                    ? "Public snapshot. Not a live trading connection."
                    : "No eligible binary markets in this sample.";
            } catch {
                snapshot = null;
                state = "failed";
                message = "Unexpected market-data format.";
            }
            return;
        }
    }

    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: marketFeed.acceptOutput(text)
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                if (marketFeed.state === "loading") {
                    marketFeed.state = "failed";
                    marketFeed.message = "Could not retrieve public market data.";
                    marketFeed.snapshot = null;
                }
            });
        }
    }
}
