import QtQuick
import Quickshell
import Quickshell.Io

// FP1b: local operator-entered plans only. No verified household membership,
// bank sync, Actual Budget account connection, credentials or background work.
Scope {
    id: store
    property string contextId: "mine"
    property bool monitoring: false
    property var rows: []
    property int revision: 0
    property string state: "idle" // idle, loading, pending, ready, failed
    property string message: "LOCAL PLANS NOT LOADED"
    property string inputFrame: ""
    property string output: ""
    property string activeAction: ""
    property string submittedContext: ""
    property bool pendingReload: false
    signal entrySaved()
    signal entryDeleted()

    function clearView() {
        rows=[];
        revision=0;
        state="idle";
        message="LOCAL PLANS NOT LOADED";
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
        if (!monitoring || !/^(mine|shared|mom|granny|family)$/.test(contextId))
            return false;
        rows=[];
        revision=0;
        if (worker.running || state==="pending" || state==="loading") {
            pendingReload=true;
            state="loading";
            message="WAITING TO LOAD SELECTED CONTEXT";
            return false;
        }
        return invoke({action:"list",contextId:contextId});
    }
    function invoke(command) {
        if (!monitoring || worker.running || state==="pending" || state==="loading")
            return false;
        submittedContext=contextId;
        activeAction=command.action;
        inputFrame=JSON.stringify(command)+"\n";
        output="";
        state=command.action==="list"?"loading":"pending";
        message=command.action==="list"?"LOADING LOCAL PLANS":"SAVING LOCAL PLANS";
        worker.exec({
            command:["/usr/bin/python3","-B",
                Quickshell.shellPath("scripts/finance/household_plan_store.py")],
            environment: ({ACTUAL_PASSWORD_FILE:null,ACTUAL_SYNC_ID:null,
                ACTUAL_SERVER_URL:null,ACTUAL_SYNC_ID_FILE:null})
        });
        return true;
    }
    function add(kind,title,targetText,savedText,monthlyText) {
        if (state!=="ready" || !monitoring) return false;
        return invoke({action:"add",contextId:contextId,expectedRevision:revision,
            kind:kind,title:title,targetText:targetText,
            savedText:savedText,monthlyText:monthlyText});
    }
    function remove(id) {
        if (state!=="ready" || !monitoring) return false;
        return invoke({action:"delete",contextId:contextId,
            expectedRevision:revision,id:id});
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
                const lines=String(text || "").split(/\r?\n/);
                for (let i=0;i<lines.length;i++) {
                    if (lines[i].startsWith("FINANCEW_HOUSEHOLD_PLAN_RESULT "))
                        store.output=lines[i].slice(30);
                }
            }
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                const same=store.monitoring
                    && store.submittedContext===store.contextId;
                let accepted=false;
                if (exitCode===0 && same && store.output) {
                    try {
                        const doc=JSON.parse(store.output);
                        if (doc && doc.source==="LOCAL_OPERATOR_PLANS"
                                && doc.identityVerified===false
                                && doc.bankVerified===false
                                && doc.version===1
                                && doc.contextId===store.contextId
                                && Number.isSafeInteger(doc.revision)
                                && doc.revision>=0
                                && Array.isArray(doc.rows)
                                && doc.rows.length<=60
                                && doc.rows.every(function(row) {
                                    return row && typeof row.id==="string"
                                        && (row.kind==="goal" || row.kind==="expense")
                                        && typeof row.title==="string"
                                        && Number.isSafeInteger(row.monthlyCents)
                                        && Number.isSafeInteger(row.targetCents)
                                        && Number.isSafeInteger(row.savedCents);
                                })) {
                            store.revision=doc.revision;
                            store.rows=doc.rows;
                            store.state="ready";
                            store.message="LOCAL OPERATOR PLANS // NOT BANK VERIFIED";
                            accepted=true;
                            if (store.activeAction==="add")store.entrySaved();
                            if (store.activeAction==="delete")store.entryDeleted();
                        }
                    } catch(error) { /* Refuse malformed private payload. */ }
                }
                if (!accepted && same) {
                    store.rows=[];
                    store.revision=0;
                    store.state="failed";
                    store.message="PLAN STORE UNAVAILABLE // REFRESH BEFORE RETRY";
                }
                store.output="";
                store.activeAction="";
                if (store.pendingReload || (store.monitoring && !same)) {
                    store.pendingReload=false;
                    store.state="idle";
                    store.refresh();
                }
            });
        }
    }
}
