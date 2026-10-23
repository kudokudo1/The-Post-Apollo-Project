#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const code = fs.readFileSync(path.join(__dirname,
  "../../widgets/tasks/TaskTodayPolicy.js"), "utf8")
  .replace(/^\s*\.pragma library\s*/m, "");
const p = vm.createContext({});
vm.runInContext(code, p, {filename:"TaskTodayPolicy.js"});
const today="2026-10-22";
const tasks=[
  {id:"t1", title:"Overdue 2", dueDate:"2026-10-21", done:false, priority:"high"},
  {id:"t2", title:"Today", dueDate:today, done:false, priority:"medium"},
  {id:"t3", title:"Already done", dueDate:today, done:true, priority:"none"},
  {id:"t4", title:"Upcoming", dueDate:"2026-10-23", done:false, priority:"low"},
  {id:"t5", title:"Unscheduled", dueDate:null, done:false, priority:"none"},
  {id:"t6", title:"Older done", dueDate:"2026-10-10", done:true, priority:"none"},
  {id:"t7", title:"Overdue 1", dueDate:"2026-10-20", done:false, priority:"urgent"},
  {id:"t8", title:"Undated done", dueDate:null, done:true, priority:"none"}
];
const original=JSON.stringify(tasks);
const r=p.view({state:"ready",items:tasks},today);
assert.equal(r.available,true);
assert.equal(r.overdue,2);
assert.equal(r.dueToday,1);
assert.equal(r.completedDueToday,1);
assert.equal(r.upcoming,1);
assert.equal(r.unscheduled,1);
assert.equal(r.today,today);
assert.equal(JSON.stringify(tasks),original); // projection never mutates source
assert.deepEqual(Array.from(r.rows.filter(x=>x.kind==="task").map(x=>x.id)),
  ["t7","t1","t2","t3"]);
assert.deepEqual(Array.from(r.rows.filter(x=>x.kind==="header").map(x=>x.text)),
  ["OVERDUE // 2","DUE TODAY // 1","DONE // DUE TODAY // 1"]);
assert.equal(r.rows.find(x=>x.id==="t7").priority,"urgent");
assert.equal(r.rows.find(x=>x.id==="t3").done,true);
assert.equal(r.rows.some(x=>x.id==="t6"),false); // not "completed today"
const privacy=JSON.stringify(r);
assert.equal(privacy.includes("createdAtMs"),false);
assert.equal(privacy.includes("updatedAtMs"),false);
for(const state of ["loading","error","unsupported","unavailable"]){
  const bad=p.view({state,items:tasks},today);
  assert.equal(bad.available,false,state);
  assert.equal(bad.rows.length,0,state);
}
assert.equal(p.view({state:"saving",items:tasks},today).available,true);
assert.equal(p.view({state:"ready",items:tasks},"2026-10-2").available,false);
assert.equal(p.view({state:"ready",items:tasks},"").available,false);
assert.equal(p.view({state:"ready",items:null},today).available,false);
const empty=p.view({state:"empty",items:[]},today);
assert.equal(empty.available,true);
assert.equal(empty.rows.length,0);

// Crossing DST weeks still relies on civil day strings rather than 24h offsets.
const dst=p.view({state:"ready",items:[
  {id:"t9",title:"Before DST",dueDate:"2026-03-07",done:false},
  {id:"t10",title:"DST day",dueDate:"2026-03-08",done:false},
  {id:"t11",title:"After DST",dueDate:"2026-03-09",done:false}
]},"2026-03-08");
assert.equal(dst.overdue,1);
assert.equal(dst.dueToday,1);
assert.equal(dst.upcoming,1);
console.log("TASKS TODAY local due-date projection contracts: PASS");
