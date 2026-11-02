#!/usr/bin/env node
"use strict";
// TASKS M13c: isolated in-memory synthetic evidence and draft review tests.
// No real task data, production UI, source writes or credentials.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const crypto=require("node:crypto");
const root=path.resolve(__dirname,"../..");
const restart=require("./fixtures/TaskRestartReviewM13a.cjs");
const display=require("./fixtures/TaskRecoveryDisplayM13b.cjs");
const evidence=require("./fixtures/TaskRecoveryEvidenceM13c.cjs");
const sha=x=>crypto.createHash("sha256").update(x).digest("hex");
const copy=x=>JSON.parse(JSON.stringify(x));
function load(file) {
    const ctx=vm.createContext({unescape,encodeURIComponent});
    vm.runInContext(fs.readFileSync(path.join(root,file),"utf8")
                    .replace(/^\.pragma library\s*/,""),ctx,{timeout:1000,filename:file});
    return ctx;
}
const policy=load("services/hub/ApolloHubTodoPolicy.js");
const ticketContract=load("services/hub/TaskSaveTicketContractM12o.js");
const presenter=load("widgets/hub/TaskHubTicketPresenterM12p.js");
const view=d=>copy(policy.view(d.tasks.length?"ready":"empty",d,""));
function setup(surface="HUB",phase="RESERVED",sourceMode="candidate") {
    const baseline=policy.create(policy.emptyDocument(),"M13C_CONFIRMED",1000).document;
    const examples={
        HUB:{kind:"add",method:"addTask",value:{title:"HUB DRAFT"},
            mutate:()=>policy.create(baseline,"HUB DRAFT",2000)},
        DETAILS:{method:"updateTaskDetails",value:{description:"DETAILS DRAFT"},
            mutate:()=>policy.updateDetails(baseline,"t1","medium","DETAILS DRAFT",null,2000)},
        PLANNER:{method:"addTask",value:{title:"PLANNER DRAFT"},
            mutate:()=>policy.create(baseline,"PLANNER DRAFT",2000)},
        PROJECTS:{method:"createProject",value:{name:"PROJECTS DRAFT"},
            mutate:()=>policy.createProject(baseline,"PROJECTS DRAFT",2000)}
    };
    const info=examples[surface];
    assert.ok(info);
    const changed=info.mutate();
    assert.equal(changed.ok,true,JSON.stringify(changed));
    const stage=restart.make({policy,confirmed:baseline,candidate:changed.document,
        draft:{surface,method:info.method,value:info.value},
        sessionId:"M13cOldSession001",ownerEpoch:7,generation:3,
        sequence:1,phase});
    assert.equal(stage.ok,true,stage.reason);
    const raw=JSON.parse(stage.recordRaw);
    const sourceRaw=sourceMode==="candidate"?raw.expectedRaw
        :sourceMode==="before"?raw.beforeRaw
        :sourceMode==="missing"?null:"FOREIGN_SOURCE";
    const review=restart.reopen({recordRaw:stage.recordRaw,sourceRaw,policy,
        freshSessionId:"M13cNewSession002",freshEpoch:8});
    assert.equal(review.ok,true,review.reason);
    const ticketId="m12o-m13c-"+surface+"-ticket001";
    const ticket=ticketContract.begin(surface,info.method,ticketId,
        view(baseline),view(changed.document),info.value);
    assert.ok(ticket);
    const link={stageId:review.stageId,
        priorSessionId:review.priorSessionId,
        priorOwnerEpoch:review.priorOwnerEpoch,
        ticketId,surface,method:info.method};
    const pendingHub=surface==="HUB"?presenter.begin(ticketContract,info.kind,
        info.method,{admitted:true,ticketId,baseline:ticket.baseline,
                    expected:ticket.expected},ticket.baseline,info.value):undefined;
    const projected=display.project({review,ticket,link,contract:ticketContract,
        presenter,pendingHub});
    assert.equal(projected.ok,true,projected.reason);
    // Fake pinned evidence is independently constructed from the original
    // test stage BEFORE submitting a separate observation for validation.
    const pin={format:1,kind:"M13C_SEPARATE_FAKE_TEST_PIN",
        checkpointSha256:sha(stage.recordRaw),
        sourceSha256:sourceRaw===null?null:sha(sourceRaw),
        sourceMissing:sourceRaw===null,
        stageId:stage.stageId,priorSessionId:"M13cOldSession001",
        priorOwnerEpoch:7,freshEpoch:8,draftCapturedAtMs:1000000};
    const args={checkpointRaw:stage.recordRaw,sourceRaw,review,
        display:projected,pin,nowMs:1005000,reviewAfterMs:10000};
    return {args,stage,raw,projected};
}
function noAuthority(result) {
    assert.equal(result.writable,false);
    assert.equal(result.writeAuthorized,false);
    assert.equal(result.replayAuthorized,false);
    assert.equal(result.restoreAuthorized,false);
    assert.equal(result.clearDraftAuthorized,false);
    assert.equal(result.deleteDraftAuthorized,false);
    assert.equal(result.productionActivation,false);
    assert.equal(result.sourceTrusted,false);
}
for(const surface of ["HUB","DETAILS","PLANNER","PROJECTS"]) {
    for(const phase of ["RESERVED","SETTLED"]) {
        test(surface+"/"+phase+": separately pinned review retains confirmed row and draft",()=>{
            const s=setup(surface,phase);
            const result=evidence.evaluate(s.args);
            assert.equal(result.ok,true,result.reason);
            assert.equal(result.reason,"SYNTHETIC_PIN_MATCH_REVIEW_ONLY");
            assert.equal(result.mode,"RECOVERY_REVIEW");
            assert.equal(result.reviewUrgency,"REVIEW_RECENT");
            assert.equal(result.snapshot.items[0].title,"M13C_CONFIRMED");
            assert.equal(result.snapshot.state,"error");
            assert.equal(result.snapshot.writable,false);
            assert.equal(result.draftRetention,"HOLD_FOR_OPERATOR_REVIEW");
            assert.equal(result.draftPersistence,"NOT_APPROVED_FOR_PRODUCTION");
            assert.deepEqual(copy(result.draft),copy(s.projected.draft));
            noAuthority(result);
        });
    }
}
for(const sourceMode of ["candidate","before","missing","foreign"]) {
    test("source "+sourceMode+": no source classification promotes recovered data",()=>{
        const s=setup("HUB","SETTLED",sourceMode);
        const result=evidence.evaluate(s.args);
        assert.equal(result.ok,true,result.reason);
        assert.equal(result.sourceStatus,s.args.review.sourceStatus);
        assert.equal(result.snapshot.items[0].title,"M13C_CONFIRMED");
        noAuthority(result);
    });
}
test("older draft changes review urgency only, never expires/delete/clears",()=>{
    const s=setup("DETAILS");
    const recent=evidence.evaluate(s.args);
    const aged=evidence.evaluate({...s.args,nowMs:1010000});
    const overdue=evidence.evaluate({...s.args,nowMs:1800000});
    const rollback=evidence.evaluate({...s.args,nowMs:999999});
    assert.equal(recent.reviewUrgency,"REVIEW_RECENT");
    assert.equal(aged.reviewUrgency,"REVIEW_OVERDUE");
    assert.equal(overdue.reviewUrgency,"REVIEW_OVERDUE");
    assert.equal(rollback.reviewUrgency,"CLOCK_UNCERTAIN");
    for(const r of [recent,aged,overdue,rollback]) {
        assert.equal(r.draftRetention,"HOLD_FOR_OPERATOR_REVIEW");
        assert.deepEqual(copy(r.draft),copy(recent.draft));
        noAuthority(r);
    }
});
test("altered checkpoint and raw source are rejected against the independent fixture pin",()=>{
    const s=setup("HUB");
    const altered=[
        {checkpointRaw:s.args.checkpointRaw+" "},
        {checkpointRaw:s.args.checkpointRaw.replace("RESERVED","SETTLED")},
        {sourceRaw:s.args.sourceRaw+" "},
        {sourceRaw:null},
        {pin:{...s.args.pin,checkpointSha256:"0".repeat(64)}},
        {pin:{...s.args.pin,sourceSha256:"f".repeat(64)}},
        {pin:{...s.args.pin,sourceMissing:true}},
    ];
    for(const patch of altered) {
        const outcome=evidence.evaluate({...s.args,...patch});
        assert.equal(outcome.ok,false,JSON.stringify(patch).slice(0,80));
        noAuthority(outcome);
    }
});
test("no automatic authority when owner epoch, stage, source status or draft differs",()=>{
    const s=setup("PLANNER");
    const changed=[
        {pin:{...s.args.pin,stageId:"m13a-foreign-epoch-1"}},
        {pin:{...s.args.pin,freshEpoch:7}},
        {pin:{...s.args.pin,priorOwnerEpoch:99}},
        {review:{...s.args.review,stageId:"m13a-foreign-epoch-1"}},
        {review:{...s.args.review,sourceStatus:"SOURCE_MISSING"}},
        {review:{...s.args.review,writeAuthorized:true}},
        {display:{...s.args.display,draft:{title:"not the captured draft"}}},
        {display:{...s.args.display,clearDraftAuthorized:true}},
        {display:{...s.args.display,overlay:{
            ...s.args.display.overlay,items:[]}}},
    ];
    for(const patch of changed) {
        const outcome=evidence.evaluate({...s.args,...patch});
        assert.equal(outcome.ok,false);
        noAuthority(outcome);
    }
});
test("clock and arbitrary review threshold cannot silently delete or certify",()=>{
    const s=setup("PROJECTS");
    for(const input of [
        {reviewAfterMs:0},{reviewAfterMs:2592000001},
        {reviewAfterMs:3.5},{nowMs:-1},{nowMs:"later"}
    ]) {
        const result=evidence.evaluate({...s.args,...input});
        assert.equal(result.ok,false);
        noAuthority(result);
    }
    const r=evidence.evaluate({...s.args,reviewAfterMs:1});
    assert.equal(r.reviewUrgency,"REVIEW_OVERDUE");
    assert.equal(r.deleteDraftAuthorized,false);
    noAuthority(r);
});
test("M13c remains pure/unmounted and live TASKS gates remain closed",()=>{
    const m13c=fs.readFileSync(path.join(__dirname,
        "fixtures/TaskRecoveryEvidenceM13c.cjs"),"utf8");
    const store=fs.readFileSync(path.join(root,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(root,"shell.qml"),"utf8");
    assert.doesNotMatch(m13c,/\b(?:fs\.|openSync|writeFile|renameSync|spawnSync|setTimeout|FileView|Process\s*\{)/);
    assert.doesNotMatch(store+shell,/TaskRecoveryEvidenceM13c/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const flag of ["ticketProducerEnabled","guardedWriterEnabled",
        "independentlyAuthenticatedTicketReceipt"])
        assert.match(store,new RegExp("readonly property bool "+flag+":\\s*false"));
});
