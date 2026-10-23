"use strict";
// Execute GitOperationJournalService's actual JavaScript functions with
// disposable in-memory FileView doubles. This is NOT a Qt/Quickshell runtime.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("services/git/GitOperationJournalService.qml", "utf8");

function extract(name) {
    const at = source.indexOf("    function " + name + "(");
    assert(at >= 0, name + " missing");
    let start = source.indexOf("{", at);
    assert(start >= 0, name + " body missing");
    let depth = 0, quote = "", line = false, block = false;
    for (let i = start; i < source.length; i++) {
        const a = source[i], b = source[i+1];
        if (line) { if (a === "\n") line=false; continue; }
        if (block) { if (a==="*" && b==="/") {block=false;i++;} continue; }
        if (quote) {
            if (a==="\\") {i++;continue;}
            if (a===quote) quote="";
            continue;
        }
        if (a==="/" && b==="/") {line=true;i++;continue;}
        if (a==="/" && b==="*") {block=true;i++;continue;}
        if (a==='"' || a==="'") {quote=a;continue;}
        if (a==="{") depth++;
        if (a==="}" && --depth===0)
            return source.slice(at,i+1);
    }
    throw Error("No function close for "+name);
}
const names=[
    "nowIso","cloneValue","nextOperationId","entryIndex","beginOperation",
    "completedRecoveryClass","completeOperation","failOperation","load",
    "markUndoResult","blockStorage","requireWriteAck","markMutationProfile","persist"
];
const funcs=names.map(extract).join("\n");
const delta=fs.readFileSync("services/git/GitJournalDelta.js","utf8");
const journal=fs.readFileSync("services/git/GitJournalSerialization.js","utf8");

function create(disk, requested=true, limit=48) {
    const events = [];
    const context = {
        console, JSON, Date, String, Number, Boolean, Array, Object, Math,
        repositoryPath:"/synthetic/repo", schemaVersion:1,
        maxEntries:500, serial:0, entries:[], encodedEntries:[],
        deltaRequested:requested, deltaActive:false,
        storageReady:false, storageError:"", checkpointGeneration:0,
        journalWriteStatus:0, journalWriteError:"",
        deltaWriteStatus:0, deltaWriteError:"",
        deltaRecords:[],encodedDeltaRecords:[],maxDeltaRecords:limit,
        lastPersistSerializationMs:0,lastPersistWriteMs:0,lastPersistReusedCount:0,
        lastMutationProfile:{},
        operationStarted(id,record){events.push(["start",id,record.status]);},
        operationFinished(id,ok,record){events.push(["finish",id,ok,record.status]);},
        journalFile:{
            text(){return disk.main||"";},
            setText(content){
                if(disk.failBaseWrite){
                    disk.failBaseWrite=false;
                    context.journalWriteStatus=-1;
                    context.journalWriteError="SIMULATED_BASE_SAVE_FAILED";
                    return;
                }
                disk.main=content;
                context.journalWriteStatus=1;
                if(disk.failAfterBaseWrite){
                    disk.failAfterBaseWrite=false;
                    throw Error("SIMULATED_CRASH_AFTER_CHECKPOINT");
                }
            }
        },
        deltaFile:{
            text(){return disk.delta||"";},
            setText(content){
                const clearing=JSON.parse(content).records.length===0;
                if(disk.failDeltaWrite || (clearing && disk.failSidecarClear)){
                    disk.failDeltaWrite=false;
                    disk.failSidecarClear=false;
                    context.deltaWriteStatus=-1;
                    context.deltaWriteError="SIMULATED_DELTA_SAVE_FAILED";
                    return;
                }
                disk.delta=content;
                context.deltaWriteStatus=1;
            }
        }
    };
    context.DeltaCodec=vm.createContext({});
    vm.runInContext(delta,context.DeltaCodec);
    context.JournalCodec=vm.createContext({});
    vm.runInContext(journal,context.JournalCodec);
    const scope=vm.createContext(context);
    vm.runInContext(funcs,scope);
    vm.runInContext("load()",scope);
    return {scope,events,call(name,...args){return scope[name](...args)}};
}
function snapshot(){return {recoveryClass:"EVIDENCE_ONLY",refs:[{sha:"a123"}]};}
function meta(){return {target:"origin/main",source:"CONTROL"};}
function state(record){return JSON.parse(JSON.stringify(record));}

// Missing-file startup; small durable writes stay off the legacy checkpoint.
const disk={};
const s=create(disk,true);
assert.equal(s.scope.storageReady,true);
assert.equal(s.scope.deltaActive,true);
const id=s.call("beginOperation","CONTROL/FETCH",snapshot(),meta());
assert(id);
assert.equal(s.scope.lastMutationProfile.stage,"BEGIN");
assert(s.scope.lastMutationProfile.totalMs>=0);
assert.equal(s.scope.lastMutationProfile.totalMs,
    s.scope.lastMutationProfile.recordMs
    +s.scope.lastMutationProfile.entriesMs
    +s.scope.lastMutationProfile.persistMs
    +s.scope.lastMutationProfile.notifyMs);
assert.equal(disk.main,undefined);
assert.equal(JSON.parse(disk.delta).records[0].status,"RUNNING");
assert.equal(s.events.length,1);
assert.equal(s.call("completeOperation",id,snapshot(),"fetch done"),true);
assert.equal(s.scope.lastMutationProfile.stage,"COMPLETE");
assert.equal(JSON.parse(disk.delta).records[0].status,"COMPLETE");
assert.equal(s.events[1][2],true);
const cold=create(disk,false);
assert.equal(cold.scope.storageReady,true);
assert.equal(cold.scope.deltaActive,true,"pending sidecar must replay with flag off");
assert.equal(cold.scope.entries[0].status,"COMPLETE");
assert.equal(cold.scope.entries[0].id,id);
assert.equal(cold.scope.entries[0].detail,"fetch done");

// The real extracted service must reuse only unchanged committed rows.
const cacheDisk={};
const cached=create(cacheDisk,true);
const one=cached.call("beginOperation","CONTROL/FETCH",snapshot(),meta());
assert(one);
assert.equal(cached.scope.lastPersistReusedCount,0);
const two=cached.call("beginOperation","CONTROL/PULL",snapshot(),meta());
assert(two);
assert.equal(cached.scope.lastPersistReusedCount,1);
assert.equal(cached.scope.encodedDeltaRecords.length,2);
assert.equal(cached.call("completeOperation",two,snapshot(),"pull done"),true);
assert.equal(cached.scope.lastPersistReusedCount,1);
assert.equal(JSON.parse(cacheDisk.delta).records[1].status,"COMPLETE");
assert.equal(cached.call("completeOperation",one,snapshot(),"fetch done"),true);
assert.equal(cached.scope.lastPersistReusedCount,1);
const cacheReload=create(cacheDisk,true);
assert.equal(cacheReload.scope.encodedDeltaRecords.length,0,
    "cache must not be trusted across cold journal loads");
const three=cacheReload.call("beginOperation","CONTROL/FETCH",snapshot(),meta());
assert(three);
assert.equal(cacheReload.scope.lastPersistReusedCount,0);
assert.equal(JSON.parse(cacheDisk.delta).records.length,3);
assert.equal(JSON.parse(cacheDisk.delta).records[0].status,"COMPLETE");

const checkpointDisk={};
const checkpoint=create(checkpointDisk,true,2);
assert(checkpoint.call("beginOperation","CONTROL/FETCH",snapshot(),meta()));
assert.equal(checkpoint.scope.encodedDeltaRecords.length,1);
assert(checkpoint.call("beginOperation","CONTROL/PULL",snapshot(),meta()));
assert.equal(checkpoint.scope.encodedDeltaRecords.length,0,
    "successful full checkpoint invalidates sidecar cache");
assert.equal(JSON.parse(checkpointDisk.main).entries.length,2);
assert.equal(JSON.parse(checkpointDisk.delta).records.length,0);

// A real crash after RUNNING receipt must not invent a COMPLETE result.
const interruptedDisk={};
const before=create(interruptedDisk,true);
const interruptedId=before.call("beginOperation","CONTROL/PULL",snapshot(),meta());
const after=create(interruptedDisk,true);
assert.equal(after.scope.entries[0].id,interruptedId);
assert.equal(after.scope.entries[0].status,"INTERRUPTED");
assert.equal(after.scope.entries[0].recoveryClass,"EVIDENCE_ONLY");
assert.equal(JSON.parse(interruptedDisk.main).entries[0].status,"INTERRUPTED");

// Existing legacy journal, optional Undo fields and opt-out behavior.
const legacy={main: JSON.stringify({schemaVersion:1,entries:[{
    schemaVersion:1,id:"legacy",repository:"/synthetic/repo",
    kind:"CONTROL/PULL",status:"COMPLETE",before:snapshot(),
    after:snapshot(),metadata:meta(),undoState:"UNDONE",
    undoOperationId:"undo-1",undoDetail:"restored",undoneAt:"yesterday",
    recoveryClass:"EVIDENCE_ONLY"
}]})};
const baseline=create(legacy,false);
assert.equal(baseline.scope.deltaActive,false);
assert.equal(baseline.scope.entries[0].undoOperationId,"undo-1");
assert.equal(baseline.scope.entries[0].undoDetail,"restored");
const another=baseline.call("beginOperation","CONTROL/FETCH",snapshot(),meta());
assert(another);
assert.equal(legacy.delta,undefined);
assert.equal(JSON.parse(legacy.main).entries.length,2);
assert.equal(JSON.parse(legacy.main).entries[1].undoOperationId,"undo-1");

// Delta checkpoint and fault injection during the two-file window.
const cpDisk={};
const cp=create(cpDisk,true,2);
let first=cp.call("beginOperation","CONTROL/FETCH",snapshot(),meta());
assert(first);
cpDisk.failAfterBaseWrite=true;
assert.equal(cp.call("beginOperation","CONTROL/PULL",snapshot(),meta()),"");
assert.equal(cp.scope.storageReady,false,"uncertain checkpoint acknowledgement blocks writes");
assert.match(cp.scope.storageError,/SIMULATED_CRASH_AFTER_CHECKPOINT/);
assert.equal(JSON.parse(cpDisk.main).checkpointGeneration,1);
assert.equal(JSON.parse(cpDisk.delta).baseGeneration,0);
const replay=create(cpDisk,false,2);
assert.equal(replay.scope.storageReady,true);
assert.equal(replay.scope.entries.length,2);
assert.equal(replay.scope.entries[0].kind,"CONTROL/PULL");
assert.equal(replay.scope.entries[1].id,first);
assert.equal(replay.scope.entries[0].status,"INTERRUPTED");
assert.equal(replay.scope.entries[1].status,"INTERRUPTED");

// A failed BEFORE write must not launch Git or emit operationStarted.
const deniedDisk={};
const denied=create(deniedDisk,true);
deniedDisk.failDeltaWrite=true;
assert.equal(denied.call("beginOperation","CONTROL/FETCH",snapshot(),meta()),"");
assert.equal(denied.scope.storageReady,false);
assert.equal(denied.scope.lastMutationProfile.stage,"BEGIN_FAILED");
assert.equal(denied.events.length,0);
assert.equal(deniedDisk.delta,undefined);
assert.match(denied.scope.storageError,/DELTA WRITE FAILED/);
assert.equal(denied.call("beginOperation","CONTROL/FETCH",snapshot(),meta()),"");

// Successful Git execution does not make a failed AFTER save successful.
const afterDisk={};
const afterService=create(afterDisk,true);
const afterId=afterService.call("beginOperation","CONTROL/PULL",snapshot(),meta());
assert(afterId);
afterDisk.failDeltaWrite=true;
assert.equal(afterService.call("completeOperation",afterId,snapshot(),"git succeeded"),false);
assert.equal(afterService.scope.lastMutationProfile.stage,"COMPLETE_FAILED");
assert.equal(afterService.events.length,1,"no false operationFinished on failed save");
assert.equal(afterService.scope.storageReady,false);
assert.equal(JSON.parse(afterDisk.delta).records[0].status,"RUNNING");
assert.equal(create(afterDisk,true).scope.entries[0].status,"INTERRUPTED");

// Default full-checkpoint mode must also honor failed save acknowledgements.
const legacyWriteFailure={};
const oldWriter=create(legacyWriteFailure,false);
legacyWriteFailure.failBaseWrite=true;
assert.equal(oldWriter.call("beginOperation","CONTROL/FETCH",snapshot(),meta()),"");
assert.equal(oldWriter.scope.storageReady,false);
assert.equal(oldWriter.events.length,0);
assert.equal(legacyWriteFailure.main,undefined);

// Failing to clear the sidecar after a committed checkpoint is uncertain;
// block writes and recover the already-committed generation after restart.
const clearDisk={};
const clearing=create(clearDisk,true,2);
const clearId=clearing.call("beginOperation","CONTROL/FETCH",snapshot(),meta());
assert(clearId);
clearDisk.failSidecarClear=true;
assert.equal(clearing.call("beginOperation","CONTROL/PULL",snapshot(),meta()),"");
assert.equal(clearing.scope.storageReady,false);
assert.match(clearing.scope.storageError,/DELTA WRITE FAILED/);
assert.equal(JSON.parse(clearDisk.main).checkpointGeneration,1);
assert.equal(JSON.parse(clearDisk.delta).baseGeneration,0);
const clearReload=create(clearDisk,false,2);
assert.equal(clearReload.scope.storageReady,true);
assert.equal(clearReload.scope.entries.length,2);
assert.equal(clearReload.scope.entries[0].kind,"CONTROL/PULL");

// Corrupt or incompatible storage must never admit a new operation.
for(const storage of [
    {main:"{invalid"},
    {delta:"{broken"},
    {main:JSON.stringify({schemaVersion:1,entries:[]}),
     delta:JSON.stringify({deltaVersion:1,baseGeneration:9,records:[]})}
]) {
    const invalid=create(storage,true);
    assert.equal(invalid.scope.storageReady,false);
    assert.match(invalid.scope.storageError,/JOURNAL STORAGE BLOCKED/);
    assert.equal(invalid.call("beginOperation","CONTROL/FETCH",snapshot(),meta()),"");
}
console.log("Git journal service extracted-JS replay and crash windows: PASS");
