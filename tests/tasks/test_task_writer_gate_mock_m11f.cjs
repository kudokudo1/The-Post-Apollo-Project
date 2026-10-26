#!/usr/bin/env node
"use strict";
// M11f accepts a MOCK handshake for review ONLY; no actual file/process API.
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const path="services/projects/TaskWriterGateMockM11f.js";
const source=fs.readFileSync(path,"utf8").replace(/^\.pragma library\s*$/m,"");
const ctx=vm.createContext({Date,JSON,Object,Number,String,Array,RegExp,Math});
vm.runInContext(source,ctx,{filename:path});
const synthetic=(rev)=>JSON.stringify({
    fixture:"M11E_SYNTHETIC_ONLY",revision:rev,counter:rev,marker:"sample"
})+"\n";
const evidence={
    writerId:"m11f-synthetic-writer-001",
    sessionId:"m11f-synthetic-session-002",
    epoch:7,sourceHash:"a".repeat(64),
    hostPhase:"JSON_ACTIVE",flockObserved:true,
    callbackQueueDrained:true,sourceStable:true,
    confirmedRaw:synthetic(0)
};
const frozenCopy=(x)=>JSON.stringify(x);
function noPower(result){
    assert.equal(result.mockOnly,true);
    assert.equal(result.productionWriteAuthorized,false);
    assert.equal(result.sqliteWriteAuthorized,false);
    assert.equal(result.migrationAuthorized,false);
    assert.equal(result.remoteWriteAuthorized,false);
}
function owner(){
    const initial=ctx.state(),before=frozenCopy(initial);
    assert.equal(initial.phase,"BOOT_LOCKED");
    assert.equal(ctx.eligible(initial),false);
    const opened=ctx.reviewMockOwner(initial,evidence);
    noPower(opened);
    assert.equal(opened.accepted,true);
    assert.equal(opened.state.phase,"MOCK_READY");
    assert.equal(opened.mockStageEligible,true);
    assert.equal(frozenCopy(initial),before);
    assert.equal(ctx.reviewMockOwner(opened.state,evidence).accepted,false);
    return opened.state;
}
function reserve(state, increment){
    const plan=ctx.proposeStage(state,synthetic(increment));
    noPower(plan);
    assert.equal(plan.accepted,true);
    assert.equal(plan.state.phase,"MOCK_RESERVING");
    assert.equal(plan.mockStageEligible,false);
    const receipt={
        kind:"reserve",writerId:evidence.writerId,
        sessionId:evidence.sessionId,epoch:evidence.epoch,
        stageId:plan.state.stageId,persisted:true,
        sourceHash:evidence.sourceHash
    };
    const reserved=ctx.acceptReservation(plan.state,receipt);
    noPower(reserved);
    assert.equal(reserved.accepted,true);
    assert.equal(reserved.state.phase,"MOCK_SAVING");
    assert.equal(ctx.proposeStage(reserved.state,synthetic(increment+1)).accepted,false);
    return {reserved:reserved.state,receipt,planned:plan.state};
}
function complete(s,number) {
    const saved=ctx.onSaved(s);
    noPower(saved);
    assert.equal(saved.state.phase,"MOCK_VERIFYING");
    assert.equal(saved.state.revision,number-1);
    assert.equal(ctx.proposeStage(saved.state,synthetic(number+1)).accepted,false);
    const read=ctx.verifyReadback(saved.state,synthetic(number));
    assert.equal(read.accepted,true);
    assert.equal(read.state.phase,"MOCK_SETTLING");
    const settled=ctx.acceptSettle(read.state,{
        kind:"settle",writerId:evidence.writerId,
        sessionId:evidence.sessionId,epoch:evidence.epoch,
        stageId:read.state.stageId,persisted:true,readbackMatched:true
    });
    noPower(settled);
    assert.equal(settled.accepted,true);
    assert.equal(settled.state.revision,number);
    assert.equal(settled.state.committed,number);
    assert.equal(settled.state.stageId,null);
    assert.equal(settled.state.stagedRaw,null);
    return settled.state;
}
let opened=owner(),first=reserve(opened,1);
let ready=complete(first.reserved,1);
assert.equal(ready.phase,"MOCK_READY");
assert.equal(ctx.eligible(ready),true);
let next=reserve(ready,2);
let completed=complete(next.reserved,2);
assert.equal(completed.phase,"MOCK_READY");
assert.equal(completed.committed,2);
assert.equal(completed.sequence,3);

for(const phase of ["MOCK_READY","MOCK_RESERVING","MOCK_SAVING",
                     "MOCK_VERIFYING","MOCK_SETTLING"]){
    let s=owner(),receipt=null;
    if(phase!=="MOCK_READY"){
        const entry=reserve(s,1);
        s=phase==="MOCK_RESERVING"?entry.planned:entry.reserved;
        receipt=entry.receipt;
        if(phase==="MOCK_VERIFYING" || phase==="MOCK_SETTLING"){
            s=ctx.onSaved(s).state;
            if(phase==="MOCK_SETTLING")s=ctx.verifyReadback(s,synthetic(1)).state;
        }
    }
    const freeze=ctx.requestFreeze(s);
    assert.equal(freeze.accepted,true,phase);
    noPower(freeze);
    assert.equal(ctx.eligible(freeze.state),false);
    assert.equal(ctx.proposeStage(freeze.state,synthetic(3)).accepted,false);
    if(phase==="MOCK_RESERVING"){
        const p=ctx.acceptReservation(freeze.state,receipt);
        assert.equal(p.state.phase,"MOCK_SAVING");
        s=complete(p.state,1);
    }else if(phase==="MOCK_SAVING"){
        s=complete(freeze.state,1);
    }else if(phase==="MOCK_VERIFYING"){
        const p=ctx.verifyReadback(freeze.state,synthetic(1));
        s=ctx.acceptSettle(p.state,{
            kind:"settle",writerId:evidence.writerId,
            sessionId:evidence.sessionId,epoch:evidence.epoch,
            stageId:p.state.stageId,persisted:true,readbackMatched:true
        }).state;
    }else if(phase==="MOCK_SETTLING"){
        s=ctx.acceptSettle(freeze.state,{
            kind:"settle",writerId:evidence.writerId,
            sessionId:evidence.sessionId,epoch:evidence.epoch,
            stageId:freeze.state.stageId,persisted:true,readbackMatched:true
        }).state;
    }else s=freeze.state;
    assert.equal(s.phase,"MOCK_FREEZING");
    assert.equal(ctx.acceptFreeze(s,{
        kind:"freeze",writerId:evidence.writerId,
        sessionId:evidence.sessionId,epoch:evidence.epoch,
        persisted:true,pendingStage:false,sourceHash:"b".repeat(64)
    }).state.phase,"MOCK_FROZEN");
    assert.equal(ctx.eligible(s),false);
}
function refusal(action,reason){
    const response=action();
    noPower(response);
    assert.equal(response.accepted,false);
    if(reason)assert.equal(response.reason,reason);
    return response.state;
}
for(const corrupt of [
    {...evidence,flockObserved:false},
    {...evidence,callbackQueueDrained:false},
    {...evidence,sourceStable:false},
    {...evidence,sourceHash:"bad"},
    {...evidence,epoch:-1},
    {...evidence,hostPhase:"SQLITE_ACTIVE"},
    {...evidence,confirmedRaw:"{}"},
    {...evidence,unexpected:true}
]){
    refusal(()=>ctx.reviewMockOwner(ctx.state(),corrupt));
}
refusal(()=>ctx.proposeStage(owner(),synthetic(7)),"INVALID_SYNTHETIC_INCREMENT");
refusal(()=>ctx.proposeStage(owner(),'{"version":3,"tasks":[]}'),
       "INVALID_SYNTHETIC_INCREMENT");
const sample=reserve(owner(),1);
for(const tamper of [
    {...sample.receipt,epoch:8},
    {...sample.receipt,stageId:"mock-stage-999"},
    {...sample.receipt,persisted:false},
    {...sample.receipt,sourceHash:"b".repeat(64)},
    {...sample.receipt,extra:true}
]) {
    const bad=refusal(()=>ctx.acceptReservation(sample.planned,tamper),
                      "STALE_OR_UNVERIFIED_RESERVATION");
    assert.equal(bad.phase,"RECOVERY_REVIEW");
    assert.equal(bad.revision,0);
}
let during=ctx.onSaved(sample.reserved).state;
refusal(()=>ctx.verifyReadback(during,synthetic(0)),"READBACK_NOT_MATCHED");
refusal(()=>ctx.verifyReadback(during,"malformed"),"READBACK_NOT_MATCHED");
let after=ctx.verifyReadback(during,synthetic(1)).state;
const goodSettle={
    kind:"settle",writerId:evidence.writerId,
    sessionId:evidence.sessionId,epoch:7,
    stageId:after.stageId,persisted:true,readbackMatched:true};
for(const altered of [
    {...goodSettle,epoch:6},
    {...goodSettle,stageId:"mock-stage-000"},
    {...goodSettle,persisted:false},
    {...goodSettle,readbackMatched:false},
    {...goodSettle,extra:true}
]){
    const failed=refusal(()=>ctx.acceptSettle(after,altered),
                         "STALE_OR_UNVERIFIED_SETTLE");
    assert.equal(failed.phase,"RECOVERY_REVIEW");
    assert.equal(failed.revision,0);
}
refusal(()=>ctx.onSaved(owner()),"UNEXPECTED_SAVE_CALLBACK");
refusal(()=>ctx.verifyReadback(owner(),synthetic(1)),"UNEXPECTED_READBACK");
refusal(()=>ctx.failedCallback(sample.reserved),"SAVE_OR_LOAD_FAILED");
refusal(()=>ctx.acceptSettle(sample.reserved,goodSettle),"NO_SETTLING_STAGE");
const wait=ctx.requestFreeze(owner()).state;
refusal(()=>ctx.acceptFreeze(wait,{
    kind:"freeze",writerId:evidence.writerId,
    sessionId:evidence.sessionId,epoch:7,
    persisted:false,pendingStage:false,sourceHash:"a".repeat(64)
}),"FREEZE_NOT_DURABLY_WITNESSED");
const restart=ctx.restart(owner());
refusal(()=>restart,"NEW_PROCESS_REQUIRES_REVIEW");
assert.equal(restart.state.phase,"RECOVERY_REVIEW");
assert.equal(ctx.eligible(restart.state),false);
refusal(()=>ctx.reviewMockOwner(restart.state,evidence),"NOT_BOOT_LOCKED");
assert.equal(ctx.restart(completed).state.phase,"RECOVERY_REVIEW");
assert.equal(ctx.restart(sample.reserved).state.phase,"RECOVERY_REVIEW");
console.log("M11f mock owner epoch, reservation, save/readback, settle, freeze and restart: PASS");
