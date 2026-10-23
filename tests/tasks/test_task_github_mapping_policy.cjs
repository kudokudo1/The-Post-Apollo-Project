#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const source=fs.readFileSync(path.join(__dirname,
    "../../widgets/tasks/TaskGitHubMappingPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const p=vm.createContext({});
vm.runInContext(source,p,{filename:"TaskGitHubMappingPolicy.js"});

const local={
    state:"ready",
    projects:[{id:"p1",name:"Same name as remote",total:2,remaining:1,completed:1}],
    items:[
        {id:"t1",title:"Same title as remote",projectId:"p1",
         priority:"high",dueDate:"2027-01-30",
         description:"PRIVATE LOCAL DESCRIPTION",done:false},
        {id:"t2",title:"Complete",projectId:"p1",
         priority:"none",dueDate:null,description:"",done:true},
        {id:"t3",title:"Independent",projectId:null,
         priority:"urgent",dueDate:"2027-02-01",
         description:"a",done:false}
    ]
};
const original=JSON.stringify(local);
const view=p.preview(local);
assert.equal(view.available,true);
assert.equal(view.localProjects,1);
assert.equal(view.localTasks,3);
assert.equal(view.tasksWithPriority,2);
assert.equal(view.tasksWithDate,2);
assert.equal(view.tasksWithDescription,2);
assert.equal(view.tasksDone,1);
assert.equal(view.writeReady,0);
assert.equal(view.projectRows[0].id,"p1");
assert.equal(view.projectRows[0].linkage,"NEEDS_VERIFIED_REMOTE_PROJECT_ID");
assert.equal(view.taskRows[0].id,"t1");
assert.equal(view.taskRows[0].linkage,"NEEDS_VERIFIED_REMOTE_ITEM_ID");
assert.equal(view.taskRows[1].projectId,"p1");
assert.equal(view.taskRows[2].projectId,null);
assert.equal(view.fieldRows.length,4);
assert.deepEqual(Array.from(view.fieldRows.map(x=>x.local)),
                 ["priority","dueDate","done","description"]);
assert.equal(view.fieldRows.find(x=>x.local==="done").readiness,
             "NEEDS_EXPLICIT_STATUS_SEMANTICS");
assert.equal(view.fieldRows.find(x=>x.local==="priority").readiness,
             "NEEDS_FIELD_AND_OPTION_IDS");
assert.equal(JSON.stringify(local),original);
for(const forbidden of ["PRIVATE LOCAL DESCRIPTION","remoteProjectId","remoteItemId",
                         "updatedAtMs","createdAtMs","authToken","linked:true"]){
    assert.equal(JSON.stringify(view).includes(forbidden),false,forbidden);
}
// Even matching remote titles must never be promoted to a proven identity.
const withUntrustedRemoteData={...local,
    remoteProjects:[{id:"PVT_fake",title:"Same name as remote"}],
    remoteItems:[{id:"PVTI_fake",title:"Same title as remote"}]};
assert.equal(p.preview(withUntrustedRemoteData).writeReady,0);
assert.equal(p.preview(withUntrustedRemoteData).taskRows[0].linkage,
             "NEEDS_VERIFIED_REMOTE_ITEM_ID");

for(const state of ["loading","error","unsupported","unavailable"]) {
    const blocked=p.preview({...local,state});
    assert.equal(blocked.available,false,state);
    assert.equal(blocked.localTasks,0,state);
    assert.equal(blocked.localProjects,0,state);
    assert.equal(blocked.projectRows.length,0,state);
    assert.equal(blocked.writeReady,0,state);
}
assert.equal(p.preview({...local,state:"saving"}).available,true);
assert.equal(p.preview(null).available,false);
assert.equal(p.preview({state:"ready",projects:[],items:[]}).localTasks,0);
console.log("TASKS GitHub Projects mapping preview is local/read-only: PASS");
