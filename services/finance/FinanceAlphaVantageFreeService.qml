import QtQuick
import Quickshell
import Quickshell.Io

// M19: separate Alpha Vantage free-key reader, no provider auto-fallback.
// Counts requests started in THIS running widget only, never account usage.
Scope {
    id: alphaFeed
    property bool monitoring: false
    property string state: "idle"
    property string message: "FIND ALPHA VANTAGE STOCK LISTINGS MANUALLY."
    property var identity: null
    property var candidates: []
    property var selectedListing: null
    property var snapshot: null
    property int presetDays: 30
    property string quotaUtcDay: ""
    property int requestsThisRuntime: 0
    readonly property int advertisedFreeDailyAllowance: 25
    readonly property int remainingRuntimeAllowance:
        Math.max(0,advertisedFreeDailyAllowance-requestsThisRuntime)
    property string requestedOp: ""
    property string requestedIdentity: ""
    property string requestedTicker: ""
    property string requestedSymbol: ""
    property string requestedCurrency: ""
    property string requestedFrom: ""
    property string requestedTo: ""
    readonly property bool loading: state==="looking" || state==="loading"
    readonly property bool ready: state==="ready" && snapshot!==null

    function dayOffset(delta) {
        const date=new Date();
        date.setUTCDate(date.getUTCDate()+delta);
        return date.toISOString().slice(0,10);
    }
    function availableCall() {
        const utcDay=dayOffset(0);
        if(quotaUtcDay!==utcDay) {
            quotaUtcDay=utcDay;
            requestsThisRuntime=0;
        }
        if(requestsThisRuntime>=advertisedFreeDailyAllowance) {
            state="quota";
            message="LOCAL PANEL ATTEMPT LIMIT REACHED // TRY NEXT UTC DAY";
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
        message="FIND ALPHA VANTAGE STOCK LISTINGS MANUALLY.";
        requestedOp="";
        requestedIdentity="";
        requestedTicker="";
        requestedSymbol="";
        requestedCurrency="";
        requestedFrom="";
        requestedTo="";
        presetDays=30;
        // Do not reset requestsThisRuntime when changing/closing an instrument.
    }
    onMonitoringChanged: {
        if(!monitoring)clear();
    }
    function chooseIdentity(item) {
        if(reader.running || !item
            || typeof item.figi!=="string" || !/^BBG[A-Z0-9]{9}$/.test(item.figi)
            || typeof item.ticker!=="string" || item.ticker.length===0
            || typeof item.name!=="string" || item.name.length===0
            || typeof item.exchCode!=="string" || item.exchCode.length===0)
            return false;
        clear();
        identity={figi:item.figi,ticker:item.ticker,
            name:item.name,exchCode:item.exchCode};
        state="identity";
        message="OPENFIGI IDENTITY SELECTED // NO PROVIDER SYMBOL IMPLIED.";
        return true;
    }
    function lookup() {
        if(!monitoring || loading || reader.running || !identity
            || !/^[A-Z0-9][A-Z0-9_.-]{0,29}$/.test(identity.ticker)
            || identity.ticker.indexOf("..")>=0 || !availableCall())
            return false;
        requestedOp="lookup";
        requestedIdentity=identity.figi;
        requestedTicker=identity.ticker;
        requestedSymbol="";
        requestedCurrency="";
        candidates=[];
        selectedListing=null;
        snapshot=null;
        state="looking";
        message="SEARCHING ALPHA VANTAGE // 1 FREE KEY REQUEST.";
        requestsThisRuntime++;
        reader.exec(["/usr/bin/env","node",
            Quickshell.shellPath("scripts/finance/read_alpha_vantage_free.mjs"),
            "lookup",identity.ticker]);
        return true;
    }
    function chooseListing(item) {
        if(!monitoring || reader.running
            || !["candidates","selected","ready","failed"].includes(state)
            || !item || !candidates.some(function(x){
                return x.symbol===item.symbol && x.name===item.name
                    && x.region===item.region && x.currency===item.currency;
            }))return false;
        selectedListing={symbol:item.symbol,name:item.name,
            region:item.region,currency:item.currency,type:item.type};
        snapshot=null;
        state="selected";
        message="ALPHA VANTAGE SYMBOL CHOSEN // VERIFY REGION / NAME / CURRENCY.";
        return true;
    }
    function selectPreset(days) {
        if(![7,30,90,180].includes(days) || loading || reader.running)
            return false;
        if(presetDays!==days) {
            presetDays=days;
            snapshot=null;
            if(selectedListing) {
                state="selected";
                message="DATE RANGE CHANGED // PRESS LOAD HISTORY.";
            }
        }
        return true;
    }
    function loadHistory() {
        if(!monitoring || loading || reader.running || !identity
            || !selectedListing || !["selected","ready"].includes(state)
            || !availableCall())return false;
        requestedOp="history";
        requestedIdentity=identity.figi;
        requestedSymbol=selectedListing.symbol;
        requestedCurrency=selectedListing.currency;
        requestedTo=dayOffset(0);
        requestedFrom=dayOffset(-(presetDays-1));
        snapshot=null;
        state="loading";
        message="READING ALPHA VANTAGE COMPACT DAILY HISTORY // RAW CLOSE.";
        requestsThisRuntime++;
        reader.exec(["/usr/bin/env","node",
            Quickshell.shellPath("scripts/finance/read_alpha_vantage_free.mjs"),
            "history",requestedSymbol,requestedCurrency,requestedFrom,requestedTo]);
        return true;
    }
    function validDate(day) {
        if(typeof day!=="string" || !/^\d{4}-\d{2}-\d{2}$/.test(day))
            return false;
        const x=Date.parse(day+"T00:00:00Z");
        return Number.isFinite(x) && new Date(x).toISOString().slice(0,10)===day;
    }
    function acceptOutput(raw) {
        if(!monitoring || !loading || !identity
            || requestedIdentity!==identity.figi)return;
        const lines=String(raw||"").split(/\r?\n/);
        for(let i=0;i<lines.length;i++){
            const line=lines[i];
            if(line.indexOf("FINANCE_ALPHA_FREE_ERROR ")===0) {
                const error=line.slice("FINANCE_ALPHA_FREE_ERROR ".length);
                snapshot=null;
                state=["provider-key-required","provider-key-invalid","token-invalid",
                    "token-permissions","token-unreadable"].includes(error)
                    ? "setup":"failed";
                message=error==="provider-key-required"
                    ? "FREE ALPHA VANTAGE KEY REQUIRED // NO PAID PLAN"
                    : error==="provider-rate-or-entitlement"
                    ? "ALPHA VANTAGE QUOTA OR FREE-TIER RESTRICTION"
                    : error==="provider-not-entitled"
                    ? "PROVIDER DOES NOT ENTITLE THIS DATA"
                    : error==="provider-symbol-unavailable"
                    ? "THIS ALPHA VANTAGE SYMBOL IS UNAVAILABLE"
                    : error.startsWith("token-") || error==="provider-key-invalid"
                    ? "ALPHA VANTAGE KEY IS INVALID OR UNREADABLE"
                    : "ALPHA VANTAGE DATA UNAVAILABLE // NO AUTO RETRY";
                return;
            }
            if(line.indexOf("FINANCE_ALPHA_FREE ")!==0)continue;
            try {
                const data=JSON.parse(line.slice("FINANCE_ALPHA_FREE ".length));
                if(!data || data.schemaVersion!==1 || data.readOnly!==true
                    || typeof data.retrievedAt!=="string"
                    || !Number.isFinite(Date.parse(data.retrievedAt)))
                    throw new Error("invalid-response");
                if(state==="looking" && requestedOp==="lookup"){
                    if(data.source!=="alpha-vantage-symbol-search"
                        || data.priceLinked!==false
                        || data.queryTicker!==requestedTicker
                        || !Array.isArray(data.items) || data.items.length>25
                        || !data.items.every(function(x){
                            return x && typeof x.symbol==="string"
                                && /^[A-Z0-9][A-Z0-9_.-]{0,44}$/.test(x.symbol)
                                && (x.symbol===requestedTicker
                                    || x.symbol.indexOf(requestedTicker+".")===0)
                                && typeof x.name==="string" && x.name.length>0
                                && x.name.length<=160
                                && typeof x.region==="string" && x.region.length>0
                                && x.region.length<=80
                                && /^[A-Z]{3}$/.test(x.currency)
                                && typeof x.type==="string" && x.type.length>0
                                && x.matchedOpenFigi===false;
                        }))throw new Error("invalid-symbol-results");
                    candidates=data.items;
                    state="candidates";
                    message=candidates.length
                        ? "CHOOSE EXACT LISTING // SOURCE SYMBOL NOT FIGI VERIFIED"
                        : "NO SAME-TICKER ALPHA VANTAGE STOCK LISTING FOUND";
                } else if(state==="loading" && requestedOp==="history") {
                    if(!selectedListing || data.source!=="alpha-vantage-daily-compact"
                        || data.symbol!==requestedSymbol
                        || data.currency!==requestedCurrency
                        || data.symbol!==selectedListing.symbol
                        || data.currency!==selectedListing.currency
                        || data.from!==requestedFrom || data.to!==requestedTo
                        || data.priceBasis!=="CLOSE"
                        || data.currencySource!=="alpha-vantage-symbol-search"
                        || data.identityVerified!==false
                        || data.compactMaxBars!==100
                        || !Number.isInteger(data.returnedBars)
                        || data.returnedBars<1 || data.returnedBars>100
                        || typeof data.compactMayBeTruncated!=="boolean"
                        || !validDate(data.oldestAvailable)
                        || !validDate(data.latestAvailable)
                        || !Array.isArray(data.bars) || data.bars.length>100
                        || !data.bars.every(function(bar,k){
                            return bar && validDate(bar.date)
                                && bar.date>=requestedFrom && bar.date<=requestedTo
                                && typeof bar.price==="number" && Number.isFinite(bar.price)
                                && bar.price>0 && (k===0
                                || data.bars[k-1].date<bar.date);
                        })
                        || (data.first===null)!==(data.bars.length===0)
                        || (data.last===null)!==(data.bars.length===0)
                        || (data.first && (data.first.date!==data.bars[0].date
                            || data.first.price!==data.bars[0].price))
                        || (data.last && (data.last.date!==data.bars[data.bars.length-1].date
                            || data.last.price!==data.bars[data.bars.length-1].price))
                        || (data.changePct!==null && !Number.isFinite(data.changePct)))
                        throw new Error("invalid-price-data");
                    snapshot=data;
                    state="ready";
                    message=data.bars.length
                        ? "ALPHA VANTAGE RAW DAILY CLOSES // NOT LIVE QUOTES"
                        : "NO COMPACT DAILY SESSIONS FOR THIS RANGE";
                } else throw new Error("unexpected-response-state");
            }catch(error) {
                snapshot=null;
                candidates=[];
                state="failed";
                message="INVALID ALPHA VANTAGE DATA / REFUSED";
            }
            return;
        }
    }
    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: alphaFeed.acceptOutput(text)
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function(){
                if(alphaFeed.loading){
                    alphaFeed.snapshot=null;
                    alphaFeed.state="failed";
                    alphaFeed.message="ALPHA VANTAGE REQUEST DID NOT FINISH";
                }
            });
        }
    }
}
