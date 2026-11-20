import QtQuick
import Quickshell
import Quickshell.Io

// FP1e schedule metadata only. Never reads bank, Actual, Social or Connections.
Scope {
    id: store
    property string contextId: "mine"
    property bool monitoring: false
    property var rows: []
    property int revision: 0
    property string state: "idle"
    property string message: "SCHEDULES NOT LOADED"
    property string inputFrame: ""
    property string output: ""
    property string activeAction: ""
    property string submittedContext: ""
    property bool pendingReload: false
    signal scheduleSaved()
    signal scheduleUpdated()
    signal scheduleDeleted()

    function clearView() {
        rows=[];
        revision=0;
        state="idle";
        message="SCHEDULES NOT LOADED";
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
    function validContext() {
        return /^(mine|shared|mom|granny|family)$/.test(contextId);
    }
    function refresh() {
        if (!monitoring || !validContext()) return false;
        rows=[];
        revision=0;
        if (worker.running || state==="pending" || state==="loading") {
            pendingReload=true;
            state="loading";
            message="WAITING TO READ SELECTED SCHEDULE";
            return false;
        }
        return invoke({action:"list",contextId:contextId});
    }
    function invoke(command) {
        if (!monitoring || !validContext() || worker.running
                || state==="pending" || state==="loading") return false;
        submittedContext=contextId;
        activeAction=command.action;
        output="";
        inputFrame=JSON.stringify(command)+"\n";
        state=command.action==="list"?"loading":"pending";
        message=command.action==="list"
            ?"READING LOCAL SCHEDULE":"SAVING LOCAL SCHEDULE";
        worker.exec({
            command:["/usr/bin/python3","-B",
                Quickshell.shellPath("scripts/finance/household_schedule_store.py")],
            environment: ({ACTUAL_PASSWORD_FILE:null,ACTUAL_SYNC_ID:null,
                ACTUAL_SERVER_URL:null,ACTUAL_SYNC_ID_FILE:null})
        });
        return true;
    }
    function addBill(expenseId,dueDay) {
        if (state!=="ready" || !monitoring) return false;
        return invoke({action:"add_bill",contextId:contextId,
            expectedRevision:revision,expenseId:expenseId,dueDay:dueDay});
    }
    function addPurchase(title,date,amountText,fundingGoalId) {
        if (state!=="ready" || !monitoring) return false;
        return invoke({action:"add_purchase",contextId:contextId,
            expectedRevision:revision,title:title,date:date,
            amountText:amountText,fundingGoalId:fundingGoalId || ""});
    }
    function updateBill(id,expenseId,dueDay) {
        if (state!=="ready" || !monitoring) return false;
        return invoke({action:"update_bill",contextId:contextId,
            expectedRevision:revision,id:id,expenseId:expenseId,dueDay:dueDay});
    }
    function updatePurchase(id,title,date,amountText,fundingGoalId) {
        if (state!=="ready" || !monitoring) return false;
        return invoke({action:"update_purchase",contextId:contextId,
            expectedRevision:revision,id:id,title:title,date:date,
            amountText:amountText,fundingGoalId:fundingGoalId || ""});
    }
    function addSkip(expenseId,month) {
        if (state!=="ready" || !monitoring) return false;
        return invoke({action:"add_skip",contextId:contextId,
            expectedRevision:revision,expenseId:expenseId,month:month});
    }
    function updateSkip(id,expenseId,month) {
        if (state!=="ready" || !monitoring) return false;
        return invoke({action:"update_skip",contextId:contextId,
            expectedRevision:revision,id:id,expenseId:expenseId,month:month});
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
                const prefix="FINANCEW_HOUSEHOLD_SCHEDULE_RESULT ";
                const lines=String(text || "").split(/\r?\n/);
                for (let i=0;i<lines.length;i++) {
                    if (lines[i].startsWith(prefix))
                        store.output=lines[i].slice(prefix.length);
                }
            }
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                const same=store.monitoring
                    && store.submittedContext===store.contextId;
                let accepted=false;
                if (exitCode===0 && store.output && same) {
                    try {
                        const doc=JSON.parse(store.output);
                        if (doc && doc.source==="LOCAL_OPERATOR_SCHEDULES"
                                && doc.bankVerified===false
                                && doc.identityVerified===false
                                && doc.version===2
                                && doc.contextId===store.contextId
                                && Number.isSafeInteger(doc.revision)
                                && doc.revision>=0
                                && Array.isArray(doc.rows)
                                && doc.rows.length<=60
                                && doc.rows.every(function(row) {
                                    return row && typeof row.id==="string"
                                        && (row.kind==="bill_due" || row.kind==="purchase" || row.kind==="bill_skip")
                                        && typeof row.title==="string"
                                        && typeof row.expenseId==="string"
                                        && typeof row.date==="string"
                                        && typeof row.fundingGoalId==="string"
                                        && Number.isSafeInteger(row.dueDay)
                                        && Number.isSafeInteger(row.amountCents);
                                })) {
                            store.rows=doc.rows;
                            store.revision=doc.revision;
                            store.state="ready";
                            store.message="LOCAL SCHEDULE // NOT BANK VERIFIED";
                            accepted=true;
                            if (store.activeAction==="add_bill"
                                    || store.activeAction==="add_purchase")
                                store.scheduleSaved();
                            if (store.activeAction==="delete")
                                store.scheduleDeleted();
                            if (store.activeAction.indexOf("update_")===0)
                                store.scheduleUpdated();
                        }
                    } catch(error) { /* No private payload in logs. */ }
                }
                if (!accepted && same) {
                    store.rows=[];
                    store.revision=0;
                    store.state="failed";
                    store.message="SCHEDULE ERROR // REFRESH BEFORE RETRY";
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
