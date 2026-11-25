import QtQuick
import QtQuick.Window
import Quickshell
import "services/memory" as Memory
import "widgets/cpuplus"

ShellRoot {
    id: smoke
    readonly property string trial: Quickshell.env("POST_APOLLO_WRAPPER_TRIAL") || ""
    readonly property string rootPath: Quickshell.env("POST_APOLLO_WRAPPER_ROOT") || ""
    readonly property string actionId: "c23683a9-b2ab-4a2c-87ce-000000000062"
    readonly property bool committed: trial.startsWith("COMMITTED")
    readonly property bool missing: trial.endsWith("MISSING")
    property int step: 0
    property int ticks: 0
    property int selectedInventories: 0
    property bool done: false
    Memory.MemoryQueueDesktopSession {
        id: session
        pythonPath: "/usr/bin/python3"
        ownerPath: smoke.rootPath+"/child.py"
        custodyLauncherPath: smoke.rootPath+"/services/memory/memory_queue_custody.py"
        helperPath: smoke.rootPath+"/helper.py"
        checkpointDirectory: smoke.rootPath+"/checkpoint"
    }
    Window {
        width: 340
        height: 680
        visible: true
        Flickable {
            anchors.fill: parent
            contentWidth: width
            contentHeight: work.implicitHeight
            clip: true
            CpuPlusAutoWorkspace {
                id: work
                width: parent.width
                observedDiskKiB: 16777216
                capacityTargetGiB: 24
                recoverySession: session
                section: "RECOVERY"
            }
        }
    }
    function find(item,name) {
        if (!item)return null;
        if(item.objectName===name)return item;
        for(const c of item.children||[]){const v=find(c,name);if(v)return v;}
        return null;
    }
    function check(ok,label) {
        if(!ok){console.error("R6H_FAIL // "+trial+" // "+label+" // "+session.phase+" // "+session.failure);done=true;Qt.quit();}
        return ok;
    }
    function click(name) {
        const b=find(work,name);
        if(!b || !b.available || !b.visible)return false;
        b.leftClicked(null);
        return true;
    }
    function pass() {
        if(!check(selectedInventories===(trial==="LIVE"?2:1),"actual inventory selection count"))return;
        console.log("CPU_M8D_V2_SELECTION_PASS // "+trial);
        console.log("CPU_M8B_CONTROLS_PASS // "+trial);
        console.log("R6H_NATIVE_PASS // "+trial);
        done=true;Qt.quit();
    }
    Timer {
        interval: 25
        repeat: true
        running: !smoke.done
        onTriggered: {
            if(++smoke.ticks>1200||session.phase==="FAILED"){smoke.check(false,"deadline step "+smoke.step);return;}
            if(!smoke.check(session.startupLocked&&!session.canExecute,"locked"))return;
            const pane=smoke.find(work,"cpuplusQueueRecoveryPane");
            if(!pane)return;
            if(smoke.step===0&&session.phase==="IDLE"){
                pane.lookupText="";
                if(smoke.click("cpuplusRecoverySessionOpen"))smoke.step=10;
            }else if((smoke.step===10||smoke.step===60)&&session.phase==="ACTIVE"){
                pane.lookupText="";
                if(smoke.click("cpuplusRecoveryInventoryRead")&&session.recoveryContext.recoveryPending)
                    smoke.step=smoke.step===10?11:61;
            }else if((smoke.step===11||smoke.step===61)&&pane.view){
                const inventory=pane.view;
                const expectedDismissed=smoke.trial==="RECOVERED"||smoke.step===61;
                if(!smoke.check(pane.inventoryLimit===4&&inventory.recent.length===1
                    && inventory.recent[0].actionId===smoke.actionId
                    && inventory.recent[0].dismissed===expectedDismissed
                    && inventory.recent[0].state===(smoke.committed?"COMMITTED":"PREPARED")
                    && (expectedDismissed||smoke.committed ? inventory.prepared===null
                        : inventory.prepared && inventory.prepared.actionId===smoke.actionId),
                    "exact V2 inventory and local disposition"))return;
                pane.selectRecord("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa");
                if(!smoke.check(pane.lookupText==="","unknown subject refused"))return;
                if(!smoke.click("cpuplusRecoverySelectRecord"))return;
                if(!smoke.check(pane.lookupText===smoke.actionId&&!session.recoveryContext.recoveryPending
                    && !session.reviewContext.review && !pane.dismissalConfirmation && !pane.retentionConfirmation,
                    "selection does not dispatch"))return;
                smoke.selectedInventories++;
                smoke.step=smoke.step===11?1:6;
            }else if(smoke.step===1&&session.phase==="ACTIVE"){
                if(smoke.trial==="LIVE"){
                    if(smoke.click("cpuplusRecoveryReviewRequest")&&session.reviewContext.phase==="WAIT_REVIEW")smoke.step=2;
                }else if(smoke.committed){
                    if(smoke.click("cpuplusRecoveryReceiptLookup")&&session.reviewContext.phase==="WAIT_RECEIPT")smoke.step=5;
                }else if(smoke.click("cpuplusRecoveryDispositionLookup")&&session.dispositionContext.phase==="WAIT_DISPOSITION")smoke.step=5;
            }else if(smoke.step===2&&session.dispositionContext.canDismiss){
                if(!smoke.click("cpuplusRecoveryDismissPrepare"))return;
                if(!smoke.check(!!pane.dismissalConfirmation,"frozen selection"))return;
                smoke.click("cpuplusRecoveryDismissCancel");
                if(!smoke.check(!pane.dismissalConfirmation&&session.dispositionContext.canDismiss,"cancel did not dispatch"))return;
                smoke.click("cpuplusRecoveryDismissPrepare");
                if(!smoke.check(smoke.click("cpuplusRecoveryDismissConfirm"),"dismiss confirm"))return;
                if(!smoke.check(!pane.dismissalConfirmation,"consumed confirmation"))return;
                smoke.step=3;
            }else if(smoke.step===3&&session.dispositionContext.receipt){
                if(!smoke.check(pane.dismissedReceipt&&pane.dismissedReceipt.action.actionId===smoke.actionId&&!pane.retainSelection,"live receipt not retention proof"))return;
                if(smoke.click("cpuplusRecoverySessionClose"))smoke.step=4;
            }else if(smoke.step===4&&session.phase==="IDLE"){
                if(smoke.click("cpuplusRecoverySessionOpen"))smoke.step=60;
            }else if(smoke.step===6&&session.phase==="ACTIVE"){
                if(smoke.click("cpuplusRecoveryDispositionLookup")&&session.dispositionContext.phase==="WAIT_DISPOSITION")smoke.step=5;
            }else if(smoke.step===5&&session.retentionSelection){
                if(!smoke.check(!smoke.missing&&pane.retainSelection&&pane.retainSelection.mode===(smoke.committed?"COMMITTED":"DISMISSED"),"exact historical proof presentation"))return;
                if(!smoke.click("cpuplusRecoveryRetainPrepare"))return;
                smoke.click("cpuplusRecoveryRetainCancel");
                if(!smoke.check(!pane.retentionConfirmation&&session.storageGeneration===0,"retention cancel no advance"))return;
                smoke.click("cpuplusRecoveryRetainPrepare");
                if(!smoke.check(smoke.click("cpuplusRecoveryRetainConfirm"),"retention confirm"))return;
                smoke.step=7;
            }else if(smoke.step===5&&smoke.missing&&(smoke.committed?session.reviewContext.phase==="ACK_UNKNOWN":session.dispositionContext.phase==="DISMISS_UNKNOWN")){
                if(!smoke.check(!pane.retainSelection&&!smoke.find(work,"cpuplusRecoveryRetainPrepare").available,"missing refuses retention"))return;
                if(smoke.click("cpuplusRecoverySessionClose"))smoke.step=8;
            }else if(smoke.step===7&&session.phase==="IDLE"){
                if(!smoke.check(session.storageGeneration===1&&!session.retentionSelection&&!session.recoveryContext.hostStatus.unresolved,"new locked generation"))return;
                smoke.pass();
            }else if(smoke.step===8&&session.phase==="IDLE")smoke.pass();
        }
    }
    Component.onCompleted: {
        if(Quickshell.env("POST_APOLLO_QUEUE_PIPE_SMOKE")!=="CI_DISPOSABLE_ONLY"||!["LIVE","RECOVERED","MISSING","COMMITTED","COMMITTED_MISSING"].includes(trial)||!rootPath.startsWith("/tmp/")){done=true;Qt.quit();}
    }
}
