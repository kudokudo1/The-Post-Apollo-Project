import QtQuick
import Quickshell
import Quickshell.Io
import "../../widgets/FinanceBankingAccountsPolicy.js" as Accounts

// Banking M4o // Deliberately explicit local snapshot Save.
// No bank/Actual/Connections credentials, network or automatic financial write.
Scope {
    id: store
    property bool monitoring: false
    property string state: "idle" // idle | loading | pending | ready | failed
    property string message: "LOCAL MANUAL BANKING NOT LOADED"
    property int revision: 0
    property bool savedOnDisk: false
    property var savedSession: Accounts.emptyState()
    property string frame: ""
    property string output: ""
    property string activeAction: ""
    property bool pendingReload: false

    signal sessionLoaded()
    signal sessionSaved()
    signal sessionCleared()
    signal storeUnavailable()

    Component.onCompleted: {
        if(monitoring)refresh();
    }
    onMonitoringChanged: {
        if(monitoring && state==="idle")refresh();
    }

    function refresh() {
        if(!monitoring)return false;
        if(worker.running || state==="pending" || state==="loading") {
            pendingReload=true;
            return false;
        }
        return invoke({action:"list"});
    }
    function saveManual(session) {
        if(state!=="ready" || worker.running || !Accounts.validState(session)
            || session.mode!=="manual")return false;
        return invoke({action:"save",expectedRevision:revision,session:session});
    }
    function clearSaved() {
        if(state!=="ready" || worker.running || !savedOnDisk)return false;
        return invoke({action:"clear",expectedRevision:revision,
                       confirmClear:true});
    }
    function invoke(command) {
        if(!monitoring || worker.running || state==="pending" || state==="loading")return false;
        activeAction=command.action;
        frame=JSON.stringify(command)+"\n";
        output="";
        state=command.action==="list"?"loading":"pending";
        message=command.action==="list"
            ?"READING PRIVATE LOCAL MANUAL ACCOUNTS"
            :"WRITING PRIVATE MANUAL ACCOUNT SNAPSHOT";
        worker.exec({
            command:["/usr/bin/python3","-B",
                Quickshell.shellPath("scripts/finance/banking_manual_store.py")],
            environment: ({
                ACTUAL_PASSWORD_FILE:null,ACTUAL_SYNC_ID:null,
                ACTUAL_SERVER_URL:null,ACTUAL_SYNC_ID_FILE:null
            })
        });
        return true;
    }
    function acceptOutput(raw,code) {
        if(code!==0||typeof raw!=="string"||raw.length>530000)return false;
        const prefix="FINANCEW_BANKING_MANUAL_RESULT ";
        const lines=raw.split(/\r?\n/);
        if(lines.length!==2||lines[1]!==""||!lines[0].startsWith(prefix))
            return false;
        try {
            const result=JSON.parse(lines[0].slice(prefix.length));
            if(!result || result.source!=="LOCAL_OPERATOR_BANKING"
               || result.connected!==false || result.bankVerified!==false
               || result.identityVerified!==false || result.version!==1
               || !Number.isSafeInteger(result.revision)
               || result.revision<0 || result.revision>=Number.MAX_SAFE_INTEGER
               || result.savedOnDisk!==(result.revision>0)
               || !Accounts.validState(result.session)
               || !["manual","empty"].includes(result.session.mode))
                return false;
            revision=result.revision;
            savedOnDisk=result.savedOnDisk;
            savedSession=result.session;
            state="ready";
            message=savedOnDisk
                ?"PRIVATE LOCAL MANUAL ACCOUNTS // NOT BANK VERIFIED"
                :"NO SAVED MANUAL ACCOUNTS // READY FOR LOCAL ENTRY";
            if(activeAction==="list")sessionLoaded();
            if(activeAction==="save")sessionSaved();
            if(activeAction==="clear")sessionCleared();
            return true;
        } catch(error) { return false; }
    }

    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            if(store.frame!=="") {
                worker.write(store.frame);
                store.frame="";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: store.output=String(text || "")
        }
        onExited: function(code,status) {
            Qt.callLater(function() {
                const data=store.output;
                store.output="";
                store.frame="";
                const accepted=store.acceptOutput(data,code);
                store.activeAction="";
                if(!accepted) {
                    store.state="failed";
                    store.message="LOCAL BANKING STORE REFUSED // NO SAVE CONFIRMED // RELOAD BEFORE RETRY";
                    store.storeUnavailable();
                }
                if(store.pendingReload) {
                    store.pendingReload=false;
                    store.refresh();
                }
            });
        }
    }
}
