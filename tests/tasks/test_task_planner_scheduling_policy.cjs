#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const src=fs.readFileSync("widgets/tasks/TaskPlannerSchedulingPolicy.js","utf8")
    .replace(/^\.pragma library\s*$/m,"");
const ctx={Date,Number,String,Array,Object,Math};vm.createContext(ctx);vm.runInContext(src,ctx);
const initial={state:"ready",writable:true,items:[
    {id:"t1",title:"Work",done:false,priority:"high",description:"Keep details",
     dueDate:null,projectId:"p2"},
    {id:"t2",title:"Study",done:false,priority:"none",description:"",
     dueDate:"2026-10-23",projectId:null}
]};
const original=ctx.signature(initial.items[0]);
const p=ctx.proposal(initial,original,"2026-10-24");
assert.equal(p.ok,true);
assert.equal(p.id,"t1");
assert.equal(p.priority,"high");
assert.equal(p.description,"Keep details");
assert.equal(p.targetDate,"2026-10-24");
assert.equal(p.expected.projectId,"p2");
assert.equal(p.expected.title,"Work");
assert.equal(ctx.verified(initial,p.expected),false);
const committed={...initial,items:[{...initial.items[0],dueDate:"2026-10-24"},initial.items[1]]};
assert.equal(ctx.verified(committed,p.expected),true);
assert.equal(ctx.proposal(initial,original,null).reason,"DATE UNCHANGED");
assert.equal(ctx.proposal(initial,original,"2026-02-30").reason,"INVALID DATE");
assert.equal(ctx.proposal(initial,original,"2024-02-29").ok,true);
assert.equal(ctx.proposal(initial,original,"0004-02-29").ok,true);
assert.equal(ctx.proposal(initial,original,"0001-02-29").reason,"INVALID DATE");
assert.equal(ctx.proposal({...initial,writable:false},original,"2026-10-24").reason,"STORAGE LOCKED");
assert.equal(ctx.proposal({...initial,state:"saving"},original,"2026-10-24").reason,"STORAGE LOCKED");
assert.equal(ctx.proposal({...initial,state:"error"},original,"2026-10-24").reason,"STORAGE LOCKED");
assert.equal(ctx.proposal({...initial,items:[{...initial.items[0],description:"Changed"},initial.items[1]]},
    original,"2026-10-24").reason,"TASK CHANGED // CANCEL & RESELECT");
assert.equal(ctx.proposal({...initial,items:[initial.items[1]]},original,"2026-10-24").reason,"TASK REMOVED");
const dated=ctx.signature(initial.items[1]);
assert.equal(ctx.proposal(initial,dated,null).ok,true);
assert.equal(ctx.proposal(initial,dated,"2026-10-23").reason,"DATE UNCHANGED");
assert.equal(ctx.canCreate(initial,"New task"),true);
assert.equal(ctx.canCreate(initial,"   "),false);
assert.equal(ctx.canCreate(initial,"X".repeat(161)),false);
assert.equal(ctx.canCreate(initial,"bad\u0000name"),false);
assert.equal(ctx.canCreate({...initial,writable:false},"New"),false);
assert.equal(ctx.created(initial,["t1","t2"],"New task"),false);
const added={...initial,items:initial.items.concat([
    {id:"t3",title:"New task",done:false,priority:"none",description:"",
        dueDate:null,projectId:null}])};
assert.equal(ctx.created(added,["t1","t2"],"New task"),true);
assert.equal(ctx.created({...added,state:"saving"},["t1","t2"],"New task"),false);
assert.equal(ctx.created(added,["t1","t2","t3"],"New task"),false);
console.log("PLANNER M5a guarded scheduling proposals, stale checks, create acknowledgements: PASS");
