#!/usr/bin/env node
"use strict";
// M10f, disposable CI-only paths. No real TASKS or GitHub writer accessed.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const vm=require("node:vm");
const {spawnSync}=require("node:child_process");
const gate=require("./fixtures/single_writer_gate_fixture.cjs");
const js=fs.readFileSync("services/projects/OfflineOperationJournal.js","utf8")
    .replace(/^\.pragma library\s*$/m,"");
const p=vm.createContext({JSON,Array,Object,Number,String,RegExp});
vm.runInContext(js,p,{filename:"OfflineOperationJournal.js"});
const temp=fs.mkdtempSync(path.join(os.tmpdir(),"tasks-m10f-"));
const fixturePath=path.resolve("tests/tasks/fixtures/single_writer_gate_fixture.cjs");
function scenario(label) {
    const root=path.join(temp,label);
    fs.mkdirSync(root);
    const file=path.join(root,"state.json");
    const created=p.create([
        {id:"p1",name:"Local",family:"normal"},
        {id:"p2",name:"Linked",family:"git"}
    ],[
        {id:"t1",projectId:"p1",title:"Read",done:false,
            priority:"none",description:"",dueDate:null},
        {id:"t2",projectId:"p2",title:"Fix",done:false,
            priority:"none",description:"",dueDate:null}
    ]);
    assert.equal(created.ok,true);
    const original=p.encode(created.document);
    assert.equal(original.ok,true);
    fs.writeFileSync(file,original.raw);
    const edit=p.localEdit(created.document,
        {taskId:"t2",field:"title",value:"Fix offline",operationId:"op1"});
    assert.equal(edit.ok,true);
    return {file,base:created.document,next:edit.document,original:original.raw};
}
function otherProcess(file,mode) {
    const snippet=[
        "const lock=require(process.argv[1]);",
        "const acquired=lock.acquire(process.argv[2]);",
        "if(!acquired.ok) process.stdout.write(acquired.reason);",
        "else { process.stdout.write('ACQUIRED');",
        "if(process.argv[3]!=='abandon') lock.release(acquired.lease); }"
    ].join("\n");
    const child=spawnSync(process.execPath,
        ["-e",snippet,fixturePath,file,mode||"release"],
        {encoding:"utf8",timeout:8000});
    assert.equal(child.status,0,child.stderr);
    return child.stdout;
}
function injected(fn,stage) {
    assert.throws(fn,err=>err.message==="INJECTED_"+stage,stage);
}
try {
    const one=scenario("exclusive-owner");
    const lock=gate.acquire(one.file);
    assert.equal(lock.ok,true);
    const lease=lock.lease;
    assert.equal(otherProcess(one.file),"LOCK_HELD_OR_RECOVERY_REQUIRED");
    assert.equal(gate.acquire(one.file).reason,"LOCK_HELD_OR_RECOVERY_REQUIRED");
    const initial=gate.inspect(lease,p);
    assert.equal(initial.ok,true);
    assert.equal(initial.revision,0);
    const fake={...lease,token:"0".repeat(48)};
    assert.throws(()=>gate.inspect(fake,p),/LOCK_NOT_OWNED/);
    assert.throws(()=>gate.release(fake),/LOCK_NOT_OWNED/);
    assert.equal(gate.commit(lease,0,"0".repeat(64),one.next,p).reason,
        "STALE_SOURCE_HASH");
    assert.equal(gate.commit(lease,10,initial.sha256,one.next,p).reason,
        "STALE_REVISION");
    assert.equal(gate.commit(lease,0,null,one.next,p).reason,
        "EXPECTED_HASH_REQUIRED");
    const result=gate.commit(lease,0,initial.sha256,one.next,p);
    assert.equal(result.ok,true);
    assert.equal(result.revision,1);
    const after=gate.inspect(lease,p);
    assert.equal(after.document.tasks[1].title,"Fix offline");
    assert.equal(after.document.operations.length,1);
    assert.equal(after.document.operations[0].state,"PENDING");
    assert.equal(gate.commit(lease,0,initial.sha256,one.next,p).reason,
        "STALE_REVISION");
    assert.equal(otherProcess(one.file),"LOCK_HELD_OR_RECOVERY_REQUIRED");
    assert.equal(gate.release(lease).ok,true);
    assert.equal(otherProcess(one.file),"ACQUIRED");
    assert.throws(()=>gate.inspect(lease,p),/ENOENT/);

    // A process that dies owning the lock leaves an operator-review gate.
    const orphan=scenario("abandoned");
    assert.equal(otherProcess(orphan.file,"abandon"),"ACQUIRED");
    assert.equal(gate.acquire(orphan.file).reason,
        "LOCK_HELD_OR_RECOVERY_REQUIRED");

    for(const [stage,isNew] of [
        ["before-create",false],["after-write",false],
        ["after-file-sync",false],["before-rename",false],
        ["after-rename",true],["after-directory-sync",true]
    ]) {
        const s=scenario("stop-"+stage);
        const taken=gate.acquire(s.file);
        const before=gate.inspect(taken.lease,p);
        injected(()=>gate.commit(taken.lease,0,before.sha256,
            s.next,p,stage),stage);
        const observed=gate.inspect(taken.lease,p);
        assert.equal(observed.revision,isNew?1:0,stage);
        assert.equal(observed.document.operations.length,isNew?1:0,stage);
        assert.equal(observed.document.tasks[1].title,
            isNew?"Fix offline":"Fix",stage);
        assert.equal(otherProcess(s.file),"LOCK_HELD_OR_RECOVERY_REQUIRED");
        if(isNew)
            assert.equal(gate.commit(taken.lease,0,before.sha256,s.next,p).reason,
                "STALE_REVISION");
        assert.equal(gate.release(taken.lease).ok,true);
    }

    // Ambiguous SENDING writes become UNCERTAIN on restart, never ACK.
    const s=scenario("sending-recovery");
    const held=gate.acquire(s.file).lease;
    const base=gate.inspect(held,p);
    assert.equal(gate.commit(held,0,base.sha256,s.next,p).ok,true);
    const pending=gate.inspect(held,p);
    const sending=p.transition(pending.document,"op1","begin");
    assert.equal(sending.ok,true);
    injected(()=>gate.commit(held,1,pending.sha256,
        sending.document,p,"after-rename"),"after-rename");
    const ambiguous=gate.inspect(held,p);
    assert.equal(ambiguous.revision,2);
    assert.equal(ambiguous.document.operations[0].state,"SENDING");
    const recovered=p.recover(ambiguous.document);
    assert.equal(recovered.uncertainCount,1);
    assert.equal(gate.commit(held,2,ambiguous.sha256,
        recovered.document,p).ok,true);
    const last=gate.inspect(held,p);
    assert.equal(last.document.operations[0].state,"UNCERTAIN");
    assert.equal(p.nextIntent(last.document).reason,"UNCERTAIN_BLOCKED");
    gate.release(held);

    const local=scenario("normal-only");
    const lockLocal=gate.acquire(local.file).lease;
    const baseline=gate.inspect(lockLocal,p);
    const normal=p.localEdit(local.base,
        {taskId:"t1",field:"title",value:"Read tonight"});
    assert.equal(normal.remoteIntentCreated,false);
    assert.equal(gate.commit(lockLocal,0,baseline.sha256,normal.document,p).ok,true);
    assert.equal(gate.inspect(lockLocal,p).document.operations.length,0);
    gate.release(lockLocal);

    // Hash compare catches stale input even when revision number is unchanged.
    const mixed=scenario("non-cooperative");
    const heldMixed=gate.acquire(mixed.file).lease;
    const snap=gate.inspect(heldMixed,p);
    const alternative=JSON.parse(mixed.original);
    alternative.tasks[0].title="External change";
    fs.writeFileSync(mixed.file,JSON.stringify(alternative));
    assert.equal(gate.commit(heldMixed,0,snap.sha256,mixed.next,p).reason,
        "STALE_SOURCE_HASH");
    assert.equal(gate.inspect(heldMixed,p).document.tasks[0].title,
        "External change");
    gate.release(heldMixed);

    const corrupt=scenario("corrupt");
    const corruptionLease=gate.acquire(corrupt.file).lease;
    fs.writeFileSync(corrupt.file,"{invalid");
    assert.ok(gate.commit(corruptionLease,0,"0".repeat(64),
        corrupt.next,p).reason.startsWith("COMMITTED_"));
    assert.equal(fs.readFileSync(corrupt.file,"utf8"),"{invalid");
    gate.release(corruptionLease);
    console.log("TASKS M10f cross-process single-writer and crash-window tests: PASS");
} finally {
    fs.rmSync(temp,{recursive:true,force:true});
}
