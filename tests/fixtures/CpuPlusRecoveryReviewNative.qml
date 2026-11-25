import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/cpuplus"
import "widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer
import "widgets/cpuplus/CpuPlusQueueRecovery.js" as Recovery
import "services/memory/MemoryQueueSessionHost.js" as Host

// Native QML interaction against the real host transitions, with synthetic
// validated evidence. No pipe dispatch, storage or protected operations.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_QUEUE_PIPE_SMOKE")==="CI_DISPOSABLE_ONLY"
    property string oldOwner: "11111111-1111-1111-1111-111111111111"
    property string owner: "22222222-2222-2222-2222-222222222222"
    property string actionId: "33333333-3333-3333-3333-333333333333"
    property string reviewId: "44444444-4444-4444-4444-444444444444"
    property var host: Host.initial(Consumer)
    property var readyState: null
    property int phase: 0
    property int ticks: 0
    property int reviewCount: 0
    property int ackCount: 0
    property int receiptCount: 0
    property int otherCount: 0
    property bool failed: false
    property bool mounted: true
    function check(ok,label) {
        if(!ok){failed=true;console.error("CPU_RECOVERY_REVIEW_NATIVE_FAIL // "+label);Qt.quit();}
        return ok;
    }
    function find(item,name) {
        if(!item)return null;
        if(item.objectName===name)return item;
        for(const c of item.children||[]){const v=find(c,name);if(v)return v;}
        return null;
    }
    function installReview() {
        const record={version:1,ordinal:1,message:{version:1,owner_id:oldOwner,action_id:actionId,action_sequence:1,kind:"QUEUE",expected_request_id:null,target_gib:24,expires_at:200},state:"PREPARED",prepared_at:100,result_request_id:null,committed_at:null,adjustment_outcome:"UNVERIFIED",can_execute:false};
        const review={version:1,review_id:reviewId,owner_id:owner,action_id:actionId,snapshot:{version:1,record,pending_request_id:null,pending_digest:"a".repeat(64),adjustment_outcome:"UNVERIFIED",can_execute:false,startup_unlock:false},review_digest:"b".repeat(64),reviewed_at_ms:100000,can_execute:false,startup_unlock:false};
        host=Object.assign({},host,{reviewFlow:{phase:"REVIEW_READY",review,sequence:9}});
        readyState=host;
    }
    function launch() {
        const initial=Host.start(host,Consumer,4294967297,"STAGED",true);
        host=Object.assign({},initial,{phase:"CONNECTED",session:Object.assign({},Consumer.connect(initial.session,owner),{status:{state:"IDLE REPORTED",requestId:null}})});
    }
    Window {
        width: 320
        height: 620
        visible: smoke.armed
        Flickable {
            anchors.fill: parent
            contentWidth: width
            contentHeight: workspace.item?workspace.item.implicitHeight:0
            clip: true
            Loader {
                id: workspace
                width: parent.width
                active: smoke.mounted
                sourceComponent: CpuPlusAutoWorkspace {
                    observedDiskKiB: 16777216
                    capacityTargetGiB: 24
                    hostState: smoke.host
                    onReviewRequested: actionId=>{
                        const t=Host.beginReview(smoke.host,actionId);
                        if(smoke.check(!!t.frame,"accepted review intent")){smoke.host=t.state;smoke.reviewCount++;}
                    }
                    onAcknowledgmentRequested: (selection,generation)=>{
                        const t=Host.acknowledgeReview(smoke.host,selection,generation,Recovery.row);
                        if(smoke.check(!!t.frame&&generation===4294967297,"exact ACK generation")){smoke.host=t.state;smoke.ackCount++;}
                    }
                    onReviewReceiptRequested: reviewId=>{
                        const t=Host.readReviewReceipt(smoke.host,reviewId);
                        if(smoke.check(!!t.frame&&reviewId===smoke.reviewId,"exact historical receipt intent")){smoke.host=t.state;smoke.receiptCount++;}
                    }
                    onIntentConfirmed: intent=>smoke.otherCount++
                    onHistoryReadRequested: requestId=>smoke.otherCount++
                    onRecoveryReadRequested: (kind,value)=>smoke.otherCount++
                }
            }
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: smoke.armed&&!smoke.failed
        onTriggered: {
            if(++smoke.ticks>100){smoke.check(false,"timeout phase "+smoke.phase);return;}
            const w=workspace.item;
            const p=smoke.find(w,"cpuplusQueueRecoveryPane");
            if(smoke.phase===0&&w){w.selectSection("RECOVERY");smoke.phase=1;return;}
            if(smoke.phase===4&&!workspace.item){smoke.mounted=true;smoke.phase=5;return;}
            if(smoke.phase===5&&w&&!p){w.selectSection("RECOVERY");return;}
            if(!p)return;
            const request=smoke.find(p,"cpuplusRecoveryReviewRequest");
            const prepare=smoke.find(p,"cpuplusRecoveryAckPrepare");
            const confirm=smoke.find(p,"cpuplusRecoveryAckConfirm");
            const lookup=smoke.find(p,"cpuplusRecoveryReceiptLookup");
            const cancel=smoke.find(p,"cpuplusRecoveryAckCancel");
            if(!request||!prepare||!confirm||!lookup||!cancel)return;
            if(smoke.phase===1){
                p.lookupText=smoke.actionId;
                if(!smoke.check(request.available&&!prepare.available,"review available before evidence"))return;
                request.leftClicked(null);request.leftClicked(null);
                if(!smoke.check(smoke.reviewCount===1&&smoke.host.reviewFlow.phase==="WAIT_REVIEW","one explicit review"))return;
                smoke.installReview();smoke.phase=2;return;
            }
            if(smoke.phase===2){
                if(!smoke.check(prepare.available&&!w.readAvailable&&p.reviewEvidence.action.target===24,"ready evidence blocks other reads"))return;
                prepare.leftClicked(null);
                if(!smoke.check(!!p.confirmation&&smoke.ackCount===0,"first click freezes only"))return;
                cancel.leftClicked(null);confirm.leftClicked(null);
                if(!smoke.check(!p.confirmation&&smoke.ackCount===0,"explicit cancel emits no ACK"))return;
                prepare.leftClicked(null);
                smoke.host=Object.assign({},smoke.host,{reviewFlow:Object.assign({},smoke.host.reviewFlow,{review:Object.assign({},smoke.host.reviewFlow.review,{review_digest:"c".repeat(64)})})});
                smoke.phase=21;return;
            }
            if(smoke.phase===21){
                confirm.leftClicked(null);
                if(!smoke.check(!p.confirmation&&smoke.ackCount===0,"changed digest cancels confirmation"))return;
                prepare.leftClicked(null);
                smoke.host=Object.assign({},smoke.host,{generation:4294967298});
                smoke.phase=22;return;
            }
            if(smoke.phase===22){
                confirm.leftClicked(null);
                if(!smoke.check(!p.confirmation&&smoke.ackCount===0,"changed generation cancels confirmation"))return;
                smoke.host=Object.assign({},smoke.host,{generation:4294967297});
                smoke.phase=23;return;
            }
            if(smoke.phase===23){
                prepare.leftClicked(null);
                smoke.host=Object.assign({},smoke.host,{checkpointWait:{record:{kind:"REVIEW_ACK"}}});
                smoke.phase=24;return;
            }
            if(smoke.phase===24){
                confirm.leftClicked(null);prepare.leftClicked(null);request.leftClicked(null);lookup.leftClicked(null);
                if(!smoke.check(!p.confirmation&&!prepare.available&&!lookup.available&&!request.available&&smoke.ackCount===0
                    &&p.reviewContext.phase==="WAIT_CHECKPOINT","checkpoint wait blocks controls"))return;
                smoke.host=Object.assign({},smoke.host,{checkpointWait:null});
                smoke.phase=25;return;
            }
            if(smoke.phase===25){
                prepare.leftClicked(null);
                smoke.host=Object.assign({},smoke.host,{reviewFlow:Object.assign({},smoke.host.reviewFlow,{sequence:10})});
                smoke.phase=3;return;
            }
            if(smoke.phase===3){
                confirm.leftClicked(null);
                if(!smoke.check(!p.confirmation&&smoke.ackCount===0,"changed sequence cancels confirmation"))return;
                prepare.leftClicked(null);
                if(!smoke.check(!!p.confirmation,"second selection prepared"))return;
                smoke.mounted=false;smoke.phase=4;return;
            }
            if(smoke.phase===5){
                if(!smoke.check(!p.confirmation&&smoke.ackCount===0,"no replay on reopen"))return;
                prepare.leftClicked(null);
                confirm.leftClicked(null);confirm.leftClicked(null);
                if(!smoke.check(smoke.ackCount===1&&smoke.host.reviewFlow.phase==="WAIT_ACK","one explicit ACK"))return;
                smoke.host=Host.stop(smoke.host,Consumer,"LOST",smoke.host.generation);
                smoke.phase=6;return;
            }
            if(smoke.phase===6){
                prepare.leftClicked(null);lookup.leftClicked(null);
                if(!smoke.check(!prepare.available&&!lookup.available&&p.unknownReviewId===smoke.reviewId&&smoke.receiptCount===0,"disconnected ACK unknown"))return;
                const next=Host.start(smoke.host,Consumer,4294967298,"STAGED",true);
                smoke.host=Object.assign({},next,{phase:"CONNECTED",session:Object.assign({},Consumer.connect(next.session,"55555555-5555-5555-5555-555555555555"),{status:{state:"IDLE REPORTED",requestId:null}})});
                smoke.phase=7;return;
            }
            if(smoke.phase===7){
                p.receiptLookup=smoke.actionId;
                if(!smoke.check(!request.available&&lookup.available&&p.effectiveReceiptId===smoke.reviewId,"unknown review forces exact receipt ID"))return;
                lookup.leftClicked(null);lookup.leftClicked(null);
                if(!smoke.check(smoke.receiptCount===1&&smoke.ackCount===1&&smoke.otherCount===0&&smoke.host.startupLocked&&smoke.host.reviewFlow.phase==="WAIT_RECEIPT","one receipt lookup, no retry or unlock"))return;
                const receipt={version:1,review:smoke.host.reviewLost,acknowledged_at_ms:100001,disposition:"REVIEW_ACKNOWLEDGED_ONLY",adjustment_outcome:"UNVERIFIED",can_execute:false,startup_unlock:false};
                smoke.host=Object.assign({},smoke.host,{reviewFlow:null,reviewLost:null,reviewReceipt:receipt});
                smoke.phase=8;return;
            }
            if(smoke.phase===8){
                if(!smoke.check(p.reviewReceipt&&p.reviewReceipt.reviewId===smoke.reviewId
                    &&p.reviewReceipt.action.actionId===smoke.actionId&&!p.unknownReviewId
                    &&!prepare.available&&smoke.ackCount===1&&smoke.host.startupLocked,"historical receipt displayed without authority"))return;
                console.log("CPU_RECOVERY_REVIEW_NATIVE_PASS // explicit review, cancel, digest/generation/sequence invalidation, checkpoint wait, reopen, single ACK, lost receipt correlation and historical receipt");
                Qt.quit();
            }
        }
    }
    Component.onCompleted: if(!armed)Qt.quit();else launch()
}
