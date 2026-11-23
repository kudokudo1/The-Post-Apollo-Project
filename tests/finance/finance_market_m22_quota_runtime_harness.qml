import QtQuick
import QtQuick.Window
import Quickshell
import "../../widgets" as FinanceWidgets

// M22: REAL FinanceMarketQuotaStatusPane, with an inert fake Quickshell
// Process supplied by the Python offscreen test's temporary import path.
// No host local quota DB, real processes, shell config or provider network.
Window {
    id: fixtureRoot
    objectName: "quotaOffscreenHarness"
    width: 660
    height: 560
    visible: true
    color: "#16051F"
    property bool backEmitted: false
    readonly property int fakeProcessCalls: Quickshell.callCount
    readonly property string fakeLastCommand: Quickshell.lastCommand

    function report(state,eod,alpha) {
        const known = state==="ready";
        const row = function(provider,limit,used) {
            return {
                provider:provider,limit:limit,
                reserved:known ? used : null,
                recordState:known ? "known" : "unknown"
            };
        };
        return "FINANCE_QUOTA_STATUS "+JSON.stringify({
            schemaVersion:1,
            source:"post-apollo-market-local-quota-status-v1",
            scope:"post-apollo-market-local-v1",
            readOnly:true,
            noProviderCalls:true,
            notAccountBalance:true,
            utcDay:"2026-11-23",
            ledgerState:state,
            providers:[row("eodhd",20,eod),row("alpha-vantage",25,alpha)]
        })+"\n";
    }
    function stageReady() { Quickshell.nextPayload=report("ready",3,9); }
    function stageFull() { Quickshell.nextPayload=report("ready",20,25); }
    function stageAbsent() { Quickshell.nextPayload=report("absent",0,0); }
    function stageBusy() { Quickshell.nextPayload=report("unavailable",0,0); }
    function stageCorrupt() {
        Quickshell.nextPayload="FINANCE_QUOTA_STATUS invalid-json\n";
    }
    function stageInvalidCount() {
        Quickshell.nextPayload=report("ready",31,9);
    }
    function stageError() {
        Quickshell.nextPayload="FINANCE_QUOTA_STATUS_ERROR status-unavailable\n";
    }
    function resetBack() { backEmitted=false; }

    FinanceWidgets.FinanceMarketQuotaStatusPane {
        id: realPane
        anchors.fill: parent
        active: false
        onExitRequested: fixtureRoot.backEmitted=true
    }
}
