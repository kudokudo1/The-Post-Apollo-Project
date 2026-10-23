#!/usr/bin/env node
"use strict";
// M10a contract is a READ-ONLY v3 projection, not a migration or sync engine.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const source = fs.readFileSync("services/projects/UnifiedProjectContract.js", "utf8")
    .replace(/^\.pragma library\s*$/m, "");
const context = vm.createContext({Array, Date, Number, Object, RegExp, String});
vm.runInContext(source, context, {filename:"UnifiedProjectContract.js"});

const validLink = {
    provider:"github", owner:"kudokudo1",
    projectNodeId:"PVT_verified_by_future_adapter_only", projectNumber:7
};
const candidate = {
    id:"p42", name:"Desktop", family:"git", remote:validLink
};
assert.equal(context.isGithubProjectReference(validLink), true);
const maybe = context.validateProjectCandidate(candidate);
assert.equal(maybe.ok, true);
assert.equal(maybe.reason, "REMOTE_ID_UNVERIFIED");
assert.equal(maybe.remoteVerified, false, "shape is NOT proof of remote identity");
assert.equal(context.validateProjectCandidate({
    id:"p42", name:"Desktop", family:"normal", remote:null
}).ok, true);

for (const malformed of [
    {id:"p42",name:"Desktop",family:"normal",remote:validLink},
    {id:"p42",name:"Desktop",family:"git",remote:null},
    {id:"p42",name:"Desktop",family:"git",remote:{...validLink,projectNodeId:""}},
    {id:"p42",name:"Desktop",family:"git",remote:{...validLink,projectNumber:0}},
    {id:"p42",name:"Desktop",family:"git",remote:{...validLink,owner:"user/group"}},
    {id:"p42",name:"Desktop",family:"git",remote:{...validLink,provider:"gitlab"}},
    {id:"p42",name:"Desktop",family:"normal",remote:undefined},
    {id:"p42",name:"Desktop",family:"unknown",remote:null},
    {id:"wrong",name:"Desktop",family:"normal",remote:null},
    {id:"p2",name:" ",family:"normal",remote:null}
]) {
    assert.equal(context.validateProjectCandidate(malformed).ok, false,
        JSON.stringify(malformed));
}

const currentV3Snapshot = {
    state:"ready",
    projects:[{id:"p1",name:"Personal",total:1,remaining:1}],
    items:[
        {id:"t1",title:"Read",done:false,projectId:"p1",description:"PRIVATE CONTENT"},
        {id:"t2",title:"Other",done:true,projectId:null,dueDate:"2026-10-23"}
    ]
};
const before = JSON.stringify(currentV3Snapshot);
const preview = context.previewV3(currentV3Snapshot);
assert.equal(preview.available, true);
assert.equal(preview.writeReady, false);
assert.equal(preview.projectCount, 1);
assert.equal(preview.taskCount, 2);
assert.equal(preview.projects[0].id, "p1");
assert.equal(preview.projects[0].family, "normal");
assert.equal(preview.projects[0].remote, null);
assert.equal(preview.projects[0].linked, false);
assert.equal(preview.tasks[0].id, "t1");
assert.equal(preview.tasks[0].projectId, "p1");
assert.equal(preview.tasks[1].projectId, null);
assert.equal(JSON.stringify(currentV3Snapshot), before, "never mutate snapshot");
assert.ok(!JSON.stringify(preview).includes("PRIVATE CONTENT"),
          "never copy description body into compatibility preview");

// Matching a title to a remote name cannot change NORMAL family.
const titleMatch = context.previewV3({
    state:"ready",
    projects:[{id:"p2",name:"GitHub Project"}],
    items:[]
});
assert.equal(titleMatch.projects[0].family, "normal");
assert.equal(titleMatch.projects[0].remote, null);

for (const state of ["loading","unsupported","error","offline","unavailable"]) {
    const result=context.previewV3({...currentV3Snapshot,state});
    assert.equal(result.available,false,state);
    assert.equal(result.writeReady,false,state);
    assert.equal(result.projectCount,0,state);
}
for (const invalid of [
    {state:"ready",projects:[],items:[{id:"t3",title:"Orphan",done:false,projectId:"p7"}]},
    {state:"ready",projects:[{id:"p1",name:"A"},{id:"p1",name:"B"}],items:[]},
    {state:"ready",projects:[{id:"p1",name:"A"}],items:[{id:"t1",title:"X",done:false},
        {id:"t1",title:"Y",done:false}]},
    {state:"ready",projects:null,items:[]},
    {state:"saving",projects:[],items:[{id:"t1",title:"Invalid",done:"false"}]},
    null
]) {
    assert.equal(context.previewV3(invalid).available,false,
                 JSON.stringify(invalid));
}
assert.equal(context.previewV3({state:"empty",projects:[],items:[]}).available,true);
assert.equal(context.previewV3({state:"saving",projects:[],items:[]}).writeReady,false);

for (const forbidden of [
    "FileView {", "Process {", "XMLHttpRequest", "XmlHttpRequest",
    "Quickshell.execDetached", "setText(", "gh project ",
    "ApolloHubTodoStore.", "ApolloHubTodoStore {", "GitHubProjectsService {", "localStorage",
    "require(", "fetch("
]) assert.ok(!source.includes(forbidden), "forbidden M10 side effect: " + forbidden);
console.log("Proxy 1 M10a project identity, v3 read compatibility, no writes: PASS");
