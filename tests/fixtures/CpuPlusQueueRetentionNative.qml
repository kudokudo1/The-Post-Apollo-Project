import QtQuick
import Quickshell
import Quickshell.Io
import "host/MemoryQueueSessionHost.js" as Host
import "widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer
import "widgets/cpuplus/CpuPlusQueuePresentation.js" as Presentation
import "widgets/cpuplus/CpuPlusQueueHistory.js" as History
import "widgets/cpuplus/CpuPlusQueueRecovery.js" as Recovery

// Disposable fixture only. One canonical host, one exact Process instance,
// one fixed helper at a time. No COMMIT, no automatic retry or production mount.
ShellRoot {
    id: smoke
    readonly property string trial: Quickshell.env("POST_APOLLO_RETENTION_TRIAL") || ""
    readonly property string rootPath: Quickshell.env("POST_APOLLO_RETENTION_ROOT") || ""
    property var host: Host.initial(Consumer)
    property int generation: 0
    property string phase: "BOOT"
    property int ticks: 0
    property bool done: false
    property string actionId: "c23683a9-b2ab-4a2c-87ce-000000000061"
    property var loaded: null
    property var advanceRequest: null
    property var helperRequest: null
    property var helperReply: null
    property bool helperInvalid: false
    property int prepWrites: 0
    property int dismissWrites: 0
    property int historyWrites: 0
    function check(ok,label) {
        if (!ok) {
            console.error("R6F_FAIL // "+trial+" // "+phase+" // "+label+" // "+host.failure);
            done=true; child.running=false; helper.running=false; Qt.quit();
        }
        return ok;
    }
    function launch() {
        ++generation;
        host=Host.start(host,Consumer,generation,"STAGED",true,true,false,true);
        if (!check(host.phase==="HELLO" && host.startupLocked,"locked launch"))return;
        child.command=["/usr/bin/python3","-B",rootPath+"/child.py",String(generation)];
        child.stdinEnabled=true;
        child.running=true;
        phase="WAIT_STATUS";
    }
    function send(next) {
        if (!check(!!next.frame,"canonical explicit frame"))return;
        host=next.state;
        child.write(next.frame);
    }
    function io(command,value) {
        if (!check(!helperRequest && !helper.running,"single helper"))return;
        helperRequest={command,value,generation};
        helperReply=null;helperInvalid=false;
        helper.command=["/usr/bin/python3","-B",rootPath+"/helper.py",command,rootPath+"/checkpoint"];
        helper.stdinEnabled=true;
        helper.running=true;
    }
    function checkpoint(next) {
        if (!check(!!next.checkpoint && !next.frame,"durable gate before frame"))return;
        host=next.state;
        io("GEN_SAVE",{version:1,generation:0,record:next.checkpoint});
    }
    function retire(nextPhase) {
        host=Host.stop(host,Consumer,null,generation);
        if (!check(host.phase==="STOPPED" && host.startupLocked,"retire before EOF"))return;
        phase=nextPhase;
        child.stdinEnabled=false;
    }
    function receive(line) {
        if (done) return;
        let p;
        try { p=JSON.parse(line); } catch (_) { check(false,"child JSON");return; }
        if (phase==="WAIT_DISMISS" && trial==="LOST" && p.kind==="LOCAL_DISPOSITION") {
            if (!check(p.receipt?.review?.action_id===actionId,"actual lost reply"))return;
            retire("EXIT_REVIEW");
            return;
        }
        // A retired owner may finish writing its last publication; never
        // deliver it to a retired controller or a new generation.
        if (host.phase==="STOPPED")return;
        host=Host.feed(host,line+"\n",Consumer,Presentation.project,History.project,
            generation,Recovery.project,Recovery.row);
        if (!check(host.phase!=="FAILED","canonical feed "+p.kind))return;
        if (p.kind==="HELLO_DISPOSITION") {
            send(Host.takeDispositionConnect(host,generation));
        } else if (p.kind==="PREPARED_ACTION") {
            if (!check(phase==="WAIT_PREPARED" && host.stage?.phase==="RECEIPT_READY","actual prepared receipt"))return;
            retire("EXIT_PREPARED");
        } else if (p.kind==="LOCAL_DISPOSITION") {
            if (!check(phase==="WAIT_DISMISS" && host.publicationRequired && !host.retentionProof,
                "live dismissal is not history proof"))return;
            phase="WAIT_DISMISS_STATUS";
        } else if (p.kind==="LOCAL_DISPOSITION_HISTORY") {
            if (!check(phase==="WAIT_HISTORY","explicit history response"))return;
            const review=loaded.snapshot.checkpoint.dismissal.review;
            const selection={storageGeneration:0,actionId:actionId,reviewDigest:review.review_digest,sequence:host.sequence};
            const take=(sel,g=generation)=>Host.takeRetentionAdvance(host,sel,loaded,g,Consumer,Recovery.row);
            if (trial==="MISSING") {
                if (!check(p.receipt===null && !!host.dispositionLost && !take(selection).request,
                    "missing history never advances"))return;
                retire("EXIT_MISSING");
                return;
            }
            if (!check(!!p.receipt && Host.equal(p.receipt.review,review)
                && !take(Object.assign({},selection,{sequence:selection.sequence+1})).request
                && !take(selection,generation-1).request,"exact real history and stale refusal"))return;
            const next=take(selection);
            if (!check(!!next.request && !next.frame && next.state.retentionPending
                && next.state.startupLocked && next.state.phase==="STOPPED","retire before advancement"))return;
            host=next.state;
            advanceRequest=next.request;
            phase="EXIT_ADVANCE";
            child.stdinEnabled=false;
        }
    }
    Process {
        id: child
        stdinEnabled: true
        stdout: SplitParser { onRead: data=>smoke.receive(data) }
        stderr: SplitParser { onRead: data=>console.log(data) }
        onExited: (code,status)=>{
            if (smoke.done)return;
            if (!smoke.check(code===0 && status===0 && smoke.host.phase==="STOPPED","exact child exited"))return;
            console.log("R6F_CHILD_EXIT // "+smoke.generation);
            if (smoke.phase==="EXIT_PREPARED") smoke.phase="LAUNCH_REVIEW";
            else if (smoke.phase==="EXIT_REVIEW") smoke.phase="LOAD_REVIEW";
            else if (smoke.phase==="EXIT_ADVANCE") smoke.phase="ADVANCE";
            else if (smoke.phase==="EXIT_MISSING") smoke.phase="FINISH_MISSING";
            else smoke.check(false,"unexpected exit");
        }
    }
    Process {
        id: helper
        stdinEnabled: true
        onStarted: {
            if (!smoke.helperRequest) { running=false;return; }
            if (smoke.helperRequest.value!==null) write(JSON.stringify(smoke.helperRequest.value)+"\n");
            stdinEnabled=false;
        }
        stdout: SplitParser {
            onRead: data=>{
                if (smoke.helperReply!==null || typeof data!=="string" || !data.length || data.length>=16384) {
                    smoke.helperInvalid=true;return;
                }
                try {
                    const p=JSON.parse(data);
                    if (!Host.safe(p) || JSON.stringify(p)!==data) throw Error("noncanonical");
                    smoke.helperReply=p;
                } catch (_) { smoke.helperInvalid=true; }
            }
        }
        stderr: SplitParser { onRead: data=>{smoke.helperInvalid=true;console.error(data);} }
        onExited: (code,status)=>{
            if (smoke.done)return;
            const q=smoke.helperRequest,p=smoke.helperReply;
            smoke.helperRequest=null;
            if (!smoke.check(q && q.generation===smoke.generation && !smoke.helperInvalid
                && code===0 && status===0 && p?.version===1 && p.can_execute===false,"exact helper result"))return;
            if (q.command==="GEN_SAVE") {
                if (!smoke.check(Host.exact(p,["version","kind","generation","record","can_execute"])
                    && p.kind==="CHECKPOINT_GENERATION_SAVED" && p.generation===0
                    && Host.equal(p.record,q.value.record),"actual durable generation save"))return;
                const next=Host.finishCheckpoint(smoke.host,{version:1,kind:"CHECKPOINT_SAVED",
                    record:p.record,can_execute:false},smoke.generation,Consumer,Recovery.row);
                if (!smoke.check(!!next.frame && !next.state.checkpointWait,"release exact checkpoint once"))return;
                smoke.host=next.state;
                if (smoke.phase==="SAVE_ACTION") {
                    ++smoke.prepWrites;smoke.phase="WAIT_PREPARED";child.write(next.frame);
                } else if (smoke.phase==="SAVE_DISMISS") {
                    if (smoke.trial==="MISSING") {
                        smoke.retire("EXIT_REVIEW"); // durable intent, withheld frame
                    } else {
                        ++smoke.dismissWrites;smoke.phase="WAIT_DISMISS";child.write(next.frame);
                    }
                } else smoke.check(false,"unexpected save");
            } else if (q.command==="GEN_LOAD") {
                if (!smoke.check(p.kind==="CHECKPOINT_GENERATION_LOADED" && p.snapshot?.startup_unlock===false
                    && p.snapshot?.can_execute===false,"generation load"))return;
                const restored=Host.restoreCheckpoint(Consumer,p.snapshot.checkpoint,Recovery.row);
                if (!smoke.check(!!restored && restored.startupLocked,"restore locked"))return;
                if (smoke.phase==="WAIT_LOAD") {
                    if (!smoke.check(p.snapshot.generation===0 && !p.snapshot.sealed
                        && restored.dispositionLost?.action_id===smoke.actionId
                        && restored.session.unresolved?.action_id===smoke.actionId,"exact durable identity"))return;
                    smoke.loaded=p;smoke.host=restored;smoke.phase="LAUNCH_HISTORY";
                } else if (smoke.phase==="WAIT_RELOAD") {
                    if (!smoke.check(p.snapshot.generation===1 && !p.snapshot.sealed
                        && !restored.session.unresolved && !restored.session.pending,"fresh locked empty generation"))return;
                    smoke.host=restored;smoke.phase="FINISH";
                } else smoke.check(false,"unexpected load");
            } else if (q.command==="GEN_ADVANCE") {
                if (!smoke.check(smoke.phase==="WAIT_ADVANCE" && smoke.host.retentionPending
                    && p.kind==="CHECKPOINT_GENERATION_ADVANCED" && p.generation===1
                    && p.action_id===smoke.actionId && p.startup_unlock===false,"exact advancement result"))return;
                smoke.phase="RELOAD";
            }
        }
    }
    Timer {
        interval: 25
        repeat: true
        running: !smoke.done
        onTriggered: {
            if (++smoke.ticks>1200){smoke.check(false,"timeout");return;}
            if (smoke.phase==="BOOT" || smoke.phase==="LAUNCH_REVIEW" || smoke.phase==="LAUNCH_HISTORY") {
                if (!child.running && !helper.running) smoke.launch();
            } else if (smoke.phase==="WAIT_STATUS" && smoke.host.session.status && !smoke.host.publicationRequired) {
                if (smoke.generation===1) {
                    const intent=Consumer.prepare(smoke.host.session,"QUEUE",16,Math.floor(Date.now()/1000)+180).prepared;
                    if (!smoke.check(!Host.confirm(smoke.host,intent,smoke.actionId,Consumer).frame,"startup locked"))return;
                    // The fixture alone injects confirmation to create PREPARED evidence.
                    smoke.host=Object.assign({},smoke.host,{startupLocked:false});
                    smoke.phase="SAVE_ACTION";
                    smoke.checkpoint(Host.confirm(smoke.host,intent,smoke.actionId,Consumer));
                } else if (smoke.generation===2) {
                    smoke.phase="WAIT_REVIEW";smoke.send(Host.beginReview(smoke.host,smoke.actionId));
                } else {
                    smoke.phase="WAIT_HISTORY";++smoke.historyWrites;
                    smoke.send(Host.readDispositionReceipt(smoke.host,smoke.actionId));
                }
            } else if (smoke.phase==="WAIT_REVIEW" && Host.dispositionContext(smoke.host).canDismiss) {
                const v=Host.dispositionContext(smoke.host);
                smoke.phase="SAVE_DISMISS";
                smoke.checkpoint(Host.dismissReview(smoke.host,{reviewId:v.review.review_id,
                    digest:v.review.review_digest,sequence:v.reviewSequence},smoke.generation,Recovery.row));
            } else if (smoke.phase==="WAIT_DISMISS_STATUS" && smoke.host.session.status && !smoke.host.publicationRequired) {
                smoke.retire("EXIT_REVIEW");
            } else if (smoke.phase==="LOAD_REVIEW" && !child.running && !helper.running) {
                smoke.phase="WAIT_LOAD";smoke.io("GEN_LOAD",null);
            } else if (smoke.phase==="ADVANCE" && !child.running && !helper.running) {
                smoke.phase="WAIT_ADVANCE";smoke.io("GEN_ADVANCE",smoke.advanceRequest);
            } else if (smoke.phase==="RELOAD" && !helper.running) {
                smoke.phase="WAIT_RELOAD";smoke.io("GEN_LOAD",null);
            } else if (smoke.phase==="FINISH" || smoke.phase==="FINISH_MISSING") {
                if (!smoke.check(smoke.prepWrites===1 && smoke.historyWrites===1
                    && smoke.dismissWrites===(smoke.trial==="MISSING"?0:1)
                    && smoke.host.startupLocked && !child.running && !helper.running,"exact counts and no unlock"))return;
                console.log("R6F_NATIVE_PASS // "+smoke.trial);
                smoke.done=true;Qt.quit();
            }
        }
    }
    Component.onCompleted: {
        if (Quickshell.env("POST_APOLLO_QUEUE_PIPE_SMOKE")!=="CI_DISPOSABLE_ONLY"
            || !["LIVE","LOST","MISSING"].includes(trial) || !rootPath.startsWith("/tmp/"))Qt.quit();
    }
}
