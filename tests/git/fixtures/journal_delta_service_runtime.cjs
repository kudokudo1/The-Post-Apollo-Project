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
    "markUndoResult","persist"
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
        deltaRecords:[],maxDeltaRecords:limit,
        lastPersistSerializationMs:0,lastPersistWriteMs:0,lastPersistReusedCount:0,
        operationStarted(id,record){events.push(["start",id,record.status]);},
        operationFinished(id,ok,record){events.push(["finish",id,ok,record.status]);},
        journalFile:{
            text(){return disk.main||"";},
            setText(content){disk.main=content;
                if(disk.failAfterBaseWrite){disk.failAfterBaseWrite=false;throw Error("SIMULATED_CRASH_AFTER_CHECKPOINT");}
            }
        },
        deltaFile:{
            text(){return disk.delta||"";},
            setText(content){disk.delta=content;}
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
assert.equal(disk.main,undefined);
assert.equal(JSON.parse(disk.delta).records[0].status,"RUNNING");
assert.equal(s.events.length,1);
assert.equal(s.call("completeOperation",id,snapshot(),"fetch done"),true);
assert.equal(JSON.parse(disk.delta).records[0].status,"COMPLETE");
assert.equal(s.events[1][2],true);
const cold=create(disk,false);
assert.equal(cold.scope.storageReady,true);
assert.equal(cold.scope.deltaActive,true,"pending sidecar must replay with flag off");
assert.equal(cold.scope.entries[0].status,"COMPLETE");
assert.equal(cold.scope.entries[0].id,id);
assert.equal(cold.scope.entries[0].detail,"fetch done");

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
let threw=false;
try {cp.call("beginOperation","CONTROL/PULL",snapshot(),meta());}
catch(e){threw=true;}
assert(threw,"must simulate a crash after durable base, before clear");
assert.equal(JSON.parse(cpDisk.main).checkpointGeneration,1);
assert.equal(JSON.parse(cpDisk.delta).baseGeneration,0);
const replay=create(cpDisk,false,2);
assert.equal(replay.scope.storageReady,true);
assert.equal(replay.scope.entries.length,2);
assert.equal(replay.scope.entries[0].kind,"CONTROL/PULL");
assert.equal(replay.scope.entries[1].id,first);
assert.equal(replay.scope.entries[0].status,"INTERRUPTED");
assert.equal(replay.scope.entries[1].status,"INTERRUPTED");

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
