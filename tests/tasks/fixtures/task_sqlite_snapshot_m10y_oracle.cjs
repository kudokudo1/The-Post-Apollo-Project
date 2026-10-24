#!/usr/bin/env node
"use strict";
// Compare real Python projection with the actual deployed legacy policy.
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
function load(path){
    const src=fs.readFileSync(path,"utf8").replace(/^\.pragma library\s*$/m,"");
    const ctx=vm.createContext({Date,Math,Array,Object,Number,String,RegExp,JSON});
    vm.runInContext(src,ctx,{filename:path});
    return ctx;
}
const old=load("services/hub/ApolloHubTodoPolicy.js");
const planner=load("widgets/tasks/TaskPlannerPolicy.js");
const today=load("widgets/tasks/TaskTodayPolicy.js");
const payload=JSON.parse(fs.readFileSync(0,"utf8"));
assert.equal(payload.protocol,1);
assert.equal(payload.writeReady,false);
assert.equal(payload.remoteWriteAuthorized,false);
assert.equal(payload.available,true);
assert.ok(["READY","EMPTY","RECOVERY_REVIEW"].includes(payload.status));
assert.equal(old.validate(payload.document).ok,true);
const docs=payload.document;
const saved=JSON.stringify(docs);
const view=old.view(docs.tasks.length?"ready":"empty",docs,"");
view.writable=false;
assert.equal(view.writable,false);
assert.equal(view.total,docs.tasks.length);
assert.equal(view.items.length,docs.tasks.length);
assert.equal(view.remaining,docs.tasks.filter(t=>!t.done).length);
assert.deepEqual(Array.from(view.items,t=>t.id),
    [...docs.tasks.filter(t=>!t.done),...docs.tasks.filter(t=>t.done)]
     .map(t=>t.id));
for(const p of view.projects){
    assert.equal(p.total,docs.tasks.filter(t=>t.projectId===p.id).length);
}
const daily=today.view(view,"2026-10-24");
const month=planner.view(view,"2026-10-01","2026-10-24","2026-10-24");
assert.equal(daily.available,true);
assert.equal(month.available,true);
assert.equal(JSON.stringify(docs),saved);
assert.equal(payload.sourceHash.length,64);
process.stdout.write(JSON.stringify({
    state:view.state,total:view.total,remaining:view.remaining,
    completed:view.completed,ids:Array.from(view.items,t=>t.id),
    projectIds:Array.from(view.projects,p=>p.id),
    todayCount:daily.dueToday,agendaCount:month.agenda.length,
    writable:view.writable
})+"\n");
