#!/usr/bin/env node
"use strict";
// Proxy 1 M10g: synthetic read-only integration contracts only.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
function load(name) {
    const content=fs.readFileSync(name,"utf8")
        .replace(/^\.pragma library\s*$/m,"");
    const ctx=vm.createContext({Date,Math,Array,Object,Number,String,RegExp,JSON});
    vm.runInContext(content,ctx,{filename:name});
    return {ctx,content};
}
const bridge=load("services/projects/UnifiedStorageReadBridge.js");
const old=load("services/hub/ApolloHubTodoPolicy.js").ctx;
const journal=load("services/projects/OfflineOperationJournal.js").ctx;
const migrate=load("services/projects/LegacyMigrationDryRun.js").ctx;
const today=load("widgets/tasks/TaskTodayPolicy.js").ctx;
const planner=load("widgets/tasks/TaskPlannerPolicy.js").ctx;

const now=1771521000000;
const v3={
    version:3,nextId:46,nextProjectId:5,
    projects:[
        {id:"p1",name:"Personal",createdAtMs:now,updatedAtMs:now+20},
        {id:"p4",name:"Development",createdAtMs:now+12,updatedAtMs:now+50}
    ],
    tasks:[
        {id:"t11",projectId:"p1",title:"Read",done:false,
         createdAtMs:now,updatedAtMs:now+150,priority:"low",
         description:"Local only",dueDate:"2026-10-23"},
        {id:"t45",projectId:"p4",title:"Deploy",done:false,
         createdAtMs:now+40,updatedAtMs:now+120,priority:"urgent",
         description:"A real description",dueDate:"2026-10-24"}
    ]
};
const dry=migrate.plan(JSON.stringify(v3),old,journal);
assert.equal(dry.ok,true,dry.reason);
const fromMigration=bridge.ctx.preview(dry.candidate,journal,old);
assert.equal(fromMigration.ok,true,fromMigration.reason);
assert.equal(fromMigration.writeReady,false);
assert.equal(fromMigration.snapshot.writable,false);
assert.equal(fromMigration.snapshot.state,"ready");
assert.equal(fromMigration.snapshot.total,2);
assert.equal(fromMigration.snapshot.projects.length,2);
assert.equal(fromMigration.snapshot.items[0].id,"t11");
assert.equal(fromMigration.snapshot.items[1].projectId,"p4");
assert.equal(fromMigration.snapshot.items[1].description,"A real description");
assert.equal(fromMigration.queuedOperations,0);
assert.equal(JSON.stringify(fromMigration.compatibilityDocument),
             JSON.stringify(dry.compatibilityV3));
assert.equal(fromMigration.compatibilityDocument.nextId,46);
assert.equal(fromMigration.compatibilityDocument.nextProjectId,5);
assert.equal(fromMigration.compatibilityDocument.tasks[0].createdAtMs,now);
assert.equal(fromMigration.candidateRevision,0);

// Downstream TODAY and PLANNER policy compatibility with the exact same
// read-only snapshot, including date and project relationships.
const daily=today.view(fromMigration.snapshot,"2026-10-23");
assert.equal(daily.available,true);
assert.equal(daily.dueToday,1);
assert.equal(daily.upcoming,1);
const month=planner.view(fromMigration.snapshot,
    "2026-10-01","2026-10-23","2026-10-23");
assert.equal(month.available,true);
assert.equal(month.agenda.length,1);
assert.equal(month.agenda[0].id,"t11");
assert.equal(month.agenda[0].projectId,"p1");
assert.equal(planner.weekDays(fromMigration.snapshot,
    "2026-10-23","2026-10-23").length,7);

// A linked GIT project may have local extensions in a future envelope.
// Read projection must not mutate/serialize-away any of those extensions.
// This does NOT verify remote identity or authorize remote writes.
const git=JSON.parse(JSON.stringify(dry.candidate));
git.projects[1].family="git";
git.projects[1].remote={
    provider:"github",owner:"kudokudo1",
    projectNodeId:"PVT_not_verified",projectNumber:15
};
git.projects[1].localExtensions={budget:{cap:9000},color:"yellow"};
git.tasks[1].localExtensions={links:["note-1"]};
git.revision=1;
git.operations.push({
    id:"op1",taskId:"t45",projectId:"p4",
    field:"title",before:"Old Deploy",after:"Deploy",
    createdRevision:1,state:"PENDING",ackToken:null
});
const original=JSON.stringify(git);
const linked=bridge.ctx.preview(git,journal,old);
assert.equal(linked.ok,true,linked.reason);
assert.equal(linked.snapshot.writable,false);
assert.equal(linked.snapshot.projects[1].name,"Development");
assert.equal(linked.queuedOperations,1);
assert.equal(linked.snapshot.items[1].id,"t45");
assert.equal(linked.compatibilityDocument.projects[1].family,undefined);
assert.equal(linked.compatibilityDocument.tasks[1].localExtensions,undefined);
assert.equal(JSON.stringify(git),original,"must not mutate underlying full model");
assert.equal(git.projects[1].localExtensions.budget.cap,9000);
assert.equal(git.tasks[1].localExtensions.links[0],"note-1");
const wouldWriteV3=old.validate(linked.compatibilityDocument);
assert.equal(wouldWriteV3.ok,true,
    "projection is v3 shaped, but must NEVER be written back");

// Conflicted/uncertain queued changes cannot disable reading but must not
// make the existing UI appear writable.
const ambiguous=JSON.parse(original);
ambiguous.operations[0].state="UNCERTAIN";
const afterUncertain=bridge.ctx.preview(ambiguous,journal,old);
assert.equal(afterUncertain.ok,true);
assert.equal(afterUncertain.queuedOperations,1);
assert.equal(afterUncertain.snapshot.writable,false);

// Missing metadata, invalid task references and malformed newer documents
// fail closed before any consumer sees a fabricated empty/saved snapshot.
for(const modify of [
  e=>{delete e.nextId;},
  e=>{e.nextProjectId=0;},
  e=>{delete e.tasks[0].createdAtMs;},
  e=>{delete e.tasks[1].priority;},
  e=>{e.tasks[0].projectId="p999";},
  e=>{e.projects[0].updatedAtMs=-10;},
  e=>{e.projects[1].name="Personal";},
  e=>{e.version=999;},
  e=>{e.tasks[1].dueDate="2026-02-29";},
  e=>{e.operations.push({...e.operations[0]});}
]) {
    const e=JSON.parse(original);
    modify(e);
    const r=bridge.ctx.preview(e,journal,old);
    assert.equal(r.ok,false,JSON.stringify(e).slice(0,100));
    assert.equal(r.writeReady,false);
}
assert.equal(bridge.ctx.preview(null,journal,old).ok,false);
assert.equal(bridge.ctx.preview(git,null,old).ok,false);
assert.equal(bridge.ctx.preview(git,journal,null).ok,false);

// A checklist is not authority. Even if all self-reported gates are true,
// the pure policy NEVER authorizes a writer or mutates any data.
const missing=bridge.ctx.cutoverReview(null);
assert.equal(missing.reviewReady,false);
assert.equal(missing.activate,false);
assert.equal(missing.writeReady,false);
assert.ok(missing.blockedBy.length>=8);
const incomplete=bridge.ctx.cutoverReview({
    originalByteBackupVerified:true,
    originalSourceFrozen:true
});
assert.equal(incomplete.reviewReady,false);
assert.ok(incomplete.blockedBy.includes("legacyWriterQuiesced"));
const selfAsserted=Object.fromEntries(Array.from(bridge.ctx.REQUIRED_GATES)
    .map(k=>[k,true]));
const review=bridge.ctx.cutoverReview(selfAsserted);
assert.equal(review.reviewReady,true);
assert.equal(review.reason,"EXTERNAL_ACTIVATION_REQUIRED");
assert.equal(review.writeReady,false);
assert.equal(review.activate,false);
for(const falseValue of [false,0,"true",null,undefined]) {
    const evidence={...selfAsserted,operatorCutoverApproved:falseValue};
    assert.equal(bridge.ctx.cutoverReview(evidence).reviewReady,false);
}
for(const forbidden of [
    "FileView {","Process {","setText(","localStorage",
    "Quickshell.execDetached(","XMLHttpRequest","gh project ",
    "GitHubProjectsService {","ApolloHubTodoStore {","require(","fetch("
]) assert.ok(!bridge.content.includes(forbidden),
               "read-only policy side effect: "+forbidden);
console.log("TASKS M10g read-only compatibility bridge and cutover gates: PASS");
