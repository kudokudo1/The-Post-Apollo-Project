#!/usr/bin/env node
"use strict";
// Execute the pure QML JS policy under Node after removing Qt's library pragma.
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const source=fs.readFileSync("widgets/tasks/TaskPlannerPolicy.js","utf8")
 .replace(/^\.pragma library\s*$/m,"");
const ctx={Date,Number,String,Array,Math};vm.createContext(ctx);vm.runInContext(source,ctx);
const month="2026-10-01";
assert.equal(ctx.moveMonth(month,1),"2026-11-01");
assert.equal(ctx.moveMonth(month,-1),"2026-09-01");
assert.equal(ctx.moveMonth("2026-01-01",-1),"2025-12-01");
assert.equal(ctx.parse("2026-02-29"),null);
assert.ok(ctx.parse("2024-02-29"));
assert.ok(ctx.parse("0004-02-29"));
assert.equal(ctx.parse("0001-02-29"),null);
assert.equal(ctx.key(1,2,3),"0001-02-03");
assert.equal(ctx.moveMonth("0001-01-01",-1),"0001-01-01");
assert.equal(ctx.moveMonth("0099-12-01",1),"0100-01-01");
const early=ctx.view({state:"empty",items:[]},"0001-01-01","0001-01-01","0001-01-01");
assert.equal(early.days.length,42);
assert.equal(early.days.find(d=>d.date==="0001-01-01").day,1);
assert.equal(early.days[0].date,"0001-01-01");
const sample={state:"ready",items:[
 {id:"t1",title:"Review",done:false,dueDate:"2026-10-23",priority:"high",projectId:"p1"},
 {id:"t2",title:"Finished",done:true,dueDate:"2026-10-23"},
 {id:"t3",title:"Tomorrow",done:false,dueDate:"2026-10-24"},
 {id:"t4",title:"Unplanned",done:false,dueDate:null},
 {id:"t5",title:"Bogus date",done:false,dueDate:"2026-02-30"}
]};
const result=ctx.view(sample,month,"2026-10-23","2026-10-23");
assert.equal(result.available,true);
assert.equal(result.days.length,42);
assert.equal(result.agenda.length,2);
assert.equal(result.agenda[0].id,"t1");
assert.equal(result.agenda[1].id,"t2");
assert.equal(result.scheduled,3);
assert.equal(result.undated,2);
assert.equal(result.days.filter(d=>d.today).length,1);
assert.equal(result.days.filter(d=>d.selected).length,1);
assert.equal(ctx.view({state:"error",items:sample.items},month,"2026-10-23","2026-10-23").available,false);
assert.equal(ctx.view(sample,"bad","2026-10-23","2026-10-23").days.length,0);
console.log("PLANNER M1 date, month, agenda, state checks: PASS");
