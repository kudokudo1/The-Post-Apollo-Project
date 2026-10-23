#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const src=fs.readFileSync(path.join(__dirname,
    "../../widgets/tasks/TaskProjectsAck.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const ack=vm.createContext({});
vm.runInContext(src,ack,{filename:"TaskProjectsAck.js"});

const old={state:"ready",projects:[{id:"p1",name:"Old"}],
    items:[{id:"t1",projectId:"p1"}]};
const saving={...old,state:"saving"};
const renamed={state:"ready",projects:[{id:"p1",name:"New"}],
    items:[{id:"t1",projectId:"p1"}]};
const failed={...old,state:"error"};
const check=(snap,kind,id,name,taskId,target,count)=>
    ack.status(snap,kind,id,name,taskId,target,count);

assert.equal(check(null,"rename","p1","New","","",1),"waiting");
assert.equal(check(saving,"rename","p1","New","","",1),"waiting");
assert.equal(check({...old,state:"loading"},"rename","p1","New","","",1),"waiting");
assert.equal(check(failed,"rename","p1","New","","",1),"failed");
assert.equal(check({...old,state:"unsupported"},"rename","p1","New","","",1),"failed");

// QML derived state can lag a new snapshot. Status uses the supplied
// snapshot alone, never separate cached properties from the caller.
assert.equal(check(renamed,"rename","p1","New","","",1),"confirmed");
assert.equal(check(old,"rename","p1","New","","",1),"unconfirmed");
assert.equal(check({...renamed,projects:null},"rename","p1","New","","",1),
             "unconfirmed");
assert.equal(check(renamed,"rename","p2","New","","",1),"unconfirmed");

// Each prior operation also gets a final outcome rather than indefinite lock.
assert.equal(check({state:"ready",projects:[{id:"p2",name:"Created"}],
                    items:[]},"create","","Created","","",0),"confirmed");
assert.equal(check(old,"create","","Created","","",1),"unconfirmed");
assert.equal(check({...old,items:[{id:"t1",projectId:"p2"}]},
                   "assign","","","t1","p2",1),"confirmed");
assert.equal(check(old,"assign","","","t1","p2",1),"unconfirmed");
assert.equal(check({...old,items:[{id:"t1",projectId:null}]},
                   "assign","","","t1",null,1),"confirmed");
const deleted={state:"ready",projects:[],items:[{id:"t1",projectId:null}]};
assert.equal(check(deleted,"delete","p1","","","",1),"confirmed");
assert.equal(check(old,"delete","p1","","","",1),"unconfirmed");
assert.equal(check({...deleted,items:[]},"delete","p1","","","",1),"unconfirmed");
assert.equal(check({state:"ready",projects:[],items:[{id:"t1",projectId:"p1"}]},
                   "delete","p1","","","",1),"unconfirmed");

// A status that's neither in-flight nor a commit cannot be called saved.
assert.equal(check({state:"unexpected",projects:[],items:[]},"rename",
                   "p1","New","","",0),"failed");
console.log("TASKS PROJECTS acknowledgement ordering and unlock contracts: PASS");
