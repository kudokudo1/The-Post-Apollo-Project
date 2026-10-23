#!/usr/bin/env node
"use strict";

// M10c uses ONLY disposable CI temp directories. It does not touch
// ~/.config, ~/.local, Quickshell.dataDir, GitHub, or production storage.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const vm=require("node:vm");
const fixture=require("./fixtures/atomic_envelope_fixture.cjs");
const code=fs.readFileSync("services/projects/OfflineOperationJournal.js","utf8")
    .replace(/^\.pragma library\s*$/m,"");
const policy=vm.createContext({JSON,Array,Object,Number,String,RegExp});
vm.runInContext(code,policy,{filename:"OfflineOperationJournal.js"});

const initial=policy.create([
    {id:"p1",name:"Personal",family:"normal"},
    {id:"p2",name:"Git Work",family:"git"}
],[
    {id:"t1",projectId:"p1",title:"Read",done:false,
        priority:"none",description:"",dueDate:null},
    {id:"t2",projectId:"p2",title:"Fix bug",done:false,
        priority:"none",description:"",dueDate:null}
]);
assert.equal(initial.ok,true);
const changed=policy.localEdit(initial.document,
    {taskId:"t2",field:"title",value:"Fix bug offline",operationId:"op1"});
assert.equal(changed.ok,true);
assert.equal(changed.document.revision,1);

const root=fs.mkdtempSync(path.join(os.tmpdir(),"pa-m10c-storage-"));
let cases=0;
function newCase() {
    const dir=path.join(root,"case-"+(++cases));
    fs.mkdirSync(dir);
    const file=path.join(dir,"tasks-and-queue.json");
    const baseline=policy.encode(initial.document);
    assert.equal(baseline.ok,true);
    fs.writeFileSync(file,baseline.raw,"utf8");
    return {dir,file};
}
try {
    const stages=[
        ["before-create",false],
        ["after-write",false],
        ["after-file-sync",false],
        ["after-rename",true],
        ["after-directory-sync",true]
    ];
    for(const [stage,observedNew] of stages) {
        const {dir,file}=newCase();
        assert.throws(()=>fixture.atomicReplace(file,changed.document,0,
            policy,stage),new RegExp("INJECTED_STOP_AT_"+stage));
        const loaded=fixture.readEnvelope(file,policy);
        assert.equal(loaded.ok,true,"source must remain parseable at "+stage);
        assert.equal(loaded.document.revision,observedNew?1:0,stage);
        const task=loaded.document.tasks.find(t=>t.id==="t2");
        const operations=loaded.document.operations;
        assert.equal(task.title,observedNew?"Fix bug offline":"Fix bug",stage);
        assert.equal(operations.length,observedNew?1:0,stage);
        // Orphan candidate files can exist after interrupted pre-rename
        // writes. The reader NEVER promotes them over the committed file.
        const reread=fixture.readEnvelope(file,policy);
        assert.equal(reread.document.revision,loaded.document.revision);
        const leftovers=fs.readdirSync(dir).filter(n=>n.includes(".m10c-"));
        assert.equal(leftovers.length,stage==="after-write"||
            stage==="after-file-sync"?1:0,stage);
    }

    const {file}=newCase();
    assert.equal(fixture.atomicReplace(file,changed.document,0,policy).ok,true);
    assert.equal(fixture.readEnvelope(file,policy).document.revision,1);
    const stale=fixture.atomicReplace(file,changed.document,0,policy);
    assert.equal(stale.ok,false);
    assert.equal(stale.reason,"STALE_REVISION");
    assert.equal(fixture.readEnvelope(file,policy).document.revision,1);

    // After committed SENDING, a restart must persist UNCERTAIN before any
    // dispatch is considered. No duplicate remote operation is produced.
    const sending=policy.transition(changed.document,"op1","begin");
    assert.equal(sending.ok,true);
    assert.equal(fixture.atomicReplace(file,sending.document,1,policy).ok,true);
    const loadedSending=fixture.readEnvelope(file,policy);
    assert.equal(loadedSending.document.operations[0].state,"SENDING");
    const recovered=policy.recover(loadedSending.document);
    assert.equal(recovered.uncertainCount,1);
    assert.equal(fixture.atomicReplace(file,recovered.document,
        loadedSending.document.revision,policy).ok,true);
    const afterRecovery=fixture.readEnvelope(file,policy).document;
    assert.equal(afterRecovery.operations.length,1);
    assert.equal(afterRecovery.operations[0].state,"UNCERTAIN");
    assert.equal(policy.nextIntent(afterRecovery).reason,"UNCERTAIN_BLOCKED");

    // NORMAL project changes survive, without introducing remote intents.
    const localChange=policy.localEdit(afterRecovery,
        {taskId:"t1",field:"title",value:"Read later"});
    assert.equal(localChange.ok,true);
    assert.equal(localChange.remoteIntentCreated,false);
    assert.equal(localChange.document.operations.length,1);
    assert.equal(fixture.atomicReplace(file,localChange.document,
        afterRecovery.revision,policy).ok,true);
    assert.equal(fixture.readEnvelope(file,policy).document.tasks[0].title,
        "Read later");

    // An invalid, unsupported or missing committed file must never be
    // replaced by empty storage through a recovery fallback.
    for(const bad of ["{incomplete",
        JSON.stringify({...initial.document,version:99})]) {
        const c=newCase();
        fs.writeFileSync(c.file,bad,"utf8");
        const before=fs.readFileSync(c.file,"utf8");
        const result=fixture.atomicReplace(c.file,changed.document,0,policy);
        assert.equal(result.ok,false);
        assert.ok(result.reason.startsWith("BASE_"));
        assert.equal(fs.readFileSync(c.file,"utf8"),before);
    }
    const absent=path.join(root,"missing","taskfile.json");
    assert.equal(fixture.readEnvelope(absent,policy).reason,
        "NO_COMMITTED_ENVELOPE");

    // Contrast: writing two separate files gives no automatic transaction.
    // A process interruption between writes causes model/queue disagreement.
    const split=path.join(root,"split");
    fs.mkdirSync(split);
    const modelFile=path.join(split,"model.json");
    const journalFile=path.join(split,"queue.json");
    fs.writeFileSync(modelFile,JSON.stringify({title:"Fix bug"}));
    fs.writeFileSync(journalFile,JSON.stringify([]));
    fs.writeFileSync(modelFile,JSON.stringify({title:"Fix bug offline"}));
    // Deliberately stop here, before updating queue.json.
    assert.equal(JSON.parse(fs.readFileSync(modelFile)).title,"Fix bug offline");
    assert.equal(JSON.parse(fs.readFileSync(journalFile)).length,0);

    // The test fixture must have no accidental production-path references.
    const fixtureCode=fs.readFileSync(
        "tests/tasks/fixtures/atomic_envelope_fixture.cjs","utf8");
    for(const forbidden of ["Quickshell.dataDir","ApolloHubTodoStore.qml",
            "gh project ","/var/home/","/home/mapple/"]) {
        assert.equal(fixtureCode.includes(forbidden),false,forbidden);
    }
    console.log("TASKS M10c disposable atomic-envelope interruption fixtures: PASS");
} finally {
    fs.rmSync(root,{recursive:true,force:true});
}
