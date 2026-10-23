#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const src=fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubTodoPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const p=vm.createContext({});
vm.runInContext(src,p,{filename:"ApolloHubTodoPolicy.js"});
const t=1000000;
const old1={version:1,nextId:2,tasks:[
  {id:"t1",title:"Old",done:false,createdAtMs:4,updatedAtMs:6}
]};
const old2={version:2,nextId:2,tasks:[
  {id:"t1",title:"M4",done:true,createdAtMs:4,updatedAtMs:6,
   priority:"high",description:"Keep",dueDate:"2028-02-29"}
]};
// Both earlier formats are READABLE without an implicit write to disk.
for(const old of [old1,old2]){
  const raw=JSON.stringify(old);
  const upgraded=p.parse(raw);
  assert.equal(upgraded.ok,true);
  assert.equal(upgraded.document.version,3);
  assert.equal(upgraded.document.nextId,2);
  assert.equal(upgraded.document.nextProjectId,1);
  assert.equal(upgraded.document.projects.length,0);
  assert.equal(upgraded.document.tasks[0].projectId,null);
  assert.equal(upgraded.document.tasks[0].id,"t1");
  assert.equal(upgraded.document.tasks[0].createdAtMs,4);
  assert.equal(upgraded.document.tasks[0].updatedAtMs,6);
  assert.equal(JSON.stringify(old),raw); // no mutation
}
const m4=p.parse(JSON.stringify(old2)).document;
assert.equal(m4.tasks[0].priority,"high");
assert.equal(m4.tasks[0].description,"Keep");
assert.equal(m4.tasks[0].dueDate,"2028-02-29");

let doc=p.parse(JSON.stringify(old1)).document;
const first=p.createProject(doc," Apollo Work ",t);
assert.equal(first.ok,true);
assert.equal(doc.projects.length,0);
doc=first.document;
assert.equal(doc.version,3);
assert.equal(doc.projects[0].id,"p1");
assert.equal(doc.projects[0].name,"Apollo Work");
assert.equal(doc.nextProjectId,2);
assert.equal(p.createProject(doc,"apollo work",t+1).reason,"DUPLICATE_PROJECT_NAME");
assert.equal(p.createProject(doc,"",t+1).reason,"INVALID_PROJECT_NAME");
assert.equal(p.createProject(doc,"no\nnewline",t+1).reason,"INVALID_PROJECT_NAME");
assert.equal(p.createProject(doc,"a".repeat(65),t+1).reason,"INVALID_PROJECT_NAME");
doc=p.createProject(doc,"Household",t+2).document;
assert.equal(doc.projects[1].id,"p2");

const moved=p.assignProject(doc,"t1","p1",t+3);
assert.equal(moved.ok,true);
assert.equal(doc.tasks[0].projectId,null);
doc=moved.document;
assert.equal(doc.tasks[0].projectId,"p1");
assert.equal(p.assignProject(doc,"t1","p1",t+4).reason,"NO_CHANGE");
assert.equal(p.assignProject(doc,"t1","p999",t+4).reason,"UNKNOWN_PROJECT");
assert.equal(p.assignProject(doc,"missing","p1",t+4).reason,"UNKNOWN_ID");
assert.equal(p.assignProject(doc,"t1","p2",t-1).reason,"INVALID_TIME");
doc=p.update(doc,"t1","done",true,t+5,false).document;
doc=p.update(doc,"t1","rename","Renamed",t+6,false).document;
assert.equal(doc.tasks[0].projectId,"p1");

let view=p.view("ready",doc);
assert.equal(view.projects.length,2);
assert.equal(view.projects[0].total,1);
assert.equal(view.projects[0].completed,1);
assert.equal(view.projects[0].remaining,0);
assert.equal(view.projects[1].total,0);
assert.equal(view.items[0].projectId,"p1");
assert.equal(view.projects[0].name,"Apollo Work");
assert.equal(JSON.stringify(view).includes("createdAtMs"),false);
assert.equal(JSON.stringify(view).includes("nextProjectId"),false);
assert.equal(p.view("saving",doc).writable,false);
assert.equal(p.view("error",doc).projects.length,0);

doc=p.assignProject(doc,"t1",null,t+7).document;
assert.equal(doc.tasks[0].projectId,null);
const rt=p.parse(JSON.stringify(doc));
assert.equal(rt.ok,true);
assert.equal(rt.document.projects.length,2);
assert.equal(rt.document.tasks[0].projectId,null);
assert.equal(rt.document.nextProjectId,3);
assert.equal(p.validate({...doc,projects:[doc.projects[0],doc.projects[0]]}).reason,
             "DUPLICATE_PROJECT_ID");
assert.equal(p.validate({...doc,projects:[doc.projects[0],{
  ...doc.projects[1],name:"apollo work"
}]}).reason,"DUPLICATE_PROJECT_NAME");
assert.equal(p.validate({...doc,nextProjectId:2}).reason,"PROJECT_SEQUENCE_REWIND");
assert.equal(p.validate({...doc,tasks:[{...doc.tasks[0],projectId:"p404"}]}).reason,
             "UNKNOWN_PROJECT_REFERENCE");
assert.equal(p.parse(JSON.stringify({...doc,version:77})).reason,"UNSUPPORTED_VERSION");

const withoutExtra=p.parse(JSON.stringify({...doc,alien:"secret",projects:[
  {...doc.projects[0],token:"DO_NOT_EXPOSE"},doc.projects[1]
]})).document;
assert.equal(JSON.stringify(withoutExtra).includes("DO_NOT_EXPOSE"),false);
assert.equal(JSON.stringify(withoutExtra).includes("alien"),false);

const full=p.emptyDocument();
full.nextProjectId=32;
full.projects=Array.from({length:30},(_,i)=>({
  id:"p"+(i+1),name:"Project "+i,createdAtMs:1,updatedAtMs:1
}));
assert.equal(p.validate(full).ok,true);
assert.equal(p.createProject(full,"Overflow",t).reason,"PROJECT_CAPACITY");
assert.equal(p.validate({...full,projects:[...full.projects,full.projects[0]]}).reason,
             "INVALID_PROJECT_LIST");
console.log("TASKS M6 local Projects: v1/v2 compatibility and guarded assignments PASS");
