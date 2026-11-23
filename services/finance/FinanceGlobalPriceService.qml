import QtQuick
import Quickshell
import Quickshell.Io

// M18: explicit free-token EODHD listing search and one selected EOD read.
// OpenFIGI identities and EODHD listings are NEVER automatically equated.
Scope {
    id: globalPrice
    property bool monitoring: false
    // Local, in-memory UTC request starts only. Other EODHD clients/hosts
    // and actual provider billing are not observed or inferred here.
    property string quotaUtcDay: ""
    property int requestsThisRuntime: 0
    readonly property int advertisedFreeDailyAllowance: 20
    property string state: "idle"
    property string message: "CHOOSE AN OPENFIGI RESULT, THEN FIND EODHD LISTINGS."
    property var identity: null
    property var candidates: []
    property var selectedListing: null
    property var snapshot: null
    property int presetDays: 30
    property string requestedOp: ""
    property string requestedIdentity: ""
    property string requestedTicker: ""
    property string requestedSymbol: ""
    property string requestedCurrency: ""
    property string requestedFrom: ""
    property string requestedTo: ""
    readonly property bool loading: state==="looking" || state==="loading"
    readonly property bool ready: state==="ready" && snapshot!==null

    function freeAttemptAllowed() {
        const utcDay=dateOffset(0);
        if (quotaUtcDay!==utcDay) {
            quotaUtcDay=utcDay;
            requestsThisRuntime=0;
        }
        if (requestsThisRuntime>=advertisedFreeDailyAllowance) {
            state="quota";
            message="LOCAL EODHD PANEL LIMIT REACHED // NO AUTOMATIC REQUEST";
            return false;
        }
        return true;
    }
    function clear() {
        identity=null;
        candidates=[];
        selectedListing=null;
        snapshot=null;
        state="idle";
        message="CHOOSE AN OPENFIGI RESULT, THEN FIND EODHD LISTINGS.";
        requestedOp="";
        requestedIdentity="";
        requestedTicker="";
        requestedSymbol="";
        requestedCurrency="";
        requestedFrom="";
        requestedTo="";
        presetDays=30;
    }
    onMonitoringChanged: {
        if (!monitoring) clear();
    }
    function chooseIdentity(item) {
        if (reader.running || !item
                || typeof item.figi!=="string"
                || !/^BBG[A-Z0-9]{9}$/.test(item.figi)
                || typeof item.ticker!=="string" || item.ticker.length<1
                || typeof item.name!=="string" || item.name.length<1
                || typeof item.exchCode!=="string" || item.exchCode.length<1)
            return false;
        clear();
        identity={figi:item.figi,ticker:item.ticker,
            name:item.name,exchCode:item.exchCode};
        state="identity";
        message="OPENFIGI IDENTITY CHOSEN // FIND EODHD LISTINGS MANUALLY.";
        return true;
    }
    function lookup() {
        if (!monitoring || loading || reader.running || !identity
                || !/^[A-Z0-9][A-Z0-9_.-]{0,29}$/.test(identity.ticker))
            return false;
        if (!freeAttemptAllowed()) return false;
        requestedOp="lookup";
        requestedIdentity=identity.figi;
        requestedTicker=identity.ticker;
        requestedSymbol="";
        requestedCurrency="";
        candidates=[];
        selectedListing=null;
        snapshot=null;
        state="looking";
        message="SEARCHING EODHD STOCK LISTINGS // ONE FREE-PLAN API CALL.";
        requestsThisRuntime++;
        reader.exec(["/usr/bin/env","node",
            Quickshell.shellPath("scripts/finance/read_global_eodhd_history.mjs"),
            "lookup",identity.ticker]);
        return true;
    }
    function chooseListing(row) {
        if (!monitoring || reader.running
                || !["candidates","selected","ready","failed"].includes(state)
                || !row || !candidates.some(function(x) {
                    return x.symbol===row.symbol
                        && x.name===row.name && x.currency===row.currency
                        && x.exchange===row.exchange;
                })) return false;
        selectedListing={
            symbol:row.symbol,code:row.code,exchange:row.exchange,
            name:row.name,type:row.type,country:row.country,
            currency:row.currency,isin:row.isin
        };
        snapshot=null;
        state="selected";
        message="EODHD LISTING SELECTED // VERIFY NAME + EXCHANGE // THEN LOAD.";
        return true;
    }
    function selectPreset(days) {
        if (![7,30,90,180].includes(days) || loading || reader.running)
            return false;
        if (presetDays!==days) {
            presetDays=days;
            snapshot=null;
            if (selectedListing) {
                state="selected";
                message="DATE RANGE CHANGED // PRESS LOAD HISTORY.";
            }
        }
        return true;
    }
    function dateOffset(days) {
        const day=new Date();
        day.setUTCDate(day.getUTCDate()+days);
        return day.toISOString().slice(0,10);
    }
    function loadHistory() {
        if (!monitoring || loading || reader.running || !identity
                || !selectedListing || !(state==="selected" || state==="ready"))
            return false;
        if (!freeAttemptAllowed()) return false;
        requestedOp="history";
        requestedIdentity=identity.figi;
        requestedSymbol=selectedListing.symbol;
        requestedCurrency=selectedListing.currency;
        requestedTo=dateOffset(0);
        requestedFrom=dateOffset(-(presetDays-1));
        snapshot=null;
        state="loading";
        message="READING EODHD DAILY CLOSES // ONE FREE-PLAN API CALL.";
        requestsThisRuntime++;
        reader.exec(["/usr/bin/env","node",
            Quickshell.shellPath("scripts/finance/read_global_eodhd_history.mjs"),
            "history",requestedSymbol,requestedCurrency,requestedFrom,requestedTo]);
        return true;
    }
    function validDate(day) {
        if (typeof day!=="string" || !/^\d{4}-\d{2}-\d{2}$/.test(day))
            return false;
        const t=Date.parse(day+"T00:00:00Z");
        return Number.isFinite(t) && new Date(t).toISOString().slice(0,10)===day;
    }
    function acceptOutput(raw) {
        if (!monitoring || !loading || !identity
                || requestedIdentity!==identity.figi) return;
        const lines=String(raw||"").split(/\r?\n/);
        for(let i=0;i<lines.length;i++) {
            const line=lines[i];
            if(line.indexOf("FINANCE_GLOBAL_EODHD_ERROR ")===0) {
                const code=line.slice("FINANCE_GLOBAL_EODHD_ERROR ".length);
                snapshot=null;
                state=["provider-key-required","token-unreadable","token-permissions",
                    "token-invalid","provider-key-invalid"].includes(code)
                    ? "setup" : "failed";
                message=code==="provider-key-required"
                    ? "FREE EODHD ACCOUNT KEY REQUIRED // PAID PLAN NOT REQUIRED"
                    : code==="provider-not-entitled"
                    ? "EODHD DOES NOT PROVIDE THIS LISTING ON CURRENT PLAN"
                    : code==="rate-limited"
                    ? "FREE PROVIDER RATE / DAILY QUOTA EXHAUSTED"
                    : code.startsWith("token-") || code==="provider-key-invalid"
                    ? "INVALID OR UNREADABLE LOCAL EODHD KEY"
                    : "EODHD LOOKUP OR PRICE HISTORY UNAVAILABLE";
                return;
            }
            if(line.indexOf("FINANCE_GLOBAL_EODHD ")!==0) continue;
            try {
                const data=JSON.parse(line.slice("FINANCE_GLOBAL_EODHD ".length));
                if(!data || data.schemaVersion!==1 || data.readOnly!==true
                        || typeof data.retrievedAt!=="string"
                        || !Number.isFinite(Date.parse(data.retrievedAt)))
                    throw new Error("invalid-header");
                if(requestedOp==="lookup" && state==="looking") {
                    if(data.source!=="eodhd-search" || data.priceLinked!==false
                            || data.queryTicker!==requestedTicker
                            || !Array.isArray(data.items) || data.items.length>25
                            || !data.items.every(function(x) {
                                return x && typeof x.symbol==="string"
                                    && /^[A-Z0-9][A-Z0-9_.-]{0,29}\.[A-Z][A-Z0-9]{0,11}$/.test(x.symbol)
                                    && x.code===requestedTicker
                                    && x.symbol===x.code+"."+x.exchange
                                    && typeof x.name==="string" && x.name.length>0
                                    && typeof x.currency==="string" && /^[A-Z]{3}$/.test(x.currency)
                                    && typeof x.country==="string" && x.country.length>0
                                    && typeof x.type==="string" && x.type.length>0
                                    && (x.isin===null || typeof x.isin==="string");
                            })) throw new Error("invalid-search");
                    candidates=data.items;
                    state="candidates";
                    message=candidates.length
                        ? "VERIFY NAME / COUNTRY / EXCHANGE // CHOOSE ONE LISTING"
                        : "NO SAME-TICKER EODHD STOCK LISTINGS RETURNED";
                } else if(requestedOp==="history" && state==="loading") {
                    if(!selectedListing || data.source!=="eodhd-eod"
                            || data.symbol!==requestedSymbol
                            || data.currency!==requestedCurrency
                            || data.symbol!==selectedListing.symbol
                            || data.currency!==selectedListing.currency
                            || data.from!==requestedFrom || data.to!==requestedTo
                            || data.currencySource!=="eodhd-search"
                            || data.identityVerified!==false
                            || !["CLOSE","ADJUSTED CLOSE"].includes(data.priceBasis)
                            || !Array.isArray(data.bars) || data.bars.length>132
                            || !data.bars.every(function(bar,j) {
                                return bar && validDate(bar.date)
                                    && bar.date>=requestedFrom && bar.date<=requestedTo
                                    && typeof bar.price==="number" && Number.isFinite(bar.price)
                                    && bar.price>0
                                    && (j===0 || data.bars[j-1].date<bar.date);
                            })
                            || (data.first===null)!==(data.bars.length===0)
                            || (data.last===null)!==(data.bars.length===0)
                            || (data.first && (data.first.date!==data.bars[0].date
                                || data.first.price!==data.bars[0].price))
                            || (data.last && (data.last.date!==data.bars[data.bars.length-1].date
                                || data.last.price!==data.bars[data.bars.length-1].price))
                            || (data.changePct!==null && !Number.isFinite(data.changePct)))
                        throw new Error("invalid-history");
                    snapshot=data;
                    state="ready";
                    message=data.bars.length
                        ? "HISTORICAL EOD CLOSES // NOT LIVE // SOURCE EODHD"
                        : "NO EOD TRADING SESSIONS FOR THIS RANGE";
                } else throw new Error("unexpected-state");
            }catch(error) {
                snapshot=null;
                candidates=[];
                state="failed";
                message="INVALID EODHD PRICE SOURCE RESPONSE";
            }
            return;
        }
    }
    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: globalPrice.acceptOutput(text)
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                if(globalPrice.loading) {
                    globalPrice.snapshot=null;
                    globalPrice.state="failed";
                    globalPrice.message="PRICE SOURCE REQUEST DID NOT FINISH";
                }
            });
        }
    }
}
