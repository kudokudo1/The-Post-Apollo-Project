import QtQuick
import Quickshell
import Quickshell.Io
import "../../widgets/FinanceStockModePolicy.js" as StockModePolicy

// Finance M14: bounded in-memory DAY -> RANGE restoration, no implicit reads.
// Still uses the M10 bounded historical-range endpoint for both modes.
Scope {
    id: stockFeed
    property bool monitoring: false
    property string selectedCik: "0000320193"
    property string displayMode: "range"
    property string dayDate: dateOffset(-1)
    property string startDate: dateOffset(-30)
    property string endDate: dateOffset(0)
    property string state: "idle"
    property string message: "Select issuer, START and END dates, then LOAD RANGE."
    property var snapshot: null
    // One ephemeral return ticket, valid only after OPEN IN DAY. Never persisted.
    property var returnTicket: null
    readonly property bool canReturnToRange: monitoring && ready
        && displayMode === "day" && snapshot !== null
        && snapshot.derivedFromRange === true && returnTicket !== null
        && snapshot.from === dayDate
        && returnTicket.cik === selectedCik
        && returnTicket.openedDay === dayDate
        && returnTicket.from === startDate && returnTicket.to === endDate
        && StockModePolicy.selectWindow(
            "range", dayDate, startDate, endDate, dateOffset(0)) !== null
        && !reader.running
    property string desiredKey: ""
    property string inFlightKey: ""
    readonly property bool loading: state === "loading"
    readonly property bool ready: state === "ready" && snapshot !== null
    readonly property int rangeDays: validDate(startDate) && validDate(endDate)
        ? Math.round((new Date(endDate + "T00:00:00Z").getTime()
                      - new Date(startDate + "T00:00:00Z").getTime()) / 86400000)
        : -1
    readonly property var activeWindow: StockModePolicy.selectWindow(
        displayMode, dayDate, startDate, endDate, dateOffset(0))
    readonly property bool validSelection: activeWindow !== null
        && ["0000320193","0000789019","0001045810"].indexOf(selectedCik) >= 0

    function dateOffset(days) {
        const day = new Date();
        day.setUTCDate(day.getUTCDate() + days);
        return day.toISOString().slice(0,10);
    }
    function validDate(day) {
        if (typeof day !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(day))
            return false;
        const date = new Date(day + "T00:00:00Z");
        return !isNaN(date.getTime()) && date.toISOString().slice(0,10) === day;
    }
    function clear() {
        returnTicket = null;
        desiredKey = "";
        snapshot = null;
        state = "idle";
        message = "Select issuer, START and END dates, then LOAD RANGE.";
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
    function selectMode(nextMode) {
        if (nextMode !== "day" && nextMode !== "range") return false;
        if (displayMode !== nextMode) {
            displayMode = nextMode;
            clear();
        }
        return true;
    }
    function selectDayDate(day) {
        if (!validDate(day) || day < "2000-01-01"
                || day > dateOffset(0)) return false;
        if (dayDate !== day) {dayDate=day;clear();}
        return true;
    }
    // Explicit RANGE -> DAY handoff from already-validated trading-session
    // history. No reader.exec(), provider request, cache mutation or reload.
    // RANGE's start/end date selections remain untouched.
    function openRangePointInDay(index, expectedDate) {
        if (!monitoring || !ready || loading || reader.running
                || displayMode !== "range" || !validSelection
                || !activeWindow || !snapshot || !Number.isInteger(index))
            return false;
        const day = StockModePolicy.daySnapshotFromRange(
            snapshot, index, selectedCik, activeWindow.from, activeWindow.to);
        if (!day || day.from !== expectedDate) return false;
        const ticket = StockModePolicy.rangeReturnTicket(
            snapshot, index, selectedCik, activeWindow.from, activeWindow.to);
        if (!ticket || ticket.openedDay !== expectedDate) return false;
        returnTicket = ticket;
        dayDate = day.from;
        displayMode = "day";
        desiredKey = "";
        inFlightKey = "";
        snapshot = day;
        state = "ready";
        message = "DAY CLOSE FROM LOADED RANGE // NO NEW MARKET REQUEST";
        return true;
    }
    // Explicit BACK TO RANGE restores a previously fetched bounded RANGE
    // snapshot, without querying the provider or recalculating prices.
    function returnToRange() {
        if (!canReturnToRange || loading || reader.running) return false;
        const restored = StockModePolicy.rangeFromReturnTicket(
            returnTicket, snapshot, selectedCik, startDate, endDate);
        if (!restored) {
            returnTicket = null;
            return false;
        }
        returnTicket = null;
        displayMode = "range";
        desiredKey = "";
        inFlightKey = "";
        snapshot = restored;
        state = "ready";
        message = "RANGE RESTORED FROM MEMORY // NO NEW MARKET REQUEST";
        return true;
    }
    function selectStartDate(day) {
        if (!validDate(day) || day < "2000-01-01"
                || day > dateOffset(0)) return false;
        if (startDate !== day) {startDate=day;clear();}
        return true;
    }
    function selectEndDate(day) {
        if (!validDate(day) || day < "2000-01-01"
                || day > dateOffset(0)) return false;
        if (endDate !== day) {endDate=day;clear();}
        return true;
    }
    function refresh() {
        if (!monitoring || !validSelection) {
            snapshot = null;
            state = "invalid";
            message = displayMode === "day"
                ? "SELECT A VALID PAST OR PRESENT CALENDAR DAY."
                : "SELECT AN ORDERED RANGE OF 0 TO 180 CALENDAR DAYS.";
            return false;
        }
        if (reader.running) {
            state = "busy";
            snapshot = null;
            message = "Previous history request is still running.";
            return false;
        }
        // Any manual provider read invalidates the one-step return ticket.
        returnTicket = null;
        const from=activeWindow.from, to=activeWindow.to;
        const key=displayMode+"/"+selectedCik+"/"+from+"/"+to;
        desiredKey=key;
        inFlightKey=key;
        snapshot=null;
        state="loading";
        message=displayMode === "day"
            ? "Reading selected day closing price."
            : "Reading historical trading sessions.";
        reader.exec(["/usr/bin/env","node",
                     Quickshell.shellPath("scripts/finance/read_market_price_range_optional_hub.mjs"),
                     selectedCik,from,to]);
        return true;
    }
    function acceptOutput(raw) {
        if (desiredKey !== inFlightKey || !monitoring) return;
        const lines=String(raw||"").split(/\r?\n/);
        for(let i=0;i<lines.length;i++) {
            const line=lines[i];
            if(line.indexOf("FINANCE_STOCK_RANGE_ERROR ")===0) {
                const reason=line.slice("FINANCE_STOCK_RANGE_ERROR ".length);
                snapshot=null;
                state=["provider-key-required","demo-not-authorized"].indexOf(reason)>=0
                    ? "setup" : "failed";
                message=reason==="provider-key-required"
                    ? "NVIDIA PRICE HISTORY REQUIRES A PROVIDER KEY"
                    : reason==="demo-not-authorized"
                    ? "MICROSOFT DEMO ACCESS DENIED // PROVIDER KEY REQUIRED"
                    : reason==="invalid-range"
                    ? "INVALID DATE RANGE // MAX 180 DAYS"
                    : reason==="hub-unhealthy" || reason==="hub-invalid-response"
                    ? "LOCAL MARKET HUB ERROR // NO DIRECT RETRY"
                    : "HISTORICAL PRICE RANGE UNAVAILABLE";
                return;
            }
            if(line.indexOf("FINANCE_STOCK_RANGE ")!==0)continue;
            try {
                const data=JSON.parse(line.slice("FINANCE_STOCK_RANGE ".length));
                const symbols={"0000320193":"AAPL.US",
                    "0000789019":"MSFT.US","0001045810":"NVDA.US"};
                if(!data || data.schemaVersion!==1 || data.source!=="eodhd-eod"
                    || data.readOnly!==true || data.cik!==selectedCik
                    || data.symbol!==symbols[selectedCik]
                    || !activeWindow
                    || data.from!==activeWindow.from || data.to!==activeWindow.to
                    || desiredKey!==displayMode+"/"+selectedCik+"/"
                        +activeWindow.from+"/"+activeWindow.to
                    || !["CLOSE","ADJUSTED CLOSE"].includes(data.priceBasis)
                    || !data.delivery || !["DIRECT","HUB"].includes(data.delivery.via)
                    || !["DIRECT","FETCHED","CACHED","SHARED"].includes(data.delivery.state)
                    || (data.delivery.via==="DIRECT" && data.delivery.state!=="DIRECT")
                    || (data.delivery.via==="HUB" && !["FETCHED","CACHED","SHARED"].includes(data.delivery.state))
                    || typeof data.delivery.servedAt!=="string"
                    || !Number.isFinite(Date.parse(data.delivery.servedAt))
                    || !Array.isArray(data.bars) || data.bars.length>132
                    || (displayMode==="day" && data.bars.length>1)
                    || !data.bars.every(function(bar,index) {
                        return bar && validDate(bar.date)
                            && bar.date>=activeWindow.from
                            && bar.date<=activeWindow.to
                            && typeof bar.price==="number"
                            && Number.isFinite(bar.price) && bar.price>0
                            && (index===0 || data.bars[index-1].date<bar.date);
                    })
                    || (data.first===null)!==(data.bars.length===0)
                    || (data.last===null)!==(data.bars.length===0)
                    || (data.first && (data.first.date!==data.bars[0].date
                        || data.first.price!==data.bars[0].price))
                    || (data.last && (data.last.date!==data.bars[data.bars.length-1].date
                        || data.last.price!==data.bars[data.bars.length-1].price))
                    || (data.changePct!==null && !Number.isFinite(data.changePct)))
                    throw new Error("invalid-stock-range");
                snapshot=data;
                state="ready";
                const delivery=data.delivery.via==="HUB"
                    ? "MARKET HUB "+data.delivery.state : "DIRECT EODHD";
                message=displayMode==="day"
                    ? (data.bars.length
                        ? "DAY CLOSE // "+delivery
                        : "NO TRADING SESSION FOR THIS CALENDAR DAY")
                    : (data.bars.length
                        ? "DAILY PRICE RANGE // "+delivery
                        : "NO TRADING SESSIONS RETURNED IN THIS RANGE");
            }catch(error){
                snapshot=null;
                state="failed";
                message="Invalid stock range response.";
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
                if(stockFeed.state==="loading"){
                    stockFeed.snapshot=null;
                    stockFeed.state="failed";
                    stockFeed.message="Stock history request did not finish.";
                }
            });
        }
    }
}
