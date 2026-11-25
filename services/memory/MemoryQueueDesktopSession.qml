import QtQuick
import Quickshell.Io
import "MemoryQueueSessionHost.js" as Host
import "../../widgets/cpuplus/CpuPlusQueueConsumer.js" as Consumer
import "../../widgets/cpuplus/CpuPlusQueueRecovery.js" as Recovery

// Unmounted recovery-only desktop composition. Trusted launch configuration
// belongs to the containing shell, not a widget or a user-supplied command.
// No PREPARE/COMMIT, startup unlock, automatic retry or process respawn API.
QtObject {
    id: root
    property string pythonPath: ""
    property string ownerPath: ""
    property string helperPath: ""
    property string checkpointDirectory: ""
    readonly property string phase: ctl.phase
    readonly property string failure: ctl.failure
    readonly property int generation: ctl.epoch
    readonly property int storageGeneration: ctl.loaded?.snapshot?.generation ?? -1
    readonly property bool startupLocked: true
    readonly property bool canExecute: false
    readonly property var recoveryContext: copy(Host.recoveryContext(hub.hostState))
    readonly property var reviewContext: copy(Host.reviewContext(hub.hostState))
    readonly property var dispositionContext: copy(Host.dispositionContext(hub.hostState))
    readonly property var retentionSelection: ctl.phase==="ACTIVE" && hub.hostState.retentionProof
        && ctl.loaded?.snapshot?.checkpoint?.dismissal
        ? copy({storageGeneration:ctl.loaded.snapshot.generation,
            actionId:hub.hostState.retentionProof.receipt.review.action_id,
            reviewDigest:hub.hostState.retentionProof.receipt.review.review_digest,
            sequence:hub.hostState.retentionProof.sequence}) : null

    function copy(v) { return JSON.parse(JSON.stringify(v)); }
    function guarded(f) {
        if (ctl.entered || ctl.phase==="FAILED") return false;
        ctl.entered=true;
        try { return f(); }
        catch (_) { fail("WRAPPER_TRANSITION_FAILED"); return false; }
        finally { ctl.entered=false; }
    }
    function config() { return [pythonPath,ownerPath,helperPath,checkpointDirectory]; }
    function checkConfig() {
        const c=config();
        return c.every(x=>x.startsWith("/") && !/[\x00-\x1f]/.test(x))
            // Host.equal compares record objects, not arrays. Compare each
            // pinned path by position without weakening configuration custody.
            && (!ctl.paths || (Array.isArray(ctl.paths) && ctl.paths.length===c.length
                && c.every((value,index)=>value===ctl.paths[index])));
    }
    function fail(reason) {
        if (ctl.phase==="FAILED") return;
        ctl.phase="FAILED";
        ctl.failure=reason;
        ctl.io=null;
        ctl.advance=null;
        ctl.loaded=null;
        retirement.stop();
        hub.publishState(Host.stop(hub.hostState,Consumer,reason,ctl.epoch));
        helper.cancel();
        if (ctl.child) { ctl.child.stdinEnabled=false; ctl.child.running=false; }
    }
    function configurationChanged() {
        if (ctl.paths && !checkConfig()) fail("LAUNCH_CONFIGURATION_CHANGED");
    }
    onPythonPathChanged: configurationChanged()
    onOwnerPathChanged: configurationChanged()
    onHelperPathChanged: configurationChanged()
    onCheckpointDirectoryChanged: configurationChanged()

    function open() {
        return guarded(()=>{
            if (ctl.phase!=="IDLE" || ctl.child || helper.busy || !checkConfig()
                || ctl.epoch>=2147483646) return false;
            if (!ctl.paths) ctl.paths=config();
            ++ctl.epoch;
            ctl.phase="LOADING";
            return beginIo("GEN_LOAD",null);
        });
    }
    function active() {
        return ctl.phase==="ACTIVE" && !!ctl.child && ctl.child.running
            && hub.hostState.phase==="CONNECTED" && !helper.busy && !ctl.io
            && checkConfig();
    }
    function writeTransition(next) {
        if (!next || !next.frame || !ctl.child || ctl.phase!=="ACTIVE"
            || !hub.publishState(next.state) || ctl.phase!=="ACTIVE") return false;
        ctl.child.write(next.frame);
        return true;
    }
    function readInventory(limit) {
        return guarded(()=>active() && writeTransition(Host.readRecovery(hub.hostState,"INVENTORY",limit)));
    }
    function readAction(actionId) {
        return guarded(()=>active() && writeTransition(Host.readRecovery(hub.hostState,"LOCAL_ACTION",actionId)));
    }
    function beginReview(actionId) {
        return guarded(()=>active() && hub.hostState.session.unresolved?.action_id===actionId
            && writeTransition(Host.beginReview(hub.hostState,actionId)));
    }
    function acknowledge(selection) {
        return guarded(()=>active() && saveTransition(Host.acknowledgeReview(
            hub.hostState,selection,ctl.epoch,Recovery.row)));
    }
    function dismiss(selection) {
        return guarded(()=>active() && saveTransition(Host.dismissReview(
            hub.hostState,selection,ctl.epoch,Recovery.row)));
    }
    function readAcknowledgment(reviewId) {
        return guarded(()=>active() && writeTransition(Host.readReviewReceipt(hub.hostState,reviewId)));
    }
    function readDisposition(actionId) {
        // Require a new LOAD of the durable dismissal intent before history
        // can be considered for retention. Close and reopen explicitly.
        return guarded(()=>active()
            && ctl.loaded?.snapshot?.checkpoint?.dismissal?.review?.action_id===actionId
            && writeTransition(Host.readDispositionReceipt(hub.hostState,actionId)));
    }
    function saveTransition(next) {
        if (!next?.checkpoint || next.frame || !ctl.loaded || ctl.loaded.snapshot.sealed) return false;
        if (!hub.publishState(next.state) || ctl.phase!=="ACTIVE") return false;
        return beginIo("GEN_SAVE",{version:1,generation:ctl.loaded.snapshot.generation,record:next.checkpoint});
    }
    function close() {
        return guarded(()=>{
            if (ctl.phase!=="ACTIVE" || !ctl.child || helper.busy || ctl.io) return false;
            return retire(Host.stop(hub.hostState,Consumer,null,ctl.epoch),"CLOSING");
        });
    }
    function advance(selection) {
        return guarded(()=>{
            if (!active()) return false;
            const next=Host.takeRetentionAdvance(hub.hostState,selection,ctl.loaded,ctl.epoch,Consumer,Recovery.row);
            if (!next.request || next.frame || !next.state.retentionPending) return false;
            ctl.advance=copy(next.request);
            return retire(next.state,"ADVANCE_EXIT");
        });
    }
    function retire(next,phaseName) {
        if (!ctl.child || next.phase!=="STOPPED" || !next.startupLocked) return false;
        ctl.phase=phaseName;
        if (!hub.publishState(next)) { fail("RETIRE_PUBLISH_FAILED");return false; }
        retirement.restart();
        ctl.child.stdinEnabled=false;
        return true;
    }
    function beginIo(operation,record) {
        if (ctl.io || !checkConfig()) { fail("CHECKPOINT_CONFIGURATION"); return false; }
        ctl.io={operation,epoch:ctl.epoch,record:record===null?null:copy(record),ticket:0};
        const ticket=helper.begin(operation,ctl.epoch,record);
        if (!ticket) { fail("CHECKPOINT_START_FAILED"); return false; }
        ctl.io=Object.assign({},ctl.io,{ticket});
        return true;
    }
    function completeIo(epoch,ticket,operation,result) {
        if (ctl.phase==="FAILED")return;
        if (ctl.entered) { fail("CHECKPOINT_CALLBACK_REENTRY");return; }
        guarded(()=>finishIo(epoch,ticket,operation,result));
    }
    function finishIo(epoch,ticket,operation,result) {
        const q=ctl.io;
        ctl.io=null;
        if (!q || q.epoch!==epoch || epoch!==ctl.epoch || q.ticket!==ticket
            || q.operation!==operation || !result || result.can_execute!==false || !checkConfig()) {
            fail("CHECKPOINT_RESULT_UNKNOWN");return;
        }
        if (operation==="GEN_SAVE" && ctl.phase==="ACTIVE" && ctl.child
            && result.generation===q.record.generation && Host.equal(result.record,q.record.record)) {
            const next=Host.finishCheckpoint(hub.hostState,{version:1,kind:"CHECKPOINT_SAVED",
                record:result.record,can_execute:false},epoch,Consumer,Recovery.row);
            if (!writeTransition(next)) fail("CHECKPOINT_FRAME_REFUSED");
            return;
        }
        if (operation==="GEN_ADVANCE" && ctl.phase==="ADVANCING" && !ctl.child && ctl.advance
            && result.generation===ctl.advance.generation+1
            && result.action_id===ctl.advance.receipt.review.action_id && result.startup_unlock===false) {
            ctl.phase="RELOADING";
            Qt.callLater(()=>{if (ctl.phase==="RELOADING" && ctl.epoch===epoch && !ctl.child)
                guarded(()=>beginIo("GEN_LOAD",null));});
            return;
        }
        if (operation!=="GEN_LOAD" || !["LOADING","RELOADING"].includes(ctl.phase) || ctl.child) {
            fail("CHECKPOINT_PHASE_MISMATCH");return;
        }
        const snapshot=result.snapshot;
        const restored=Host.restoreCheckpoint(Consumer,snapshot.checkpoint,Recovery.row);
        if (!restored || !restored.startupLocked || snapshot.startup_unlock!==false || snapshot.can_execute!==false
            || (snapshot.sealed && (!restored.dispositionLost
                || !Host.dispositionValue(snapshot.receipt,Recovery.row)
                || !Host.equal(snapshot.receipt.review,restored.dispositionLost)))) {
            fail("CHECKPOINT_RESTORE_REFUSED");return;
        }
        if (ctl.phase==="RELOADING") {
            if (!ctl.advance || snapshot.generation!==ctl.advance.generation+1 || snapshot.sealed
                || restored.session.unresolved || restored.session.pending || restored.reviewLost || restored.dispositionLost) {
                fail("RETENTION_RELOAD_MISMATCH");return;
            }
            ctl.advance=null;
            ctl.loaded=copy(result);
            if (!hub.publishState(Object.assign({},restored,{generation:epoch}))) {
                fail("RESTORE_PUBLISH_FAILED");return;
            }
            ctl.phase="IDLE"; // No automatic launch or retry.
            return;
        }
        ctl.loaded=copy(result);
        const next=Host.start(restored,Consumer,epoch,"STAGED",true,true,true,true);
        if (next.phase!=="HELLO" || !next.startupLocked) { fail("HOST_START_REFUSED");return; }
        const process=childFactory.createObject(root,{epoch:epoch,
            command:[ctl.paths[0],"-B",ctl.paths[1],String(epoch)]});
        if (!process) { fail("OWNER_CREATE_FAILED");return; }
        ctl.child=process;
        ctl.phase="ACTIVE";
        if (!hub.publishState(next) || ctl.phase!=="ACTIVE") { fail("HOST_START_PUBLISH_FAILED");return; }
        process.running=true;
    }
    function receive(process,epoch,line) {
        if (process!==ctl.child || epoch!==ctl.epoch || ctl.phase!=="ACTIVE")return;
        if (ctl.entered || !checkConfig()) { fail("OWNER_CHANNEL_REENTRY");return; }
        ctl.entered=true;
        try {
            if (!hub.receive(line,epoch) || hub.hostState.phase==="FAILED") {
                fail("OWNER_PROTOCOL_FAILED");return;
            }
            if (hub.hostState.dispositionConnectPending
                && !writeTransition(Host.takeDispositionConnect(hub.hostState,epoch))) fail("OWNER_HANDSHAKE_FAILED");
        } catch (_) { fail("OWNER_CHANNEL_FAILED"); }
        finally { ctl.entered=false; }
    }
    function exited(process,epoch,code,status) {
        if (process!==ctl.child || epoch!==ctl.epoch) return;
        if (ctl.phase==="FAILED") { ctl.child=null; process.destroy();return; }
        if (ctl.entered) { fail("OWNER_EXIT_REENTRY");return; }
        guarded(()=>finishExit(process,epoch,code,status));
    }
    function finishExit(process,epoch,code,status) {
        ctl.child=null;
        retirement.stop();
        process.destroy();
        if (ctl.phase==="FAILED")return;
        if (code!==0 || status!==0 || !["CLOSING","ADVANCE_EXIT"].includes(ctl.phase)) {
            fail("OWNER_EXIT_UNEXPECTED");return;
        }
        if (ctl.phase==="CLOSING") {
            ctl.loaded=null;
            ctl.phase="IDLE";
        } else {
            if (!ctl.advance || !hub.hostState.retentionPending || hub.hostState.phase!=="STOPPED") {
                fail("RETENTION_EXIT_MISMATCH");return;
            }
            // Exact Process object delivered its exit callback. No running
            // flag, PID lookup or timeout alone can release this transition.
            ctl.phase="ADVANCING";
            Qt.callLater(()=>{if (ctl.phase==="ADVANCING" && ctl.epoch===epoch && !ctl.child)
                guarded(()=>beginIo("GEN_ADVANCE",ctl.advance));});
        }
    }

    property QtObject internals: QtObject {
        id: ctl
        property string phase: "IDLE"
        property string failure: ""
        property int epoch: 0
        property bool entered: false
        property var paths: null
        property var child: null
        property var loaded: null
        property var io: null
        property var advance: null
    }
    property MemoryQueueHubBinding hubBinding: MemoryQueueHubBinding { id: hub }
    property MemoryQueueCheckpointAdapter checkpointAdapter: MemoryQueueCheckpointAdapter {
        id: helper
        generationMode: true
        pythonPath: ctl.paths ? ctl.paths[0] : ""
        helperPath: ctl.paths ? ctl.paths[2] : ""
        directory: ctl.paths ? ctl.paths[3] : ""
        timeoutMs: 8000
        onCompleted: (epoch,ticket,operation,result)=>root.completeIo(epoch,ticket,operation,result)
    }
    property MemoryQueueSessionWatchdog deadlineDriver: MemoryQueueSessionWatchdog {
        hostState: hub.hostState
        timeouts: ({HELLO:8000,PUBLICATION:8000,ACTION:8000,HISTORY:8000,RECOVERY:8000,PARTIAL_FRAME:8000})
        onDeadlineExpired: (epoch,category,ticket)=>{if (epoch===ctl.epoch) root.fail("OWNER_DEADLINE_"+category);}
        onPolicyRejected: epoch=>{if (epoch===ctl.epoch) root.fail("OWNER_DEADLINE_POLICY");}
    }
    property Timer retirementDeadline: Timer {
        id: retirement
        interval: 8000
        repeat: false
        onTriggered: root.fail("OWNER_RETIREMENT_TIMEOUT")
    }
    property Component ownerFactory: Component {
        id: childFactory
        Process {
            id: ownerProcess
            required property int epoch
            stdinEnabled: true
            stdout: SplitParser { onRead: line=>root.receive(ownerProcess,ownerProcess.epoch,line) }
            // Do not print backend data or accept it as authority.
            stderr: SplitParser { onRead: line=>{if (line.length && ctl.child===ownerProcess
                && ownerProcess.epoch===ctl.epoch && ctl.phase!=="FAILED") root.fail("OWNER_STDERR");} }
            onExited: (code,status)=>root.exited(ownerProcess,ownerProcess.epoch,code,status)
        }
    }
}
