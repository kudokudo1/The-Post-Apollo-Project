#!/usr/bin/env node
"use strict";
// Real production policy executed without QML, disk or network.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const code = fs.readFileSync(path.join(__dirname,
  "../../services/hub/ApolloHubTodoPolicy.js"), "utf8")
  .replace(/^\.pragma library\s*/m, "");
const p = vm.createContext({});
vm.runInContext(code, p, {filename:"ApolloHubTodoPolicy.js"});

const t = 1000000;
let d = p.create(p.emptyDocument(), "Keep my task", t).document;
d = p.create(d, "Unrelated task", t+1).document;
d = p.createProject(d, "Post Apollo", t+2).document;
d = p.createProject(d, "Another", t+3).document;
d = p.assignProject(d, "t1", "p1", t+4).document;
d = p.updateDetails(d, "t1", "urgent", "Keep this description",
                    "2028-02-29", t+5).document;
const original=JSON.stringify(d);
const initialId=d.projects[0].id;
const oldProjectCreated=d.projects[0].createdAtMs;
const oldNextProjectId=d.nextProjectId;

assert.equal(p.renameProject(d,"p1"," Post Apollo v2 ",t+6).ok,true);
assert.equal(JSON.stringify(d),original);  // all pure operations
assert.equal(p.renameProject(d,"p1","Post Apollo",t+6).reason,"NO_CHANGE");
assert.equal(p.renameProject(d,"missing","Other",t+6).reason,"UNKNOWN_PROJECT");
assert.equal(p.renameProject(d,"p1","",t+6).reason,"INVALID_PROJECT_NAME");
assert.equal(p.renameProject(d,"p1","bad\nnewline",t+6).reason,"INVALID_PROJECT_NAME");
assert.equal(p.renameProject(d,"p1","x".repeat(65),t+6).reason,"INVALID_PROJECT_NAME");
assert.equal(p.renameProject(d,"p1","another",t+6).reason,"DUPLICATE_PROJECT_NAME");
assert.equal(p.renameProject(d,"p1","New",t-1).reason,"INVALID_TIME");
d = p.renameProject(d,"p1"," Post Apollo v2 ",t+6).document;
assert.equal(d.projects[0].id,initialId);
assert.equal(d.projects[0].name,"Post Apollo v2");
assert.equal(d.projects[0].createdAtMs,oldProjectCreated);
assert.equal(d.projects[0].updatedAtMs,t+6);
assert.equal(d.nextProjectId,oldNextProjectId);
assert.equal(d.tasks[0].projectId,initialId);
assert.equal(d.tasks[0].priority,"urgent");
assert.equal(d.tasks[0].dueDate,"2028-02-29");
assert.equal(p.renameProject(d,"p1","POST APOLLO V2",t+7).ok,true);

const beforeDelete=JSON.stringify(d);
assert.equal(p.deleteProject(d,"p1",t+7,false).reason,"CONFIRM_REQUIRED");
assert.equal(p.deleteProject(d,"p1",t+7).reason,"CONFIRM_REQUIRED");
assert.equal(p.deleteProject(d,"p99",t+7,true).reason,"UNKNOWN_PROJECT");
assert.equal(p.deleteProject(d,"p1",t+4,true).reason,"INVALID_TIME");
assert.equal(JSON.stringify(d),beforeDelete);
const deleted=p.deleteProject(d,"p1",t+8,true);
assert.equal(deleted.ok,true);
assert.equal(JSON.stringify(d),beforeDelete);
const after=deleted.document;
assert.equal(after.projects.length,1);
assert.equal(after.projects[0].id,"p2");
assert.equal(after.nextProjectId,oldNextProjectId);
assert.equal(after.tasks.length,d.tasks.length); // never delete tasks
assert.equal(after.tasks[0].id,"t1");
assert.equal(after.tasks[0].projectId,null);
assert.equal(after.tasks[0].updatedAtMs,t+8);
assert.equal(after.tasks[0].title,"Keep my task");
assert.equal(after.tasks[0].priority,"urgent");
assert.equal(after.tasks[0].description,"Keep this description");
assert.equal(after.tasks[0].dueDate,"2028-02-29");
assert.equal(after.tasks[0].createdAtMs,t);
assert.equal(after.tasks[0].done,false);
assert.equal(after.tasks[1].projectId,null);
assert.equal(after.tasks[1].updatedAtMs,t+1); // unrelated unchanged
assert.equal(p.validate(after).ok,true);
assert.equal(p.parse(JSON.stringify(after)).ok,true);
const view=p.view("ready",after);
assert.equal(view.projects.some(x=>x.id==="p1"),false);
assert.equal(view.items.length,2);
assert.equal(view.items[0].projectId,null);
assert.equal(JSON.stringify(view).includes("createdAtMs"),false);
const newProject=p.createProject(after,"Reused name",t+9);
assert.equal(newProject.document.projects[1].id,"p3"); // never reuse removed ID

// Refuse deletion entirely if the clock precedes any affected task edit.
const futureDoc=p.updateDetails(d,"t1","urgent","Updated again",
                                "2028-02-29",t+20).document;
assert.equal(p.deleteProject(futureDoc,"p1",t+15,true).reason,"INVALID_TIME");
assert.equal(futureDoc.tasks[0].projectId,"p1");
assert.equal(futureDoc.projects.length,2);

// Older documents cannot contain projects: policy rejects unknown ones.
const oldV2={version:2,nextId:2,tasks:[{
    id:"t1",title:"Legacy",done:false,createdAtMs:1,updatedAtMs:1,
    priority:"none",description:"",dueDate:null
}]};
assert.equal(p.renameProject(oldV2,"p1","Nope",t).reason,"UNKNOWN_PROJECT");
assert.equal(p.deleteProject(oldV2,"p1",t,true).reason,"UNKNOWN_PROJECT");
assert.equal(p.parse(JSON.stringify(oldV2)).document.projects.length,0);

// An unsupported or corrupted project reference fails closed.
const invalid={...d,projects:[...d.projects],tasks:d.tasks.map(t=>({...t}))};
invalid.projects.shift();
assert.equal(p.validate(invalid).reason,"UNKNOWN_PROJECT_REFERENCE");
console.log("TASKS PROJECTS rename / confirmed detach-delete and legacy guards: PASS");
