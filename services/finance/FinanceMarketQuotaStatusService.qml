import QtQuick
import Quickshell
import Quickshell.Io

// M21: no-provider-call, no-write read of M20 local SQLite quota snapshot.
// The only subprocess is market_quota_status.py status; it has no reserve path.
Scope {
    id: quotaReader
    objectName: "marketQuotaReaderService"
    property bool monitoring: false
    property string state: "idle"
    property string message: "OPEN QUOTA STATUS TO READ LOCAL RESERVATIONS."
    property var snapshot: null
    readonly property bool loading: state === "loading"
    readonly property bool ready: state === "ready" && snapshot !== null
    readonly property bool unknown: state === "absent" || state === "unavailable"

    function clear() {
        state = "idle";
        message = "PRESS REFRESH LOCAL STATUS TO READ THE QUOTA LEDGER.";
        snapshot = null;
    }
    onMonitoringChanged: {
        if (!monitoring) clear();
        else refresh();
    }
    function refresh() {
        if (!monitoring || reader.running || loading) return false;
        snapshot = null;
        state = "loading";
        message = "READING LOCAL RESERVATIONS // NO MARKET API CALLS.";
        reader.exec(["/usr/bin/env","python3",
            Quickshell.shellPath("scripts/finance/market_quota_status.py"),
            "status"]);
        return true;
    }
    function calendarDay(value) {
        if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
            return false;
        const n = Date.parse(value+"T00:00:00Z");
        return Number.isFinite(n) && new Date(n).toISOString().slice(0,10)===value;
    }
    function validRow(row,provider,limit,ledgerState) {
        if (!row || row.provider!==provider || row.limit!==limit
                || !["known","unknown"].includes(row.recordState))
            return false;
        if (ledgerState==="ready")
            return row.recordState==="known"
                && Number.isInteger(row.reserved)
                && row.reserved>=0 && row.reserved<=limit;
        return row.recordState==="unknown" && row.reserved===null;
    }
    function accept(raw) {
        if (!monitoring || !loading) return;
        const lines=String(raw||"").split(/\r?\n/);
        for(let i=0;i<lines.length;i++) {
            const line=lines[i];
            if(line.indexOf("FINANCE_QUOTA_STATUS_ERROR ")===0) {
                snapshot=null;
                state="unavailable";
                message="LOCAL QUOTA STATUS UNAVAILABLE // NO ZERO ASSUMED.";
                return;
            }
            if(line.indexOf("FINANCE_QUOTA_STATUS ")!==0)continue;
            try {
                const data=JSON.parse(line.slice("FINANCE_QUOTA_STATUS ".length));
                if (!data || data.schemaVersion!==1
                        || data.source!=="post-apollo-market-local-quota-status-v1"
                        || data.scope!=="post-apollo-market-local-v1"
                        || data.readOnly!==true || data.noProviderCalls!==true
                        || data.notAccountBalance!==true
                        || !calendarDay(data.utcDay)
                        || !["ready","absent","unavailable"].includes(data.ledgerState)
                        || !Array.isArray(data.providers)
                        || data.providers.length!==2
                        || !validRow(data.providers[0],"eodhd",20,data.ledgerState)
                        || !validRow(data.providers[1],"alpha-vantage",25,data.ledgerState))
                    throw new Error("invalid-quota-status");
                snapshot=data;
                state=data.ledgerState;
                message=data.ledgerState==="ready"
                    ? "LOCAL RESERVATIONS LOADED // NOT PROVIDER ACCOUNT USAGE."
                    : data.ledgerState==="absent"
                    ? "LOCAL LEDGER NOT INITIALIZED // USAGE UNKNOWN."
                    : "LOCAL LEDGER UNREADABLE OR BUSY // USAGE UNKNOWN.";
            }catch(error) {
                snapshot=null;
                state="unavailable";
                message="INVALID LOCAL QUOTA STATUS // USAGE UNKNOWN.";
            }
            return;
        }
    }
    Process {
        id: reader
        stdout: StdioCollector {
            onStreamFinished: quotaReader.accept(text)
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                if(quotaReader.loading) {
                    quotaReader.snapshot=null;
                    quotaReader.state="unavailable";
                    quotaReader.message="LOCAL STATUS REQUEST DID NOT FINISH.";
                }
            });
        }
    }
}
