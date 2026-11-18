"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
    fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const qml=read("services/time/AlarmManagerService.qml"), policy={};
vm.runInNewContext(read("services/time/AlarmWriterDrainPolicy.js")
    .replace(/^\.pragma library\s*$/m,""),policy);
const plain=v=>JSON.parse(JSON.stringify(v));
const ready=(x={})=>({storageState:"ready",pendingWrite:false,
    queuedWrite:false,migrationRequested:false,ringingCount:0,previewing:false,
    audioState:"IDLE",notificationOutcome:"DELIVERED",...x});
function body(start){
    const i=qml.indexOf("{",start);assert(i>=0);
    let depth=0;
    for(let j=i;j<qml.length;j++){
        if(qml[j]==="{")depth++;
        if(qml[j]==="}" && --depth===0)return qml.slice(i+1,j);
    }
    throw Error("unclosed QML block");
}
function method(name) {
    const at=qml.indexOf("function "+name+"(");
    assert(at>=0,"missing "+name);
    return body(at);
}
const onSaved=body(qml.indexOf("        onSaved: {"));
const onSaveFailed=qml.slice(qml.indexOf("        onSaveFailed: function(error) {"),
                            qml.indexOf("    }\n    FileView {\n        id: legacyFile"));
const invoke=ctx=>vm.runInNewContext("(function(){"+onSaved+"})()",ctx,{timeout:1000});
function harness({pending={version:2,alarms:["old"]},
                  queued={version:2,alarms:["new"]},draining=true}={}) {
    const writes=[],events=[],later=[];
    const manager={pendingDocument:pending,queuedDocument:queued,
        storageState:"saving",storageError:"",feedback:"",
        migrationRequested:false,alarmWriterMaySave:true,
        beginWrite(doc) {
            if(writerDrain.draining && !writerDrain.acceptedFlushOnly)
                return false;
            this.pendingDocument=doc;this.storageState="saving";
            writerDrain.pendingGeneration=writerDrain.queuedGeneration;
            writes.push(doc);return true;
        },
        checkDue(){events.push("tick");},
        announceRestoredRinging(){events.push("announce");}
    };
    const writerDrain={phase:"ACTIVE",draining,
        acceptedFlushOnly:false,acceptingNewEdits:!draining,
        acceptedGeneration:2,observedSaveGeneration:0,
        pendingGeneration:1,queuedGeneration:queued?2:0,
        maybeComplete(){
            if(this.draining && policy.canFinish(ready({
                storageState:manager.storageState,
                pendingWrite:manager.pendingDocument!==null,
                queuedWrite:manager.queuedDocument!==null
            }),this.acceptedGeneration,this.observedSaveGeneration)){
                this.draining=false;this.phase="QUIESCING";
                events.push("local-drained");return true;
            }
            return false;
        },
        markFailed(){this.draining=false;this.phase="FAILED";
            this.acceptingNewEdits=false;this.acceptedFlushOnly=false;
            events.push("failed");}
    };
    return {manager,writerDrain,writes,events,later,
        context:{manager,writerDrain,Qt:{callLater:fn=>later.push(fn)}}};
}
test("starting a local drain permits pending accepted writes but not unsafe states",()=>{
    assert.equal(policy.canStart(ready()),true);
    assert.equal(policy.canStart(ready({
        storageState:"saving",pendingWrite:true,queuedWrite:true})),true);
    assert.equal(policy.canStart(ready({
        storageState:"saving",pendingWrite:true,migrationRequested:true})),true);
    for(const c of [{storageState:"loading"},{storageState:"error"},
        {storageState:"saving",pendingWrite:false},
        {queuedWrite:true,pendingWrite:false},
        {migrationRequested:true,pendingWrite:false},{ringingCount:1},
        {previewing:true},{audioState:"QT PLAYING"},
        {notificationOutcome:"DELIVERY PENDING"},{pendingWrite:0}])
        assert.equal(policy.canStart(ready(c)),false,JSON.stringify(c));
});
test("malformed snapshots and unacknowledged generations refuse local completion",()=>{
    for(const x of [null,undefined,[],{},3,"ACTIVE",
        ready({ringingCount:NaN}),ready({queuedWrite:0}),
        ready({notificationOutcome:""})])assert.equal(policy.canStart(x),false);
    assert.equal(policy.canFinish(ready(),0,0),true);
    for(const [a,b] of [[1,0],[3,2],[true,1],[-1,-1]])
        assert.equal(policy.canFinish(ready(),a,b),false);
    assert.equal(policy.canFinish(ready({pendingWrite:true}),2,2),false);
});
test("accepted queue flush requires private saved callback scope",()=>{
    for(const [phase,draining,admitting,callback,result] of [
        ["ACTIVE",true,false,true,true],["ACTIVE",true,false,false,false],
        ["ACTIVE",false,false,true,false],["ACTIVE",true,true,true,false],
        ["QUIESCING",true,false,true,false],["FAILED",true,false,true,false]])
        assert.equal(policy.queuedFlushAllowed(
            phase,draining,admitting,callback),result);
});
test("real onSaved handler flushes queued revision and only then quiesces locally",()=>{
    const h=harness();
    invoke(h.context);
    assert.deepEqual(h.writes,[{version:2,alarms:["new"]}]);
    assert.equal(h.writerDrain.acceptedFlushOnly,false);
    assert.equal(h.writerDrain.observedSaveGeneration,1);
    assert.equal(h.writerDrain.pendingGeneration,2);
    assert.equal(h.manager.storageState,"saving");
    assert.equal(h.writerDrain.draining,true);
    invoke(h.context);
    assert.equal(h.manager.storageState,"ready");
    assert.equal(h.writerDrain.observedSaveGeneration,2);
    assert.equal(h.writerDrain.phase,"QUIESCING");
    assert.equal(h.writerDrain.draining,false);
    assert.equal(h.writes.length,1);
});
test("direct beginWrite is rejected during frozen intake",()=>{
    const a=method("beginWrite"),b=method("saveDocument");
    assert.match(a,/if \(writerDrain\.draining && !writerDrain\.acceptedFlushOnly\)/);
    assert.match(b,/if \(!alarmWriterMaySave \|\| !canEdit \|\| !Policy\.validDocument\(next\)\)/);
    const h=harness();assert.equal(h.manager.beginWrite({forged:true}),false);
    assert.equal(h.writes.length,0);
});
test("identical queued content coalesces after actual onSaved callback",()=>{
    const same={version:2,alarms:["identical"]};
    const h=harness({pending:same,queued:same});invoke(h.context);
    assert.equal(h.writes.length,0);
    assert.equal(h.writerDrain.observedSaveGeneration,2);
    assert.equal(h.writerDrain.phase,"QUIESCING");
});
test("missing save callback cannot claim quiescence",()=>{
    const h=harness();assert.equal(h.writerDrain.phase,"ACTIVE");
    assert.equal(h.writerDrain.observedSaveGeneration,0);
    assert.equal(policy.canFinish(ready({
        storageState:"saving",pendingWrite:true,queuedWrite:true}),2,0),false);
});
test("queued callback refusal enters FAILED and reports non-durable status",()=>{
    const h=harness();h.manager.beginWrite=()=>false;invoke(h.context);
    assert.equal(h.writerDrain.phase,"FAILED");
    assert.equal(h.manager.storageState,"error");
    assert.equal(h.manager.storageError,"WRITER_DRAIN_QUEUE_REFUSED");
    assert.equal(h.writerDrain.acceptedFlushOnly,false);
});
test("FileView onSaveFailed contains fail-closed phase and save error",()=>{
    assert.match(onSaveFailed,/writerDrain\.markFailed\(\)/);
    assert.match(onSaveFailed,/manager\.storageState = "error"/);
    assert.match(onSaveFailed,/manager\.storageError = "V2_SAVE_FAILED"/);
    assert.match(method("markFailed"),/phase = WriterDrain\.FAILED/);
});
test("manager's public pause remains denied and internal drain unreachable",()=>{
    assert.match(qml,/import "AlarmWriterDrainPolicy.js" as WriterDrain/);
    assert.match(qml,/readonly property string alarmWriterBarrierPhase: "ACTIVE"/);
    assert.match(qml,/readonly property bool nativeWriterDrainBridgeInstalled: false/);
    assert.match(method("beginInternalSaveDrain"),
        /if \(!manager\.nativeWriterDrainBridgeInstalled/);
    assert.match(method("requestAlarmWriterPause"),
        /return WriterBarrier\.requestPause\(writerPauseSnapshot\(\)\)/);
    assert.doesNotMatch(method("requestAlarmWriterPause"),/beginInternalSaveDrain/);
    assert.doesNotMatch(qml,/on[A-Za-z]+:\s*writerDrain\.beginInternalSaveDrain/);
});
test("local onSaved witness never claims durable revision, release or ring",()=>{
    const h=harness();invoke(h.context);invoke(h.context);
    const status=plain(policy.status(h.writerDrain.phase,
        h.writerDrain.draining,ready(),2,2));
    assert.equal(status.localQueueDrained,true);
    for(const k of ["finalRevisionDurablyWitnessed","writerStopped",
        "releaseAcknowledged","canTransferOwnership","canRing"])
        assert.equal(status[k],false);
    assert(!JSON.stringify(status).includes("alarms"));
});
test("mounted scheduler/audio/edit gates and emergency local STOP are preserved",()=>{
    assert.match(qml,/allowSchedulerTick\(alarmWriterBarrierPhase\)\s*&& !writerDrain\.draining/);
    assert.match(qml,/allowRingAnnouncement\(alarmWriterBarrierPhase\)\s*&& !writerDrain\.draining/);
    assert.match(qml,/allowAudioStart\(alarmWriterBarrierPhase\)\s*&& !writerDrain\.draining/);
    assert.match(qml,/readonly property bool canEdit:\s*alarmWriterMaySave && !writerDrain\.draining/);
    for(const methodName of ["stopAlarm","stopAll","snoozeAlarm"])
        assert.match(method(methodName),/if \(!canEdit\)/);
    assert.match(qml,/readonly property bool writerReleaseAcknowledged: false/);
    assert.equal(qml.match(/alarmFile\.setText\(/g)?.length,1);
    assert.match(qml,/atomicWrites: true/);
    assert.match(qml,/blockWrites: false/);
});
