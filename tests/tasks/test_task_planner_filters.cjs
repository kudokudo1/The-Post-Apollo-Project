#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const source=fs.readFileSync("widgets/tasks/TaskPlannerSchedulingPolicy.js","utf8")
    .replace(/^\.pragma library\s*$/m,"");
const ctx={Date,Number,String,Array,Object,Math};
vm.createContext(ctx);
vm.runInContext(source,ctx);
const snapshot={state:"ready",writable:true,projects:[
    {id:"p1",name:"Home"}, {id:"p2",name:"Git"}],items:[
    {id:"t4",title:"Done",done:true,priority:"high",projectId:"p1",dueDate:null},
    {id:"t1",title:"Future",done:false,priority:"low",projectId:"p1",dueDate:"2026-11-05"},
    {id:"t3",title:"Unscheduled",done:false,priority:"high",projectId:null,dueDate:null},
    {id:"t2",title:"Today",done:false,priority:"high",projectId:"p2",dueDate:"2026-10-24"},
    {id:"t5",title:"Another",done:false,priority:"high",projectId:"p1",dueDate:null}
]};
const ids=(p,pr="any",u=false)=>Array.from(ctx.candidates(snapshot,p,pr,u),t=>t.id);
assert.deepEqual(ids("all"),["t3","t5","t2","t1"]);
assert.deepEqual(ids("all","high"),["t3","t5","t2"]);
assert.deepEqual(ids("all","any",true),["t3","t5"]);
assert.deepEqual(ids("p1"),["t5","t1"]);
assert.deepEqual(ids("p1","high",true),["t5"]);
assert.deepEqual(ids("p2"),["t2"]);
assert.deepEqual(ids("unassigned"),["t3"]);
assert.deepEqual(ids("p9"),[]);
assert.deepEqual(ids("all","bogus"),[]);
assert.deepEqual(Array.from(ctx.candidates({...snapshot,state:"error"},"all","any",false)),[]);
assert.deepEqual(Array.from(ctx.candidates({...snapshot,state:"saving"},"all","any",false),t=>t.id),
    ["t3","t5","t2","t1"]);
assert.equal(snapshot.items[0].id,"t4"); // Original order/identity never changed.
const older=["t1","t2","t3","t4","t5"];
assert.equal(ctx.newlyCreated(snapshot,older,"New"),null);
const newItem={id:"t6",title:"New",done:false,priority:"none",description:"",
    dueDate:null,projectId:null};
const created={...snapshot,items:snapshot.items.concat([newItem])};
assert.equal(ctx.newlyCreated(created,older,"New").id,"t6");
assert.equal(ctx.newlyCreated(created,older.concat(["t6"]),"New"),null);
assert.equal(ctx.newlyCreated({...created,state:"saving"},older,"New"),null);
assert.equal(ctx.newlyCreated({...created,state:"error"},older,"New"),null);
assert.equal(ctx.newlyCreated({...created,items:[...snapshot.items,{...newItem,dueDate:"2026-10-24"}]},older,"New"),null);
console.log("PLANNER M5b filters, undated queue, identity and save-readback: PASS");
