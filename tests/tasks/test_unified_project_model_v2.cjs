#!/usr/bin/env node
"use strict";
// M10h: policy-only synthetic tests. No local Quickshell or GitHub access.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
function policy(p) {
    const source=fs.readFileSync(p,"utf8").replace(/^\.pragma library\s*$/m,"");
    const ctx=vm.createContext({JSON,Object,Array,Number,String,RegExp,Date,Math});
    vm.runInContext(source,ctx,{filename:p});
    return {ctx,source};
}
const v2=policy("services/projects/UnifiedProjectModelV2.js");
const m=v2.ctx;
const oldJournal=policy("services/projects/OfflineOperationJournal.js").ctx;
const legacy=policy("services/hub/ApolloHubTodoPolicy.js").ctx;
const migrate=policy("services/projects/LegacyMigrationDryRun.js").ctx;
const bridge=policy("services/projects/UnifiedStorageReadBridge.js").ctx;
const planner=policy("widgets/tasks/TaskPlannerPolicy.js").ctx;
const today=policy("widgets/tasks/TaskTodayPolicy.js").ctx;
const now=1771521000000;
const v3={version:3,nextId:21,nextProjectId:3,
    projects:[{id:"p1",name:"Home",createdAtMs:now,updatedAtMs:now},
              {id:"p2",name:"Research",createdAtMs:now,updatedAtMs:now}],
    tasks:[{id:"t20",title:"Study",done:false,createdAtMs:now,
        updatedAtMs:now,priority:"none",description:"Original notes",
        dueDate:"2026-10-23",projectId:"p2"}]};
const legacyPlan=migrate.plan(JSON.stringify(v3),legacy,oldJournal);
assert.equal(legacyPlan.ok,true,legacyPlan.reason);
const upgraded=m.upgradeBaselineV1(legacyPlan.candidate,oldJournal);
assert.equal(upgraded.ok,true,upgraded.reason);
let data=upgraded.document;
assert.equal(data.version,2);
assert.equal(data.nextId,21);
assert.equal(data.nextProjectId,3);
assert.equal(data.nextOperationId,1);
assert.equal(data.projects[0].family,"normal");
assert.equal(data.projects[0].remote,null);
assert.equal(data.tasks[0].values && Object.keys(data.tasks[0].values).length,0);
assert.equal(data.tasks[0].createdAtMs,now);
assert.equal(m.verify(data).ok,true);
assert.equal(m.verify(m.empty()).ok,true);
assert.equal(m.upgradeBaselineV1({...legacyPlan.candidate,revision:1},oldJournal).ok,false);
assert.equal(m.upgradeBaselineV1({...legacyPlan.candidate,extra:"lost"},oldJournal).ok,false);
const ref=JSON.stringify(data);

// NORMAL edit updates timestamp without creating a remote journal op.
const title=m.editTask(data,{
    taskId:"t20",field:"title",value:"Study carefully",nowMs:now+10});
assert.equal(title.ok,true,title.reason);
assert.equal(title.remoteIntentCreated,false);
assert.equal(title.remoteWriteAuthorized,false);
assert.equal(title.document.tasks[0].updatedAtMs,now+10);
assert.equal(title.document.tasks[0].createdAtMs,now);
assert.equal(title.document.revision,1);
assert.equal(title.document.operations.length,0);
assert.equal(JSON.stringify(data),ref,"source envelope is immutable");
assert.equal(m.editTask(title.document,{
    taskId:"t20",field:"done",value:true,nowMs:now+9}).reason,"STALE_EDIT_TIME");
assert.equal(m.editTask(title.document,{
    taskId:"t20",field:"title",value:"Study carefully",nowMs:now+10}).reason,"NO_CHANGE");
// Same-millisecond edit uses the next logical millisecond for monotonicity.
const done=m.editTask(title.document,{
    taskId:"t20",field:"done",value:true,nowMs:now+10});
assert.equal(done.ok,true);
assert.equal(done.document.tasks[0].updatedAtMs,now+11);
assert.equal(done.document.tasks[0].done,true);
assert.equal(done.document.tasks[0].createdAtMs,now);

// Project rename records its own update time, and GIT rename remains blocked.
const ren=m.renameProject(done.document,{
    projectId:"p1",name:"Household",nowMs:now+5});
assert.equal(ren.ok,true,ren.reason);
assert.equal(ren.document.projects[0].updatedAtMs,now+5);
assert.equal(ren.document.projects[1].name,"Research");
assert.equal(m.renameProject(ren.document,{
    projectId:"p2",name:"Household",nowMs:now+10}).reason,"DUPLICATE_PROJECT_NAME");

// LOCAL typed fields work on NORMAL and GIT projects without remote intents.
const createField=m.addLocalField(ren.document,{
    projectId:"p2",label:"Budget",kind:"number",nowMs:now+30});
assert.equal(createField.ok,true,createField.reason);
assert.equal(createField.fieldId,"f1");
assert.equal(createField.document.projects[1].fields[0].scope,"local");
assert.equal(createField.remoteIntentCreated,false);
const budget=m.editCustomValue(createField.document,{
    taskId:"t20",fieldId:"f1",value:1250.75,nowMs:now+20});
assert.equal(budget.ok,true,budget.reason);
assert.equal(budget.document.tasks[0].values.f1,1250.75);
assert.equal(budget.document.tasks[0].updatedAtMs,now+20);
assert.equal(budget.document.operations.length,0);
assert.equal(m.editCustomValue(budget.document,{
    taskId:"t20",fieldId:"f1",value:"not a number",nowMs:now+25}).ok,false);
assert.equal(m.editCustomValue(budget.document,{
    taskId:"t20",fieldId:"f99",value:1,nowMs:now+25}).reason,"UNKNOWN_CUSTOM_FIELD");
assert.equal(m.addLocalField(createField.document,{
    projectId:"p2",label:"budget",kind:"text",nowMs:now+31}).reason,
    "DUPLICATE_FIELD_LABEL");

// Explicitly shaped GitHub references are NOT remote verification.
const linked=JSON.parse(JSON.stringify(budget.document));
linked.projects[1].family="git";
linked.projects[1].remote={provider:"github",owner:"kudokudo1",
    projectNodeId:"PVT_candidate_only",projectNumber:12};
linked.tasks[0].remote={projectItemNodeId:"PVTI_candidate_only",
    contentKind:"ISSUE",contentNodeId:"I_candidate_only"};
assert.equal(m.verify(linked).ok,true);
const linkedBefore=JSON.stringify(linked);
const edit=m.editTask(linked,{
    taskId:"t20",field:"priority",value:"high",nowMs:now+21});
assert.equal(edit.ok,true,edit.reason);
assert.equal(edit.remoteIntentCreated,true);
assert.equal(edit.remoteWriteAuthorized,false);
assert.equal(edit.document.operations.length,1);
assert.equal(edit.document.operations[0].id,"op1");
assert.equal(edit.document.operations[0].state,"PENDING");
assert.equal(edit.document.operations[0].field,"priority");
assert.equal(edit.document.operations[0].before,"none");
assert.equal(edit.document.operations[0].after,"high");
assert.equal(edit.document.nextOperationId,2);
assert.equal(edit.document.tasks[0].updatedAtMs,now+21);
assert.equal(JSON.stringify(linked),linkedBefore);
const second=m.editTask(edit.document,{
    taskId:"t20",field:"dueDate",value:"2026-10-24",nowMs:now+22});
assert.equal(second.ok,true);
assert.equal(second.document.operations[1].id,"op2");
assert.equal(second.document.operations[1].createdRevision,
    second.document.revision);
assert.equal(m.verify(second.document).ok,true);
assert.equal(m.renameProject(linked,{
    projectId:"p2",name:"Research Git",nowMs:now+31}).reason,
    "REMOTE_PROJECT_RENAME_UNSUPPORTED");
const anotherLocal=m.addLocalField(linked,{
    projectId:"p2",label:"Reviewed",kind:"boolean",nowMs:now+32});
assert.equal(anotherLocal.ok,true,anotherLocal.reason);
assert.equal(anotherLocal.document.operations.length,0);
assert.equal(anotherLocal.remoteIntentCreated,false);

// Existing M10g compatibility bridge can read v2 via lossless *display*
// projection. It must not be used to persist the richer schema as v1/v3.
const projection=m.legacyReadProjection(second.document,oldJournal);
assert.equal(projection.ok,true,projection.reason);
assert.equal(projection.writeReady,false);
const view=bridge.preview(projection.candidate,oldJournal,legacy);
assert.equal(view.ok,true,view.reason);
assert.equal(view.writeReady,false);
assert.equal(view.snapshot.writable,false);
assert.equal(view.snapshot.projects[1].name,"Research");
assert.equal(view.snapshot.items[0].priority,"high");
assert.equal(view.queuedOperations,2);
assert.equal(today.view(view.snapshot,"2026-10-23").dueToday,0);
assert.equal(planner.view(view.snapshot,"2026-10-01",
    "2026-10-24","2026-10-24").agenda[0].id,"t20");
assert.equal(JSON.stringify(second.document.tasks[0].values),JSON.stringify({f1:1250.75}));
assert.equal(projection.candidate.tasks[0].values,undefined);
assert.equal(second.document.tasks[0].values.f1,1250.75);

// The v2 parser forbids unknown fields and silent duplicate-key losses,
// including a duplicate key spelled with a JSON unicode escape.
const encoded=m.encode(second.document);
assert.equal(encoded.ok,true,encoded.reason);
const parsed=m.decode(encoded.raw);
assert.equal(parsed.ok,true,parsed.reason);
assert.equal(JSON.stringify(parsed.document),JSON.stringify(second.document));
for(const bad of [
    '{"version":2,"version":2}',
    '{"version":2,"\\u0076ersion":2}',
    '{"x":{"one":1,"one":2}}',
    '{"tasks":[{"id":"t1","id":"t2"}]}'
]) assert.equal(m.decode(bad).reason,"DUPLICATE_JSON_KEY",bad);
assert.equal(m.decode("{broken").ok,false);
assert.equal(m.decode(JSON.stringify({...second.document,version:3})).reason,
    "UNSUPPORTED_SCHEMA_VERSION");

// Invalid or unknown fields fail closed; source remains untouched.
for(const modify of [
    d=>{d.extra="future opaque data";},
    d=>{d.projects[0].extra="would be discarded";},
    d=>{d.projects[1].fields[0].scope="github";},
    d=>{d.projects[1].fields[0].kind="currency";},
    d=>{d.projects[1].fields.push({...d.projects[1].fields[0]});},
    d=>{d.tasks[0].values.unknown="bad";},
    d=>{d.tasks[0].values.f1="bad";},
    d=>{d.tasks[0].remote={projectItemNodeId:"madeup",contentKind:"ISSUE",contentNodeId:null};},
    d=>{d.projects[1].remote.projectNodeId="";},
    d=>{d.tasks[0].updatedAtMs=d.tasks[0].createdAtMs-1;},
    d=>{d.operations[0].state="ACKNOWLEDGED";},
    d=>{d.nextOperationId=2;},
    d=>{d.tasks[0].projectId="p99";},
    d=>{d.tasks[0].dueDate="2026-02-29";},
    d=>{d.projects[0].name="Research";},
]) {
    const fixture=JSON.parse(JSON.stringify(second.document));
    modify(fixture);
    assert.equal(m.verify(fixture).ok,false,JSON.stringify(fixture).slice(0,130));
}
assert.equal(m.editTask(linked,{
    taskId:"t20",field:"priority",value:"invalid",nowMs:now+50}).ok,false);
assert.equal(m.editTask(linked,{
    taskId:"t20",field:"priority",value:"high",nowMs:now-1}).ok,false);
for(const forbidden of [
    "FileView {","Process {","ApolloHubTodoStore {","GitHubProjectsService {",
    "Quickshell.execDetached(","setText(","XMLHttpRequest","fetch(","require("
]) assert.ok(!v2.source.includes(forbidden),"forbidden effect: "+forbidden);
console.log("TASKS M10h v2 strict model, typed fields, monotonic edits and read bridge: PASS");
