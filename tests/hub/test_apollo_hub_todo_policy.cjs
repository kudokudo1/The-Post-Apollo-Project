#!/usr/bin/env node
"use strict";
// Execute production domain code, without QML or filesystem writes.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const script = fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubTodoPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const p = vm.createContext({});
vm.runInContext(script,p,{filename:"ApolloHubTodoPolicy.js"});
const t = 1000000;

let doc = p.emptyDocument();
assert.equal(p.validate(doc).ok,true);
assert.equal(p.view("empty",doc).writable,true);
assert.equal(p.view("loading",doc).writable,false);
assert.equal(p.view("error",doc,"INVALID_JSON").error,"INVALID_JSON");
assert.equal(p.view("unsupported",doc,"UNSUPPORTED_VERSION").writable,false);

const one=p.create(doc,"  Buy milk  ",t);
assert.equal(one.ok,true);
assert.equal(one.document.tasks[0].id,"t1");
assert.equal(one.document.tasks[0].title,"Buy milk");
assert.equal(one.document.tasks[0].createdAtMs,t);
assert.equal(one.document.tasks[0].updatedAtMs,t);
assert.equal(one.document.tasks[0].done,false);
assert.equal(doc.tasks.length,0); // immutable transition
assert.equal(one.document.nextId,2);
doc=one.document;
let second=p.create(doc,"Write notes",t+20);
assert.equal(second.ok,true);
assert.equal(second.document.tasks[1].id,"t2");
doc=second.document;
assert.equal(p.view("ready",doc).remaining,2);

const done=p.update(doc,"t2","done",true,t+30,false);
assert.equal(done.ok,true);
assert.equal(doc.tasks[1].done,false); // not mutated
doc=done.document;
assert.equal(p.view("ready",doc).completed,1);
assert.equal(p.view("ready",doc).remaining,1);
assert.equal(p.view("ready",doc).items[0].id,"t1");
assert.equal(p.view("ready",doc).items[1].id,"t2"); // completed last
assert.equal(p.update(doc,"t2","done",true,t+31,false).reason,"NO_CHANGE");
assert.equal(p.update(doc,"t2","done","true",t+31,false).reason,"INVALID_DONE");

const rename=p.update(doc,"t1","rename","  Buy milk and tea  ",t+40,false);
assert.equal(rename.ok,true);
assert.equal(rename.document.tasks[0].title,"Buy milk and tea");
assert.equal(doc.tasks[0].title,"Buy milk");
doc=rename.document;
assert.equal(p.update(doc,"t1","rename","  Buy milk and tea ",t+41,false).reason,"NO_CHANGE");
assert.equal(p.update(doc,"t1","rename","  ",t+41,false).reason,"INVALID_TITLE");
assert.equal(p.update(doc,"t1","rename","x".repeat(161),t+41,false).reason,"INVALID_TITLE");
assert.equal(p.update(doc,"t1","rename","new\nline",t+41,false).reason,"INVALID_TITLE");
assert.equal(p.update(doc,"t1","done",true,t+35,false).reason,"INVALID_TIME");
assert.equal(p.update(doc,"missing","rename","Hey",t+41,false).reason,"UNKNOWN_ID");
assert.equal(p.update(doc,"t1","unrecognized",null,t+41,false).reason,"INVALID_ACTION");

let noDelete=p.update(doc,"t1","delete",null,t+42,false);
assert.equal(noDelete.ok,false);
assert.equal(noDelete.reason,"CONFIRM_REQUIRED");
assert.equal(doc.tasks.length,2);
const removed=p.update(doc,"t1","delete",null,t+42,true);
assert.equal(removed.ok,true);
assert.equal(removed.document.tasks.length,1);
assert.equal(removed.document.nextId,3);
assert.equal(doc.tasks.length,2);
doc=removed.document;
assert.equal(p.create(doc,"Third",t+60).document.tasks[1].id,"t3");
// Deleting cannot re-use a historical ID after restart.

const roundtrip=p.parse(JSON.stringify(doc));
assert.equal(roundtrip.ok,true);
assert.equal(roundtrip.document.tasks[0].id,"t2");
assert.equal(p.validate(roundtrip.document).ok,true);
assert.equal(p.parse(JSON.stringify({version:9,nextId:1,tasks:[]})).reason,
             "UNSUPPORTED_VERSION");
assert.equal(p.parse("{bad").reason,"INVALID_JSON");
assert.equal(p.parse("").reason,"INVALID_FILE");
assert.equal(p.parse("x".repeat(1048577)).reason,"INVALID_FILE");
assert.equal(p.parse(JSON.stringify({version:1,nextId:1,tasks:[{
    id:"t1", title:"A",done:false,createdAtMs:1,updatedAtMs:1
}]})).reason,"SEQUENCE_REWIND");
assert.equal(p.parse(JSON.stringify({version:1,nextId:3,tasks:[
    {id:"t1",title:"A",done:false,createdAtMs:1,updatedAtMs:1},
    {id:"t1",title:"B",done:false,createdAtMs:1,updatedAtMs:1}
]})).reason,"DUPLICATE_ID");

for(const candidate of [
 {version:1,nextId:1,tasks:"bad"},
 {version:1,nextId:0,tasks:[]},
 {version:1,nextId:1,tasks:[{id:"t0",title:"Bad",done:false,createdAtMs:1,updatedAtMs:1}]},
 {version:1,nextId:2,tasks:[{id:"t1",title:"Bad",done:"false",createdAtMs:1,updatedAtMs:1}]},
 {version:1,nextId:2,tasks:[{id:"t1",title:"Bad",done:false,createdAtMs:9,updatedAtMs:7}]},
 {version:1,nextId:2,tasks:[{id:"t1",title:"Bad\n",done:false,createdAtMs:1,updatedAtMs:1}]},
 {version:1,nextId:2,tasks:[{id:"t1",title:"",done:false,createdAtMs:1,updatedAtMs:1}]},
 {version:1,nextId:2,tasks:[{id:"t1",title:"Bad ",done:false,createdAtMs:1,updatedAtMs:1}]},
 {version:1,nextId:2,tasks:[{id:"t1",title:"Bad",done:false,createdAtMs:1,updatedAtMs:1.2}]},
 {version:1,nextId:2,tasks:[{id:"t1",title:"Bad",done:false,createdAtMs:1,updatedAtMs:1}],unknown:true}
]) {
  if(candidate.unknown){ // Extra untrusted persisted keys are dropped on parsing.
    const result=p.parse(JSON.stringify(candidate));
    assert.equal(result.ok,true);
    assert.equal(JSON.stringify(result.document).includes("unknown"),false);
  } else assert.equal(p.parse(JSON.stringify(candidate)).ok,false);
}

const max=p.emptyDocument();
max.nextId=202;
max.tasks=Array.from({length:200},(_,i)=>({
    id:"t"+(i+1),title:"Task "+i,done:false,createdAtMs:1,updatedAtMs:1,\n    priority:"none", description:"", dueDate:null
}));
assert.equal(p.validate(max).ok,true);
assert.equal(p.create(max,"Overflow",t).reason,"CAPACITY");
assert.equal(p.parse(JSON.stringify({...max,tasks:[...max.tasks,max.tasks[0]]})).reason,
             "INVALID_TASK_LIST");

// Projection offers only list-scale display fields, no persisted write handle.
const stored={...doc,secret:"private",tasks:doc.tasks.map(task=>({
    ...task, exec:"dangerous",accountToken:"DO_NOT_EXPOSE"
}))};
const output=JSON.stringify(p.view("ready",stored));
for (const privateKey of ["DO_NOT_EXPOSE","private","exec","accountToken",
                         "createdAtMs","updatedAtMs","nextId","version"])
    assert.equal(output.includes(privateKey),false,privateKey);
assert.equal(p.view("saving",doc).writable,false);
assert.equal(p.view("unsupported",doc).items.length,0);
console.log("ApolloHub B7 To-do document, mutations, safety behavior tests passed");
