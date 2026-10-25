import QtQuick
import Quickshell
import Quickshell.Io

// Market STOCKS M9: manual historical EOD reference-date lookup.
// Reuses the exact M8 optional-hub adapter, shared cache and provider gates.
// A reference date here is NOT asserted to be an SEC filing date.
Scope {
    id: stockFeed
    property bool monitoring: false
    property string selectedCik: "0000320193"
    property string referenceDate: defaultReferenceDate()
    property string state: "idle"
    property string message: "Choose an issuer and reference date, then LOAD HISTORY."
    property var snapshot: null
    property string desiredKey: ""
    property string inFlightKey: ""
    readonly property bool loading: state === "loading"
    readonly property bool ready: state === "ready" && snapshot !== null

    function defaultReferenceDate() {
        const date = new Date();
        date.setUTCDate(date.getUTCDate() - 14);
        return date.toISOString().slice(0, 10);
    }
    function validDate(value) {
        if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
            return false;
        const date = new Date(value + "T00:00:00Z");
        return !isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
    }
    function clear() {
        desiredKey = "";
        snapshot = null;
        state = "idle";
        message = "Choose an issuer and reference date, then LOAD HISTORY.";
    }
    onMonitoringChanged: {
        if (!monitoring) clear();
    }
    function selectIssuer(cik) {
        if (["0000320193","0000789019","0001045810"].indexOf(cik) < 0)
            return false;
        if (selectedCik !== cik) {
            selectedCik = cik;
            clear();
        }
        return true;
    }
    function selectReferenceDate(day) {
        if (!validDate(day) || day > new Date().toISOString().slice(0,10)
                || day < "2000-01-01")
            return false;
        if (referenceDate !== day) {
            referenceDate = day;
            clear();
        }
        return true;
    }
    function refresh() {
        if (!monitoring || !validDate(referenceDate)
                || referenceDate > new Date().toISOString().slice(0,10)
                || referenceDate < "2000-01-01"
                || ["0000320193","0000789019","0001045810"].indexOf(selectedCik) < 0)
            return false;
        if (reader.running) {
            state = "busy";
            snapshot = null;
            message = "Previous stock history request is still running.";
            return false;
        }
        const key = selectedCik + "/" + referenceDate;
        desiredKey = key;
        inFlightKey = key;
        snapshot = null;
        state = "loading";
        message = "Reading dated daily market history.";
        reader.exec(["/usr/bin/env","node",
                     Quickshell.shellPath("scripts/finance/read_sec_price_optional_hub.mjs"),
                     selectedCik,referenceDate]);
        return true;
    }
    function acceptOutput(raw) {
        if (desiredKey !== inFlightKey || !monitoring)
            return;
        const lines = String(raw || "").split(/\r?\n/);
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.indexOf("FINANCE_SEC_PRICE_ERROR ") === 0) {
                const reason = line.slice("FINANCE_SEC_PRICE_ERROR ".length);
                snapshot = null;
                state = reason === "provider-key-required"
                    || reason === "demo-not-authorized" ? "setup" : "failed";
                message = reason === "provider-key-required"
                    ? "PROVIDER KEY REQUIRED // NO NVIDIA DEMO ACCESS"
                    : reason === "demo-not-authorized"
                    ? "MICROSOFT DEMO DENIED // PROVIDER KEY REQUIRED"
                    : reason === "hub-unhealthy" || reason === "hub-invalid-response"
                    ? "LOCAL MARKET HUB ERROR // NO AUTOMATIC DIRECT RETRY"
                    : "HISTORICAL STOCK DATA UNAVAILABLE";
                return;
            }
            if (line.indexOf("FINANCE_SEC_PRICE ") !== 0) continue;
            try {
                const data = JSON.parse(line.slice("FINANCE_SEC_PRICE ".length));
                const symbols = {
                    "0000320193": "AAPL.US",
                    "0000789019": "MSFT.US",
                    "0001045810": "NVDA.US"
                };
                if (!data || data.schemaVersion !== 1
                    || data.source !== "eodhd-eod" || data.readOnly !== true
                    || data.cik !== selectedCik
                    || data.filingDate !== referenceDate
                    || desiredKey !== selectedCik + "/" + referenceDate
                    || data.symbol !== symbols[selectedCik]
                    || !["CLOSE","ADJUSTED CLOSE"].includes(data.priceBasis)
                    || !data.delivery
                    || !["DIRECT","HUB"].includes(data.delivery.via)
                    || !["DIRECT","FETCHED","CACHED","SHARED"].includes(data.delivery.state)
                    || (data.delivery.via === "DIRECT" && data.delivery.state !== "DIRECT")
                    || (data.delivery.via === "HUB"
                        && !["FETCHED","CACHED","SHARED"].includes(data.delivery.state))
                    || typeof data.delivery.servedAt !== "string"
                    || !Number.isFinite(Date.parse(data.delivery.servedAt))
                    || (data.delivery.via === "HUB"
                        && (typeof data.delivery.cachedAt !== "string"
                            || !Number.isFinite(Date.parse(data.delivery.cachedAt))))
                    || !Array.isArray(data.bars) || data.bars.length < 1
                    || data.bars.length > 32
                    || !data.bars.every(function(bar) {
                        return bar && typeof bar.date === "string"
                            && /^\d{4}-\d{2}-\d{2}$/.test(bar.date)
                            && typeof bar.price === "number"
                            && Number.isFinite(bar.price) && bar.price > 0;
                    })
                    || (data.changePct !== null && (!Number.isFinite(data.changePct)
                        || Math.abs(data.changePct) > 1e7)))
                    throw new Error("invalid-stock-response");
                snapshot = data;
                state = "ready";
                message = "DAILY CLOSING HISTORY // "
                    + (data.delivery.via === "HUB"
                        ? "MARKET HUB " + data.delivery.state : "DIRECT EODHD");
            } catch (error) {
                snapshot = null;
                state = "failed";
                message = "Invalid stock history response.";
            }
            return;
        }
    }
    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: stockFeed.acceptOutput(text)
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                if (stockFeed.state === "loading") {
                    stockFeed.snapshot = null;
                    stockFeed.state = "failed";
                    stockFeed.message = "Stock history read did not finish.";
                }
            });
        }
    }
}
