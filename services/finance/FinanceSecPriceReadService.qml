import QtQuick
import Quickshell
import Quickshell.Io

// Finance SEC M5. One historical-price request only after PRICE CONTEXT.
// Existing SEC filing index authorizes the target; no background price poller.
Scope {
    id: priceFeed
    property var secFeed: null
    property bool monitoring: false
    property string state: "idle"
    property string message: "Select a filing, then press PRICE CONTEXT."
    property var snapshot: null
    property string desiredKey: ""
    property string inFlightKey: ""
    readonly property bool loading: state === "loading"

    function clear() {
        desiredKey = "";
        snapshot = null;
        state = "idle";
        message = "Select a filing, then press PRICE CONTEXT.";
    }
    onMonitoringChanged: if (!monitoring) clear()

    function inspect(filing) {
        if (!monitoring || !secFeed || !secFeed.snapshot || !filing
                || !Array.isArray(secFeed.snapshot.filings))
            return false;
        const known = secFeed.snapshot.filings.some(function(row) {
            return row.accession === filing.accession
                && row.filedAt === filing.filedAt
                && row.form === filing.form;
        });
        if (!known || ["0000320193","0000789019","0001045810"].indexOf(secFeed.snapshot.cik) < 0
                || !/^\d{10}-\d{2}-\d{6}$/.test(filing.accession)
                || !/^\d{4}-\d{2}-\d{2}$/.test(filing.filedAt))
            return false;
        if (reader.running) {
            state = "busy";
            snapshot = null;
            message = "Previous price read in progress. Retry after it finishes.";
            return false;
        }
        const key = secFeed.snapshot.cik + "/" + filing.accession + "/" + filing.filedAt;
        desiredKey = key;
        inFlightKey = key;
        snapshot = null;
        state = "loading";
        message = "Retrieving historical daily closing prices.";
        reader.exec(["/usr/bin/env","node",
                     Quickshell.shellPath("scripts/finance/read_sec_price_optional_hub.mjs"),
                     secFeed.snapshot.cik,filing.filedAt]);
        return true;
    }

    function acceptOutput(raw) {
        if (desiredKey !== inFlightKey || !secFeed || !secFeed.snapshot)
            return;
        const lines = String(raw || "").split(/\r?\n/);
        for (let i=0;i<lines.length;i++) {
            const line=lines[i];
            if (line.indexOf("FINANCE_SEC_PRICE_ERROR ") === 0) {
                snapshot = null;
                const reason=line.slice("FINANCE_SEC_PRICE_ERROR ".length);
                state = (reason === "provider-key-required"
                         || reason === "demo-not-authorized") ? "setup" : "failed";
                message = reason === "provider-key-required"
                    ? "NVIDIA PRICE HISTORY REQUIRES AN EODHD KEY"
                    : reason === "demo-not-authorized"
                    ? "MICROSOFT DEMO ACCESS DENIED // PROVIDER KEY REQUIRED"
                    : reason === "hub-unhealthy" || reason === "hub-invalid-response"
                    ? "LOCAL MARKET HUB ERROR // NO DIRECT RETRY TO AVOID DUPLICATE REQUEST"
                    : "HISTORICAL PRICE DATA UNAVAILABLE // NO ESTIMATE DISPLAYED";
                return;
            }
            if (line.indexOf("FINANCE_SEC_PRICE ") !== 0) continue;
            try {
                const data=JSON.parse(line.slice("FINANCE_SEC_PRICE ".length));
                if (!data || data.schemaVersion !== 1 || data.source !== "eodhd-eod"
                    || data.readOnly !== true
                    || data.cik + "/" + desiredKey.split("/")[1] + "/" + data.filingDate !== desiredKey
                    || data.cik !== secFeed.snapshot.cik
                    || !["AAPL.US","MSFT.US","NVDA.US"].includes(data.symbol)
                    || !["ADJUSTED CLOSE","CLOSE"].includes(data.priceBasis)
                    || !data.delivery
                    || !["DIRECT","HUB"].includes(data.delivery.via)
                    || !["DIRECT","FETCHED","CACHED","SHARED"].includes(data.delivery.state)
                    || typeof data.delivery.servedAt !== "string"
                    || !Number.isFinite(Date.parse(data.delivery.servedAt))
                    || (data.delivery.via === "HUB"
                        && (!["FETCHED","CACHED","SHARED"].includes(data.delivery.state)
                            || typeof data.delivery.cachedAt !== "string"
                            || !Number.isFinite(Date.parse(data.delivery.cachedAt))))
                    || (data.delivery.via === "DIRECT" && data.delivery.state !== "DIRECT")
                    || !Array.isArray(data.bars) || data.bars.length > 32
                    || !data.bars.every(function(bar) {
                        return bar && /^\d{4}-\d{2}-\d{2}$/.test(bar.date)
                            && typeof bar.price === "number"
                            && Number.isFinite(bar.price) && bar.price > 0;
                    })
                    || (data.changePct !== null && (!Number.isFinite(data.changePct)
                        || Math.abs(data.changePct) > 1e7)))
                    throw new Error("invalid-market-snapshot");
                // The selection must still be in this issuer's current SEC index.
                if (!secFeed.snapshot.filings.some(function(f) {
                    return f.accession === desiredKey.split("/")[1]
                        && f.filedAt === data.filingDate;
                })) throw new Error("stale-filing");
                snapshot = data;
                state = "ready";
                const delivery = data.delivery.via === "HUB"
                    ? "MARKET HUB " + data.delivery.state : "DIRECT EODHD";
                message = data.previous && data.next
                    ? delivery + " // DATED PRICE COMPARISON // NOT CAUSAL"
                    : delivery + " // PARTIAL PRICE HISTORY";
            } catch (error) {
                snapshot = null;
                state = "failed";
                message = "Invalid historical price response.";
            }
            return;
        }
    }

    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: priceFeed.acceptOutput(text)
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                if (priceFeed.state === "loading") {
                    priceFeed.snapshot = null;
                    priceFeed.state = "failed";
                    priceFeed.message = "Historical price read failed.";
                }
            });
        }
    }
}
