#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const source=fs.readFileSync("services/projects/OfflineOperationJournal.js","utf8")
    .replace(/^\.pragma library\s*$/m,"");
const env=vm.createContext({JSON,Array,Object,Number,String,RegExp});
vm.runInContext(source,env,{filename:"OfflineOperationJournal.js"});

const normal={id:"p1",name:"Personal",family:"normal"};
const git={id:"p2",name:"Remote Work",family:"git"};
function task(id,projectId,title) {
    return {id,projectId,title,done:false,priority:"none",
        description:"",dueDate:null};
}
const original=env.create([normal,git],[task("t1","p1","Read"),task("t2","p2","Fix Bug")]);
assert.equal(original.ok,true);
assert.equal(original.document.version,1);
assert.equal(original.document.revision,0);
assert.equal(original.document.operations.length,0);
const before=JSON.stringify(original.document);

// NORMAL edit: no remote queue whatsoever.
const local=env.localEdit(original.document,
    {taskId:"t1",field:"title",value:"Read today"});
assert.equal(local.ok,true);
assert.equal(local.remoteIntentCreated,false);
assert.equal(local.document.tasks[0].title,"Read today");
assert.equal(local.document.operations.length,0);
assert.equal(local.document.revision,1);
assert.equal(JSON.stringify(original.document),before,"never mutate input");

// GIT edit: local data and pending intent returned as one versioned envelope.
const queued=env.localEdit(local.document,
    {taskId:"t2",field:"title",value:"Fix quickly",operationId:"op1"});
assert.equal(queued.ok,true);
assert.equal(queued.remoteIntentCreated,true);
assert.equal(queued.document.tasks[1].title,"Fix quickly");
assert.equal(queued.document.operations.length,1);
assert.equal(queued.document.operations[0].state,"PENDING");
assert.equal(queued.document.operations[0].before,"Fix Bug");
assert.equal(queued.document.operations[0].after,"Fix quickly");
assert.equal(queued.document.operations[0].createdRevision,2);
assert.equal(local.document.operations.length,0);

// Simulated save/restart: one serialized envelope carries BOTH data and intent.
const serialized=env.encode(queued.document);
assert.equal(serialized.ok,true);
const reloaded=env.decode(serialized.raw);
assert.equal(reloaded.ok,true);
assert.equal(reloaded.document.tasks[1].title,"Fix quickly");
assert.equal(reloaded.document.operations[0].state,"PENDING");
assert.equal(reloaded.document.operations[0].id,"op1");
assert.equal(env.recover(reloaded.document).uncertainCount,0);

// Out-of-order, duplicate, malformed and no-op changes never alter input.
const next=env.localEdit(reloaded.document,
    {taskId:"t2",field:"priority",value:"high",operationId:"op2"});
assert.equal(next.ok,true);
assert.equal(next.document.operations.length,2);
assert.equal(env.nextIntent(next.document).id,"op1");
assert.equal(env.transition(next.document,"op2","begin").ok,false);
assert.equal(env.localEdit(next.document,
    {taskId:"t2",field:"done",value:true,operationId:"op1"}).reason,
    "DUPLICATE_OPERATION_ID");
assert.equal(env.localEdit(next.document,
    {taskId:"t2",field:"priority",value:"high",operationId:"op3"}).reason,
    "NO_CHANGE");
assert.equal(env.localEdit(next.document,
    {taskId:"t2",field:"dueDate",value:"2026-02-29",operationId:"op3"}).ok,false);
assert.equal(env.localEdit(next.document,
    {taskId:"t2",field:"description",value:"x".repeat(2001),operationId:"op3"}).ok,false);
assert.equal(env.localEdit(next.document,
    {taskId:"t9",field:"done",value:true,operationId:"op3"}).reason,"UNKNOWN_TASK");

// A persisted SENDING operation after restart becomes UNCERTAIN and blocks
// any later queued op. Do not blind-retry non-idempotent remote actions.
const begun=env.transition(next.document,"op1","begin");
assert.equal(begun.ok,true);
assert.equal(begun.document.operations[0].state,"SENDING");
assert.equal(env.nextIntent(begun.document).reason,"SENDING_BLOCKED");
const written=env.encode(begun.document);
const returned=env.recover(env.decode(written.raw).document);
assert.equal(returned.ok,true);
assert.equal(returned.uncertainCount,1);
assert.equal(returned.document.operations[0].state,"UNCERTAIN");
assert.equal(returned.document.operations[1].state,"PENDING");
assert.equal(env.nextIntent(returned.document).reason,"UNCERTAIN_BLOCKED");
assert.equal(env.nextIntent(returned.document).id,"op1");
assert.equal(env.transition(returned.document,"op1","begin").ok,false);
assert.equal(JSON.stringify(begun.document.operations[0].state),'"SENDING"',
             "recovery never alters committed input");
assert.equal(env.recover(returned.document).uncertainCount,0,
             "recovery is stable after uncertain state");
assert.equal(env.transition(returned.document,"op1","acknowledge",null).ok,false);

// Only an external verified result may legitimately provide the receipt
// value. The pure policy tests shape, not whether GitHub really confirmed it.
const ack=env.transition(returned.document,"op1","acknowledge","observed-id-and-field-1");
assert.equal(ack.ok,true);
assert.equal(ack.document.operations[0].state,"ACKNOWLEDGED");
assert.equal(ack.document.operations[0].ackToken,"observed-id-and-field-1");
assert.equal(env.nextIntent(ack.document).id,"op2");
const begun2=env.transition(ack.document,"op2","begin");
assert.equal(begun2.ok,true);
const conflict=env.transition(begun2.document,"op2","conflict");
assert.equal(conflict.ok,true);
assert.equal(env.nextIntent(conflict.document).reason,"CONFLICT_BLOCKED");
assert.equal(env.transition(conflict.document,"op2","begin").ok,false);

// Corrupted or unknown future envelopes fail closed without silently emptying.
for(const input of [
    "",
    "{oops",
    JSON.stringify({...queued.document,version:2}),
    JSON.stringify({...queued.document,tasks:[]}),
    JSON.stringify({...queued.document,operations:[
        {...queued.document.operations[0],state:"ACKNOWLEDGED",ackToken:null}]}),
    JSON.stringify({...queued.document,operations:[
        {...queued.document.operations[0],projectId:"p1"}]}),
    JSON.stringify({...queued.document,operations:[
        {...queued.document.operations[0],createdRevision:2000}]}),
]) {
    assert.equal(env.decode(input).ok,false,input.slice(0,50));
}
assert.equal(env.decode(JSON.stringify({...queued.document,version:2})).reason,
             "UNSUPPORTED_ENVELOPE_VERSION");
assert.equal(env.decode("x".repeat(1048577)).ok,false);
const orphan=env.create([normal],[task("t2","p2","Lost")]);
assert.equal(orphan.ok,false);
const duplicate=env.create([normal,normal],[task("t1","p1","Hi")]);
assert.equal(duplicate.ok,false);

// Journal capacity must fail closed rather than drop queued edits.
const full=JSON.parse(JSON.stringify(next.document));
full.operations=Array.from({length:1001},(_,i)=>({
    id:"op"+(i+1),taskId:"t2",projectId:"p2",field:"title",
    before:"a",after:"b",createdRevision:i+1,
    state:"PENDING",ackToken:null
}));
full.revision=1001;
assert.equal(env.verify(full).reason,"INVALID_OPERATION_LIST");

for (const forbidden of [
    "FileView {","Process {","XMLHttpRequest","XmlHttpRequest",
    "Quickshell.execDetached","setText(","gh project ",
    "ApolloHubTodoStore {","GitHubProjectsService {","localStorage",
    "require(","fetch("
]) assert.ok(!source.includes(forbidden),"forbidden effect: "+forbidden);

console.log("TASKS M10b offline atomic-envelope journal, restart and uncertain retry: PASS");
