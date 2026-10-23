#!/usr/bin/env node
"use strict";
// Proxy 1 M10d. Pure policies only; inputs are synthetic fixtures,
// NOT the user's files. No filesystem writes, Quickshell or gh processes.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
function policy(file) {
    const script=fs.readFileSync(file,"utf8").replace(/^\.pragma library\s*$/m,"");
    const ctx=vm.createContext({JSON,Array,Object,String,Number,RegExp,Date,Math});
    vm.runInContext(script,ctx,{filename:file});
    return {ctx,script};
}
const legacy=policy("services/hub/ApolloHubTodoPolicy.js").ctx;
const journal=policy("services/projects/OfflineOperationJournal.js").ctx;
const migrator=policy("services/projects/LegacyMigrationDryRun.js");
const move=migrator.ctx;

function raw(doc) { return JSON.stringify(doc); }
const at=1771521000000;
const project=(id,name,created=at)=>({
    id,name,createdAtMs:created,updatedAtMs:created+120
});
const task=(id,title,projectId,options={})=>({
    id,title,done:options.done||false,
    createdAtMs:options.createdAtMs||at,
    updatedAtMs:options.updatedAtMs||at+240,
    priority:options.priority||"none",
    description:options.description||"",
    dueDate:options.dueDate===undefined?null:options.dueDate,
    projectId
});
const v3={
    version:3,nextId:81,nextProjectId:22,
    projects:[project("p1","Personal"),project("p20","Gaming",at+10000)],
    tasks:[
        task("t4","Test migration","p20",{priority:"urgent",
            description:"Detailed text\nSecond line & symbols",dueDate:"0001-01-01"}),
        task("t80","Without a project",null,{done:true,
            priority:"low",description:"Saved notes",dueDate:"2024-02-29"})
    ]
};
const source=raw(v3);
const normalized=legacy.parse(source);
assert.equal(normalized.ok,true);
const result=move.plan(source,legacy,journal);
assert.equal(result.ok,true,result.reason);
assert.equal(result.sourceVersion,3);
assert.equal(result.counts.projects,2);
assert.equal(result.counts.tasks,2);
assert.equal(result.writeReady,false);
assert.equal(result.migrationPerformed,false);
assert.equal(result.candidate.version,1,"prototype version, not live Todo v4");
assert.equal(result.candidate.revision,0);
assert.equal(result.candidate.nextId,81);
assert.equal(result.candidate.nextProjectId,22);
assert.equal(result.candidate.operations.length,0);
assert.equal(result.candidate.projects[0].family,"normal");
assert.equal(result.candidate.projects[1].family,"normal");
assert.equal(result.candidate.projects[0].remote,null);
assert.equal(result.candidate.projects[1].remote,null);
assert.equal(result.candidate.tasks[0].dueDate,"0001-01-01");
assert.equal(result.candidate.tasks[1].dueDate,"2024-02-29");
assert.equal(result.candidate.tasks[0].description,
    "Detailed text\nSecond line & symbols");
assert.equal(result.candidate.tasks[0].projectId,"p20");
assert.equal(result.candidate.tasks[1].projectId,null);
assert.equal(result.candidate.tasks[0].createdAtMs,at);
assert.equal(result.candidate.projects[1].updatedAtMs,at+10120);
assert.equal(JSON.stringify(result.compatibilityV3),
    JSON.stringify(normalized.document),"v3 projection must be byte-equivalent as JSON");
assert.equal(JSON.stringify(v3),source,"never modify source");

const compatibility=move.restoreCompatibleV3(result.candidate,legacy,journal);
assert.equal(compatibility.ok,true);
assert.equal(JSON.stringify(compatibility.document),
    JSON.stringify(normalized.document));

// Existing user-facing readers must still recognize the v3 projection.
const snapshot=legacy.view("ready",compatibility.document,"");
assert.equal(snapshot.total,2);
assert.equal(snapshot.projects.length,2);
assert.equal(snapshot.items[0].projectId,"p20");
assert.equal(snapshot.items[0].description,
    "Detailed text\nSecond line & symbols");
assert.equal(snapshot.items[1].done,true);

// Older v1/v2 records normalize safely; no false project identity.
const basicTask={
    id:"t1",title:"Old checklist",done:false,
    createdAtMs:at,updatedAtMs:at
};
const v1={version:1,nextId:2,tasks:[basicTask]};
const one=move.plan(raw(v1),legacy,journal);
assert.equal(one.ok,true,one.reason);
assert.equal(one.sourceVersion,1);
assert.equal(one.candidate.nextId,2);
assert.equal(one.candidate.nextProjectId,1);
assert.equal(one.candidate.tasks[0].priority,"none");
assert.equal(one.candidate.tasks[0].description,"");
assert.equal(one.candidate.tasks[0].dueDate,null);
assert.equal(one.candidate.tasks[0].projectId,null);
assert.equal(one.candidate.projects.length,0);
assert.equal(one.candidate.operations.length,0);
const v2={
    version:2,nextId:9,tasks:[{
        ...basicTask,id:"t8",priority:"medium",
        description:"v2 survives",dueDate:"2026-10-23"
    }]
};
const two=move.plan(raw(v2),legacy,journal);
assert.equal(two.ok,true,two.reason);
assert.equal(two.sourceVersion,2);
assert.equal(two.candidate.nextId,9);
assert.equal(two.candidate.tasks[0].description,"v2 survives");
assert.equal(two.candidate.tasks[0].priority,"medium");
assert.equal(two.candidate.tasks[0].projectId,null);

// Empty and sparse-counter documents must stay empty/sparse.
const empty=move.plan(raw(legacy.emptyDocument()),legacy,journal);
assert.equal(empty.ok,true);
assert.equal(empty.candidate.projects.length,0);
assert.equal(empty.candidate.tasks.length,0);
const deleted=move.plan(raw({
    version:3,nextId:900,nextProjectId:99,projects:[],tasks:[]
}),legacy,journal);
assert.equal(deleted.ok,true);
assert.equal(deleted.candidate.nextId,900);
assert.equal(deleted.candidate.nextProjectId,99);

// Legacy validation would otherwise discard unknown properties on clone.
// The new migration MUST reject them before any candidate becomes available.
for(const [alter,expected] of [
    [x=>{x.unexpected="DO NOT DROP ME"}, "UNRECOGNIZED_LEGACY_FIELDS"],
    [x=>{x.projects[0].externalMetadata="do not lose"}, "UNRECOGNIZED_PROJECT_FIELDS"],
    [x=>{x.tasks[0].customField="do not lose"}, "UNRECOGNIZED_TASK_FIELDS"],
    [x=>{x.version=4}, "LEGACY_UNSUPPORTED_VERSION"],
    [x=>{x.tasks[0].projectId="p99"}, "LEGACY_UNKNOWN_PROJECT_REFERENCE"],
    [x=>{x.tasks[0].dueDate="2026-02-29"}, "LEGACY_INVALID_TASK"],
    [x=>{x.nextId=80}, "LEGACY_SEQUENCE_REWIND"],
    [x=>{x.nextProjectId=20}, "LEGACY_PROJECT_SEQUENCE_REWIND"],
    [x=>{x.projects.push({...x.projects[0]})}, "LEGACY_DUPLICATE_PROJECT_ID"],
    [x=>{x.tasks.push({...x.tasks[0]})}, "LEGACY_DUPLICATE_ID"]
]) {
    const doc=JSON.parse(source);
    alter(doc);
    const out=move.plan(raw(doc),legacy,journal);
    assert.equal(out.ok,false,expected);
    assert.equal(out.reason,expected);
}
for (const bad of ["", "{truncated", "null", "[]", "x".repeat(1048577)]) {
    assert.equal(move.plan(bad,legacy,journal).ok,false);
}

// Can't reconstruct safe v3 snapshot once journal has live pending changes,
// a project becomes GIT, or extra fields appear.
for (const modify of [
    d=>{d.revision=1},
    d=>{d.projects[0].family="git"},
    d=>{d.projects[0].remote={provider:"github"}},
    d=>{d.tasks[0].custom="local extension"},
    d=>{d.nextId=undefined},
    d=>{d.someFutureField=42}
]) {
    const candidate=JSON.parse(JSON.stringify(result.candidate));
    modify(candidate);
    const roll=move.restoreCompatibleV3(candidate,legacy,journal);
    assert.equal(roll.ok,false,JSON.stringify(candidate).slice(0,150));
}
assert.equal(move.plan(source,null,journal).ok,false);
assert.equal(move.plan(source,legacy,null).ok,false);

for(const forbidden of [
    "FileView {","Process {","Qt.openUrlExternally(","gh project ",
    "Quickshell.execDetached(","setText(","fetch(","XMLHttpRequest",
    "require(","fs.write","ApolloHubTodoStore {"
]) assert.ok(!migrator.script.includes(forbidden),
             "dry-run policy must be pure: "+forbidden);
console.log("TASKS M10d non-destructive v1/v2/v3 migration and compatibility tests: PASS");
