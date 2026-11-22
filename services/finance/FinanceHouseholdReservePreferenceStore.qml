import QtQuick
import Quickshell
import Quickshell.Io

// FinanceW FP1k: one optional percentage per local context label.
// Same Linux login, not separately authenticated household identities.
Scope {
    id: store
    property string contextId: "mine"
    property bool monitoring: false
    property int marginPercent: 100
    property int revision: 0
    property string state: "idle" // idle, loading, pending, ready, failed
    property string message: "RESERVE PREFERENCE NOT LOADED"
    property string inputFrame: ""
    property string output: ""
    property string activeAction: ""
    property string submittedContext: ""
    property bool pendingReload: false
    signal preferenceLoaded()
    signal preferenceSaved()
    signal preferenceReset()

    function validContext() {
        return /^(mine|shared|mom|granny|family)$/.test(contextId);
    }
    function clearView() {
        marginPercent=100;
        revision=0;
        state="idle";
        message="RESERVE PREFERENCE NOT LOADED";
    }
    onContextIdChanged: {
        clearView();
        if (monitoring) refresh();
    }
    onMonitoringChanged: {
        if (monitoring) refresh();
        else clearView();
    }
    Component.onCompleted: {
        if (monitoring) refresh();
    }
    function refresh() {
        if (!monitoring || !validContext()) return false;
        marginPercent=100;
        revision=0;
        if (worker.running || state==="pending" || state==="loading") {
            pendingReload=true;
            state="loading";
            message="WAITING FOR SELECTED CONTEXT";
            return false;
        }
        return invoke({action:"list",contextId:contextId});
    }
    function invoke(command) {
        if (!monitoring || !validContext() || worker.running
                || state==="loading" || state==="pending") return false;
        submittedContext=contextId;
        activeAction=command.action;
        output="";
        inputFrame=JSON.stringify(command)+"\n";
        state=command.action==="list"?"loading":"pending";
        message=command.action==="list"
            ?"READING RESERVE PREFERENCE":"SAVING RESERVE PREFERENCE";
        worker.exec({
            command:["/usr/bin/python3","-B",
                Quickshell.shellPath("scripts/finance/household_reserve_preference_store.py")],
            environment: ({ACTUAL_PASSWORD_FILE:null,ACTUAL_SYNC_ID:null,
                ACTUAL_SERVER_URL:null,ACTUAL_SYNC_ID_FILE:null})
        });
        return true;
    }
    function save(percent) {
        if (!monitoring || state!=="ready" ||
            [100,110,125].indexOf(percent)<0) return false;
        return invoke({action:"save",contextId:contextId,
            expectedRevision:revision,marginPercent:percent});
    }
    function reset() {
        if (!monitoring || state!=="ready") return false;
        return invoke({action:"reset",contextId:contextId,
            expectedRevision:revision});
    }

    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            if (store.inputFrame) {
                worker.write(store.inputFrame);
                store.inputFrame="";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                const prefix="FINANCEW_RESERVE_PREF_RESULT ";
                const lines=String(text || "").split(/\r?\n/);
                for(let i=0;i<lines.length;i++) {
                    if(lines[i].startsWith(prefix))
                        store.output=lines[i].slice(prefix.length);
                }
            }
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                const same=store.monitoring
                    && store.submittedContext===store.contextId;
                let accepted=false;
                if(exitCode===0 && same && store.output) {
                    try {
                        const doc=JSON.parse(store.output);
                        if(doc && doc.source==="LOCAL_OPERATOR_RESERVE_PREFS"
                                && doc.identityVerified===false
                                && doc.bankVerified===false
                                && doc.version===1
                                && doc.contextId===store.contextId
                                && Number.isSafeInteger(doc.revision)
                                && doc.revision>=0
                                && [100,110,125].indexOf(doc.marginPercent)>=0) {
                            store.marginPercent=doc.marginPercent;
                            store.revision=doc.revision;
                            store.state="ready";
                            store.message="LOCAL PREFERENCE // NOT BANK VERIFIED";
                            accepted=true;
                            if(store.activeAction==="list")
                                store.preferenceLoaded();
                            if(store.activeAction==="save")
                                store.preferenceSaved();
                            if(store.activeAction==="reset")
                                store.preferenceReset();
                        }
                    } catch(error) { /* Refuse, do not log personal content. */ }
                }
                if(!accepted && same) {
                    store.state="failed";
                    store.message="PREFERENCE STORE UNAVAILABLE // REFRESH BEFORE RETRY";
                    // Do not silently overwrite or fall back to a saved guess.
                    store.revision=0;
                }
                store.output="";
                store.activeAction="";
                if(store.pendingReload || (store.monitoring && !same)) {
                    store.pendingReload=false;
                    store.state="idle";
                    store.refresh();
                }
            });
        }
    }
}
