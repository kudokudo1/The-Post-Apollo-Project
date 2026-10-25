#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
function load(file){
    const s=fs.readFileSync(file,"utf8").replace(/^\.pragma library\s*$/m,"");
    const ctx=vm.createContext({Date,Number,String,Array,Object,Math,JSON,RegExp});
    vm.runInContext(s,ctx,{filename:file});
    return {ctx,source:s};
}
const parity=load("services/projects/TaskSqliteShadowParityM11a.js");
const todo=load("services/hub/ApolloHubTodoPolicy.js");
const TIME=1700000000000;
function source(){
    return {version:3,nextId:4,nextProjectId:3,
        projects:[
            {id:"p1",name:"Work",createdAtMs:TIME,updatedAtMs:TIME+3},
            {id:"p2",name:"Home",createdAtMs:TIME,updatedAtMs:TIME+5}],
        tasks:[
            {id:"t1",title:"Needs attention",done:false,
             priority:"high",description:"Private notes",dueDate:"2026-10-24",
             projectId:"p1",createdAtMs:TIME,updatedAtMs:TIME+2},
            {id:"t2",title:"Completed",done:true,priority:"low",
             description:"",dueDate:null,projectId:"p2",
             createdAtMs:TIME,updatedAtMs:TIME+2},
            {id:"t3",title:"Unassigned",done:false,priority:"none",
             description:"No sync",dueDate:null,projectId:null,
             createdAtMs:TIME,updatedAtMs:TIME+2}]};
}
const deep=o=>JSON.parse(JSON.stringify(o));
const response=(doc,patch={})=>({
    protocol:1,status:doc.tasks.length?"READY":"EMPTY",
    available:true,revision:0,sourceHash:"a".repeat(64),
    blockedOperations:0,document:doc,
    writeReady:false,remoteWriteAuthorized:false,...patch
});
const old=source();
assert.equal(todo.ctx.validate(old).ok,true);
const baseline=JSON.stringify(old);
const out=parity.ctx.compare(old,response(deep(old)),todo.ctx);
assert.equal(out.status,"MATCH_FOR_REVIEW_ONLY");
assert.equal(out.matched,true);
assert.equal(out.snapshot.writable,false);
assert.equal(out.snapshot.total,3);
assert.equal(out.snapshot.remaining,2);
assert.equal(out.snapshot.completed,1);
assert.equal(out.snapshot.projects[0].total,1);
assert.equal(out.snapshot.projects[1].total,1);
assert.equal(out.writeReady,false);
assert.equal(out.activate,false);
assert.equal(out.migrate,false);
assert.equal(out.legacyWriterFrozen,false);
assert.equal(out.sqliteWriterAuthorized,false);
assert.equal(out.remoteWriteAuthorized,false);
assert.equal(JSON.stringify(old),baseline);
// Successful previews intentionally retain task content in memory for UI parity.\n// Failure reports emit only field identifiers, never private values.
const paired=deep(old);
paired.tasks[0].description="Private changed";
let x=parity.ctx.compare(old,response(paired),todo.ctx);
assert.equal(x.status,"DIVERGED");
assert.ok(Array.from(x.blockers).includes("tasks[0].description"));
assert.equal(x.snapshot,null);
assert.ok(!JSON.stringify(x).includes("Private changed"));
// Check every compatibility field, including same-count reorders.
const mutations=[
    [x=>x.tasks[0].title="Different title","tasks[0].title"],
    [x=>x.tasks[0].priority="urgent","tasks[0].priority"],
    [x=>x.tasks[0].dueDate="2026-10-25","tasks[0].dueDate"],
    [x=>x.tasks[0].projectId="p2","tasks[0].projectId"],
    [x=>x.tasks[0].done=true,"tasks[0].done"],
    [x=>x.tasks[0].updatedAtMs++,"tasks[0].updatedAtMs"],
    [x=>x.projects[1].name="A different project","projects[1].name"],
    [x=>x.projects[1].createdAtMs++,"projects[1].createdAtMs"],
    [x=>x.nextId++,"nextId"],
    [x=>x.nextProjectId++,"nextProjectId"],
    [x=>x.tasks.reverse(),"tasks[0].id"],
    [x=>x.projects.reverse(),"projects[0].id"]
];
for(const [edit,key] of mutations) {
    const changed=deep(old);edit(changed);
    assert.equal(todo.ctx.validate(changed).ok,true,key);
    const r=parity.ctx.compare(old,response(changed),todo.ctx);
    assert.equal(r.status,"DIVERGED",key);
    assert.ok(Array.from(r.blockers).includes(key),key);
    assert.equal(r.activate,false);
    assert.equal(r.snapshot,null);
}
for (const patch of [
    {status:"RECOVERY_REVIEW",blockedOperations:1},
    {status:"READY",blockedOperations:1},
    {status:"ABSENT",available:false,document:null,revision:null,sourceHash:null},
    {status:"ERROR",available:false},
    {protocol:2},{writeReady:true},{remoteWriteAuthorized:true},
    {sourceHash:"unknown"},{revision:-1},{blockedOperations:-1},
    {available:"true"},{unexpected:true}
]) {
    const r=parity.ctx.compare(old,response(deep(old),patch),todo.ctx);
    assert.equal(r.status,"BLOCKED",JSON.stringify(patch));
    assert.equal(r.matched,false);
    assert.equal(r.writeReady,false);
}
for(const modify of [
    d=>{d.tasks[0].dueDate="2026-02-30";},
    d=>{d.version=4;},d=>{delete d.tasks[0].id;},
    d=>{d.projects[1].id="p1";}
]) {
    const invalid=deep(old);modify(invalid);
    assert.equal(parity.ctx.compare(invalid,response(deep(old)),todo.ctx).status,"BLOCKED");
    assert.equal(parity.ctx.compare(old,response(invalid),todo.ctx).status,"BLOCKED");
}
const empty={version:3,nextId:1,nextProjectId:1,projects:[],tasks:[]};
assert.equal(parity.ctx.compare(empty,response(deep(empty)),todo.ctx).status,
             "MATCH_FOR_REVIEW_ONLY");
assert.equal(parity.ctx.compare(empty,response(deep(empty),{status:"READY"})).status,
             "BLOCKED");
assert.equal(parity.ctx.compare(old,response(deep(old)),null).status,"BLOCKED");
assert.equal(parity.ctx.compare(old,response(deep(old),{operatorApproved:true}),
                               todo.ctx).status,"BLOCKED");
console.log("M11a exact legacy/SQLite shadow parity, mutation coverage, and permanent no-activation: PASS");
