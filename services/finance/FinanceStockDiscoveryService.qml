import QtQuick
import Quickshell
import Quickshell.Io

// M17: user-triggered worldwide equity identity lookup, not an EOD price feed.
// Separate from FinanceStockHistoryReadService, SEC and all money writers.
Scope {
    id: finder
    property bool monitoring: false
    property string state: "idle"
    property string message: "TYPE A TICKER OR COMPANY, THEN PRESS SEARCH."
    property string requestedQuery: ""
    property string requestedCursor: ""
    property var snapshot: null
    readonly property bool loading: state === "loading"
    readonly property bool ready: state === "ready" && snapshot !== null
    readonly property bool canNext: ready && snapshot.next !== ""

    function clear() {
        requestedQuery = "";
        requestedCursor = "";
        snapshot = null;
        state = "idle";
        message = "TYPE A TICKER OR COMPANY, THEN PRESS SEARCH.";
    }
    onMonitoringChanged: {
        if (!monitoring) clear();
    }
    function search(query) {
        return request(query, "");
    }
    function nextPage() {
        if (!canNext) return false;
        return request(snapshot.query, snapshot.next);
    }
    function request(query, cursor) {
        if (!monitoring || loading || reader.running
                || typeof query !== "string" || typeof cursor !== "string")
            return false;
        const term = query.trim().replace(/\s+/g," ");
        if (term.length < 2 || term.length > 80 || term.split(" ").length > 12
                || cursor.length > 512 || (cursor !== ""
                    && !/^[A-Za-z0-9._+=/-]+$/.test(cursor))) {
            snapshot = null;
            state = "invalid";
            message = "ENTER 2-80 CHARACTERS / UP TO 12 TERMS.";
            return false;
        }
        requestedQuery = term;
        requestedCursor = cursor;
        snapshot = null;
        state = "loading";
        message = cursor ? "LOOKING UP NEXT OPENFIGI PAGE." : "SEARCHING OPENFIGI.";
        reader.exec(["/usr/bin/env","node",
            Quickshell.shellPath("scripts/finance/search_openfigi_stocks.mjs"),
            term,cursor]);
        return true;
    }
    function acceptOutput(raw) {
        if (!monitoring || state !== "loading") return;
        const lines = String(raw || "").split(/\r?\n/);
        for (let i=0;i<lines.length;i++) {
            const line=lines[i];
            if (line.indexOf("FINANCE_STOCK_SEARCH_ERROR ")===0) {
                const code=line.slice("FINANCE_STOCK_SEARCH_ERROR ".length);
                snapshot=null;
                state="failed";
                message=code==="rate-limited"
                    ? "OPENFIGI FREE LIMIT REACHED // RETRY LATER"
                    : code==="invalid-query" || code==="invalid-cursor"
                    ? "INVALID SEARCH TEXT OR PAGE"
                    : "STOCK DISCOVERY UNAVAILABLE // NO PRICE REQUEST";
                return;
            }
            if (line.indexOf("FINANCE_STOCK_SEARCH ")!==0) continue;
            try {
                const data=JSON.parse(line.slice("FINANCE_STOCK_SEARCH ".length));
                if (!data || data.schemaVersion!==1 || data.source!=="openfigi-v3"
                        || data.readOnly!==true || data.priceLinked!==false
                        || data.query!==requestedQuery || data.cursor!==requestedCursor
                        || typeof data.retrievedAt!=="string"
                        || !Number.isFinite(Date.parse(data.retrievedAt))
                        || typeof data.next!=="string" || data.next.length>512
                        || (data.next!=="" && !/^[A-Za-z0-9._+=/-]+$/.test(data.next))
                        || !Array.isArray(data.items) || data.items.length>100
                        || !data.items.every(function(item) {
                            return item && typeof item.figi==="string"
                                && /^BBG[A-Z0-9]{9}$/.test(item.figi)
                                && typeof item.ticker==="string"
                                && item.ticker.length>0 && item.ticker.length<=60
                                && typeof item.name==="string"
                                && item.name.length>0 && item.name.length<=180
                                && typeof item.exchCode==="string"
                                && item.exchCode.length>0 && item.exchCode.length<=32
                                && typeof item.securityType==="string"
                                && item.securityType.length<=80;
                        })) throw new Error("invalid-search-snapshot");
                snapshot=data;
                state="ready";
                message=data.items.length
                    ? "OPENFIGI // INSTRUMENTS FOUND // PRICE DATA NOT LINKED"
                    : "NO MATCHING STOCKS ON THIS PAGE";
            }catch(error) {
                snapshot=null;
                state="failed";
                message="INVALID STOCK DISCOVERY RESPONSE";
            }
            return;
        }
    }
    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: finder.acceptOutput(text)
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                if (finder.state==="loading") {
                    finder.snapshot=null;
                    finder.state="failed";
                    finder.message="STOCK DISCOVERY REQUEST DID NOT FINISH";
                }
            });
        }
    }
}
