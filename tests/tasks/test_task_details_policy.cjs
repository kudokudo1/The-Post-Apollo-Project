#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const src = fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubTodoPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(src, policy, {filename: "ApolloHubTodoPolicy.js"});
const t = 1000000;

// Read v1 into memory as v2, retain IDs/titles/done/timestamps, no file write.
const legacy = {version:1, nextId:3, tasks:[
    {id:"t1", title:"Legacy task", done:false, createdAtMs:100, updatedAtMs:120},
    {id:"t2", title:"Finished task", done:true, createdAtMs:110, updatedAtMs:130}
]};
const original = JSON.stringify(legacy);
const migrated = policy.parse(original);
assert.equal(migrated.ok,true);
assert.equal(migrated.document.version,2);
assert.equal(migrated.document.nextId,3);
assert.equal(migrated.document.tasks[0].id,"t1");
assert.equal(migrated.document.tasks[1].done,true);
assert.equal(migrated.document.tasks[0].createdAtMs,100);
assert.equal(migrated.document.tasks[0].updatedAtMs,120);
assert.equal(migrated.document.tasks[0].priority,"none");
assert.equal(migrated.document.tasks[0].description,"");
assert.equal(migrated.document.tasks[0].dueDate,null);
assert.equal(JSON.stringify(legacy),original);

let d = migrated.document;
const details = policy.updateDetails(d,"t1","high",
    "Paragraph one\nParagraph two", "2028-02-29", t);
assert.equal(details.ok,true);
assert.equal(d.tasks[0].priority,"none"); // immutable
d = details.document;
assert.equal(d.version,2);
assert.equal(d.tasks[0].priority,"high");
assert.equal(d.tasks[0].description,"Paragraph one\nParagraph two");
assert.equal(d.tasks[0].dueDate,"2028-02-29");
assert.equal(d.tasks[0].updatedAtMs,t);
assert.equal(policy.updateDetails(d,"t1","high",
    "Paragraph one\nParagraph two","2028-02-29",t+1).reason,"NO_CHANGE");
const projected=policy.view("ready",d);
assert.equal(projected.items[0].priority,"high");
assert.equal(projected.items[0].description,"Paragraph one\nParagraph two");
assert.equal(projected.items[0].dueDate,"2028-02-29");
for(const key of ["updatedAtMs","createdAtMs","nextId","version"])
    assert.equal(JSON.stringify(projected).includes(key),false);

for(const [p,note,date,reason] of [
    ["critical","",null,"INVALID_PRIORITY"],
    ["high","a".repeat(2001),null,"INVALID_DESCRIPTION"],
    ["high","bad\0text",null,"INVALID_DESCRIPTION"],
    ["high","", "2026-02-29","INVALID_DUE_DATE"],
    ["high","", "2026-04-31","INVALID_DUE_DATE"],
    ["high","", "2026-13-01","INVALID_DUE_DATE"],
    ["high","", "2026-2-1","INVALID_DUE_DATE"],
    ["high","", "0000-01-01","INVALID_DUE_DATE"],
    ["high","", undefined,"INVALID_DUE_DATE"]
]) {
    const invalid=policy.updateDetails(d,"t1",p,note,date,t+2);
    assert.equal(invalid.reason,reason);
}
assert.equal(policy.updateDetails(d,"t1","none","",null,t-1).reason,"INVALID_TIME");
assert.equal(policy.updateDetails(d,"missing","none","",null,t+2).reason,"UNKNOWN_ID");
assert.equal(policy.parse(JSON.stringify({...d, tasks:[
    {...d.tasks[0],priority:"unapproved"},d.tasks[1]
]})).reason,"INVALID_TASK");
assert.equal(policy.parse(JSON.stringify({...d, tasks:[
    {...d.tasks[0],dueDate:"2026-02-30"},d.tasks[1]
]})).reason,"INVALID_TASK");
assert.equal(policy.parse(JSON.stringify({...d,version:7})).reason,"UNSUPPORTED_VERSION");

// Rename/toggle preserve details, and round-trip preserves known fields.
d=policy.update(d,"t1","rename","Renamed",t+3,false).document;
d=policy.update(d,"t1","done",true,t+4,false).document;
assert.equal(d.tasks[0].priority,"high");
assert.equal(d.tasks[0].description,"Paragraph one\nParagraph two");
assert.equal(d.tasks[0].dueDate,"2028-02-29");
const rt=policy.parse(JSON.stringify(d));
assert.equal(rt.ok,true);
assert.equal(rt.document.tasks[0].priority,"high");
assert.equal(rt.document.tasks[0].description,"Paragraph one\nParagraph two");
assert.equal(rt.document.tasks[0].dueDate,"2028-02-29");

// Unknown keys are sanitized on parse, not passed to a UI or serialized.
const untrusted={...d, extraRoot:"secret", tasks:d.tasks.map(t=>({
    ...t, externalCommand:"never", privateToken:"DO_NOT_EXPOSE"
}))};
const cleaned=policy.parse(JSON.stringify(untrusted));
assert.equal(cleaned.ok,true);
for(const bad of ["extraRoot","externalCommand","privateToken","DO_NOT_EXPOSE"])
    assert.equal(JSON.stringify(cleaned.document).includes(bad),false);
assert.equal(policy.view("saving",d).writable,false);
assert.equal(policy.view("unsupported",d).items.length,0);

console.log("TASKS v2 details policy + v1 compatibility: PASS");
