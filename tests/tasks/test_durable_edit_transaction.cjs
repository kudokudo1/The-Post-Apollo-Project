#!/usr/bin/env node
"use strict";
// M10i synthetic/throwaway integration exercise, no live files or network.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const vm=require("node:vm");
const txn=require("./fixtures/durable_edit_transaction_fixture.cjs");
const js=fs.readFileSync("services/projects/UnifiedProjectModelV2.js","utf8")
    .replace(/^\.pragma library\s*$/m,"");
const model=vm.createContext({JSON,Object,Array,Number,String,RegExp,Date,Math});
vm.runInContext(js,model,{filename:"UnifiedProjectModelV2.js"});
const root=fs.mkdtempSync(path.join(os.tmpdir(),"pa-m10i-fixtures-"));
const at=1700000000000;
let serial=0;
function scenario() {
    const dir=path.join(root,String(++serial));
    fs.mkdirSync(dir);
    const file=path.join(dir,"candidate-envelope.json");
    const baseline=model.empty();
    baseline.projects=[
        {id:"p1",name:"Personal",family:"normal",remote:null,
         createdAtMs:at,updatedAtMs:at,fields:[]},
        {id:"p2",name:"Git Planning",family:"git",
         remote:{provider:"github",owner:"kudokudo1",
            projectNodeId:"PVT_unverified_identity",projectNumber:12},
         createdAtMs:at,updatedAtMs:at,
         fields:[{id:"f1",label:"Research",kind:"text",scope:"local"}]}
    ];
    baseline.tasks=[
        {id:"t1",title:"Read",done:false,projectId:"p1",remote:null,
         createdAtMs:at,updatedAtMs:at,priority:"none",
         description:"",dueDate:null,values:{}},
        {id:"t2",title:"Build widget",done:false,projectId:"p2",remote:null,
         createdAtMs:at,updatedAtMs:at,priority:"high",
         description:"Keep offline",dueDate:"2026-10-23",
         values:{f1:"Do not send to GitHub"}}
    ];
    baseline.nextId=3;baseline.nextProjectId=3;baseline.nextOperationId=1;
    assert.equal(model.verify(baseline).ok,true);
    const encoded=model.encode(baseline);
    assert.equal(encoded.ok,true);
    fs.writeFileSync(file,encoded.raw);
    return {file,baseline,original:encoded.raw};
}
function locked(s) {
    const taken=txn.acquire(s.file);
    assert.equal(taken.ok,true);
    const first=txn.inspect(taken.lease,model);
    assert.equal(first.ok,true);
    return {lease:taken.lease,first};
}
function editTask(id,field,value,when) {
    return {kind:"task",request:{taskId:id,field,value,nowMs:when}};
}
try {
    const sample=scenario(), {lease,first}=locked(sample);
    const pre=JSON.stringify(first.document);
    const r=txn.transact(lease,first,editTask("t2","title",
        "Build widget offline",at+1),model);
    assert.equal(r.ok,true,r.reason);
    assert.equal(r.status,"LOCAL_COMMITTED");
    assert.equal(r.localSaved,true);
    assert.equal(r.remoteSent,false);
    assert.equal(r.remoteWriteAuthorized,false);
    assert.equal(r.remoteIntentCreated,true);
    assert.equal(r.revision,1);
    const committed=txn.inspect(lease,model);
    assert.equal(committed.ok,true);
    assert.equal(committed.revision,1);
    assert.equal(committed.document.tasks[1].title,"Build widget offline");
    assert.equal(committed.document.tasks[1].updatedAtMs,at+1);
    assert.equal(committed.document.tasks[1].values.f1,
        "Do not send to GitHub");
    assert.equal(committed.document.operations.length,1);
    assert.equal(committed.document.operations[0].id,"op1");
    assert.equal(committed.document.operations[0].field,"title");
    assert.equal(committed.document.operations[0].state,"PENDING");
    assert.equal(committed.document.nextOperationId,2);
    assert.equal(JSON.stringify(first.document),pre);
    assert.equal(txn.transact(lease,first,
        editTask("t2","done",true,at+2),model).reason,"STALE_REVISION");
    const next=txn.transact(lease,committed,
        editTask("t2","priority","medium",at+2),model);
    assert.equal(next.ok,true);
    assert.equal(txn.inspect(lease,model).document.operations[1].id,"op2");
    assert.equal(txn.inspect(lease,model).document.nextOperationId,3);
    assert.equal(txn.release(lease).ok,true);

    // NORMAL task edits and local GIT custom values remain local-only.
    const s2=scenario(),lock2=locked(s2);
    const normal=txn.transact(lock2.lease,lock2.first,
        editTask("t1","done",true,at+1),model);
    assert.equal(normal.ok,true);
    assert.equal(normal.remoteIntentCreated,false);
    let snap=txn.inspect(lock2.lease,model);
    assert.equal(snap.document.operations.length,0);
    const custom=txn.transact(lock2.lease,snap,
        {kind:"custom",request:{taskId:"t2",fieldId:"f1",
            value:"Offline notes",nowMs:at+2}},model);
    assert.equal(custom.ok,true);
    assert.equal(custom.remoteIntentCreated,false);
    assert.equal(txn.inspect(lock2.lease,model).document.tasks[1].values.f1,
        "Offline notes");
    assert.equal(txn.inspect(lock2.lease,model).document.operations.length,0);
    txn.release(lock2.lease);

    // Project edits also preserve model timestamps and do not sync by accident.
    const s3=scenario(),lock3=locked(s3);
    const renamed=txn.transact(lock3.lease,lock3.first,
        {kind:"project-rename",request:{projectId:"p1",
            name:"Home",nowMs:at+3}},model);
    assert.equal(renamed.ok,true,renamed.reason);
    let current=txn.inspect(lock3.lease,model);
    assert.equal(current.document.projects[0].updatedAtMs,at+3);
    assert.equal(current.document.projects[0].name,"Home");
    const field=txn.transact(lock3.lease,current,
        {kind:"field-create",request:{projectId:"p2",
            label:"Cost",kind:"number",nowMs:at+3}},model);
    assert.equal(field.ok,true,field.reason);
    assert.equal(field.remoteIntentCreated,false);
    current=txn.inspect(lock3.lease,model);
    assert.equal(current.document.projects[1].fields[1].label,"Cost");
    assert.equal(current.document.operations.length,0);
    assert.equal(txn.transact(lock3.lease,current,
        {kind:"unknown",request:{}},model).reason,"EDIT_UNKNOWN_COMMAND");
    txn.release(lock3.lease);

    // All interruption points require explicit reconciliation, not replay.
    for (const [point,applied] of [
        ["before-create",false],["after-write",false],
        ["after-file-sync",false],["before-rename",false],
        ["after-rename",true],["after-directory-sync",true]
    ]) {
        const specimen=scenario(),lockedSpec=locked(specimen);
        const uncertain=txn.transact(lockedSpec.lease,lockedSpec.first,
            editTask("t2","title","Interrupted edit",at+5),model,point);
        assert.equal(uncertain.ok,false,point);
        assert.equal(uncertain.reason,"COMMIT_UNCERTAIN",point);
        assert.equal(uncertain.localSaved,false,point);
        assert.equal(uncertain.remoteSent,false,point);
        const observed=txn.reconcile(lockedSpec.lease,uncertain.intent,model);
        assert.equal(observed.ok,true,point);
        assert.equal(observed.status,applied
            ? "LOCAL_COMMIT_OBSERVED":"LOCAL_COMMIT_NOT_APPLIED",point);
        const disk=txn.inspect(lockedSpec.lease,model).document;
        assert.equal(disk.tasks[1].title,applied
            ?"Interrupted edit":"Build widget",point);
        assert.equal(disk.operations.length,applied?1:0,point);
        assert.equal(disk.nextOperationId,applied?2:1,point);
        assert.equal(txn.release(lockedSpec.lease).ok,true);
    }

    // Unknown state (unrelated noncooperative change) must block resolution.
    const s4=scenario(),l4=locked(s4);
    const ambiguous=txn.transact(l4.lease,l4.first,
        editTask("t2","title","Intended",at+1),model,"before-rename");
    assert.equal(ambiguous.reason,"COMMIT_UNCERTAIN");
    const alternate=JSON.parse(s4.original);
    alternate.tasks[0].title="Third-party rewrite";
    fs.writeFileSync(s4.file,JSON.stringify(alternate));
    assert.equal(txn.reconcile(l4.lease,ambiguous.intent,model).reason,
        "UNKNOWN_OR_CONFLICTING_LOCAL_STATE");
    txn.release(l4.lease);

    // An invalid or unknown version is never replaced or treated as empty.
    const s5=scenario(),l5=locked(s5);
    fs.writeFileSync(s5.file,JSON.stringify({...s5.baseline,version:999}));
    const beforeInvalid=fs.readFileSync(s5.file,"utf8");
    assert.ok(txn.transact(l5.lease,l5.first,
        editTask("t2","done",true,at+1),model).reason.startsWith(
            "UNREADABLE_SOURCE_"));
    assert.equal(fs.readFileSync(s5.file,"utf8"),beforeInvalid);
    txn.release(l5.lease);

    // Policies do not enable a remote executor or live desktop writer.
    const fixture=fs.readFileSync(
        "tests/tasks/fixtures/durable_edit_transaction_fixture.cjs","utf8");
    for (const prohibited of [
        "ApolloHubTodoStore.qml","Quickshell.dataDir","gh project ",
        "GitHubProjectsService.qml","/var/home/mapple/","process.env.HOME"
    ]) assert.equal(fixture.includes(prohibited),false,prohibited);
    console.log("TASKS M10i v2 local+journal transaction & reconciliation: PASS");
} finally {
    fs.rmSync(root,{recursive:true,force:true});
}
