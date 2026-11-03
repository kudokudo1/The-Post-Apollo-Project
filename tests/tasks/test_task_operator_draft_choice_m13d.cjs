#!/usr/bin/env node
"use strict";
// M13d // Fake operator choices only. No UI actuation or real storage.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const crypto=require("node:crypto");
const ROOT=path.resolve(__dirname,"../..");
const restart=require("./fixtures/TaskRestartReviewM13a.cjs");
const display=require("./fixtures/TaskRecoveryDisplayM13b.cjs");
const evidence=require("./fixtures/TaskRecoveryEvidenceM13c.cjs");
const choices=require("./fixtures/TaskOperatorDraftChoiceM13d.cjs");
const sha=s=>crypto.createHash("sha256").update(s).digest("hex");
const copy=x=>JSON.parse(JSON.stringify(x));
function load(file) {
    const ctx=vm.createContext({unescape,encodeURIComponent});
    vm.runInContext(fs.readFileSync(path.join(ROOT,file),"utf8")
        .replace(/^\.pragma library\s*/,""),ctx,{timeout:1000,filename:file});
    return ctx;
}
const policy=load("services/hub/ApolloHubTodoPolicy.js");
const contract=load("services/hub/TaskSaveTicketContractM12o.js");
const presenter=load("widgets/hub/TaskHubTicketPresenterM12p.js");
const view=d=>copy(policy.view(d.tasks.length?"ready":"empty",d,""));
function setup(surface="HUB",phase="RESERVED",clock="recent") {
    const before=policy.create(policy.emptyDocument(),"M13D_CONFIRMED",1000).document;
    const variant={
        HUB:{kind:"add",method:"addTask",draft:{title:"HUB DRAFT"},
            change:()=>policy.create(before,"HUB DRAFT",2000)},
        DETAILS:{method:"updateTaskDetails",draft:{description:"DETAILS DRAFT"},
            change:()=>policy.updateDetails(before,"t1","medium","DETAILS DRAFT",null,2000)},
        PLANNER:{method:"addTask",draft:{title:"PLANNER DRAFT"},
            change:()=>policy.create(before,"PLANNER DRAFT",2000)},
        PROJECTS:{method:"createProject",draft:{name:"PROJECTS DRAFT"},
            change:()=>policy.createProject(before,"PROJECTS DRAFT",2000)}
    }[surface];
    assert.ok(variant);
    const result=variant.change();
    assert.equal(result.ok,true);
    const stage=restart.make({policy,confirmed:before,candidate:result.document,
        draft:{surface,method:variant.method,value:variant.draft},
        sessionId:"M13dOldSession001",ownerEpoch:7,generation:3,sequence:1,phase});
    assert.equal(stage.ok,true,stage.reason);
    const record=JSON.parse(stage.recordRaw),sourceRaw=record.expectedRaw;
    const review=restart.reopen({recordRaw:stage.recordRaw,sourceRaw,policy,
        freshSessionId:"M13dNewSession002",freshEpoch:8});
    assert.equal(review.ok,true,review.reason);
    const ticketId="m12o-m13d-"+surface+"-ticket001";
    const ticket=contract.begin(surface,variant.method,ticketId,
        view(before),view(result.document),variant.draft);
    assert.ok(ticket);
    const link={stageId:review.stageId,
        priorSessionId:review.priorSessionId,
        priorOwnerEpoch:review.priorOwnerEpoch,
        ticketId,surface,method:variant.method};
    const pendingHub=surface==="HUB"?presenter.begin(contract,variant.kind,
        variant.method,{admitted:true,ticketId,baseline:ticket.baseline,
            expected:ticket.expected},ticket.baseline,variant.draft):undefined;
    const projected=display.project({review,ticket,link,contract,presenter,pendingHub});
    assert.equal(projected.ok,true,projected.reason);
    const pin={format:1,kind:"M13C_SEPARATE_FAKE_TEST_PIN",
        checkpointSha256:sha(stage.recordRaw),sourceSha256:sha(sourceRaw),
        sourceMissing:false,stageId:stage.stageId,
        priorSessionId:"M13dOldSession001",priorOwnerEpoch:7,
        freshEpoch:8,draftCapturedAtMs:1000000};
    const nowMs=clock==="overdue"?1800000:clock==="rollback"?999999:1005000;
    const inspected=evidence.evaluate({checkpointRaw:stage.recordRaw,
        sourceRaw,review,display:projected,pin,nowMs,reviewAfterMs:10000});
    assert.equal(inspected.ok,true,inspected.reason);
    return inspected;
}
const choice=(review,action="KEEP",overrides={})=>({
    kind:"M13D_FAKE_OPERATOR_CHOICE",action,stageId:review.stageId,
    gestureId:"M13dFakeGesture0001",reviewDigest:choices.bindReview(review),
    selectedAtMs:1005000,...overrides
});
const second=(proposal,overrides={})=>({
    kind:"M13D_FAKE_SECOND_GESTURE",
    decisionId:proposal.decisionId,stageId:proposal.stageId,
    action:proposal.action,gestureId:"M13dFakeGesture0002",
    acknowledgedUncertainSave:true,scope:"DRAFT_ONLY",...overrides
});
function noPower(r) {
    for(const name of ["writeAuthorized","replayAuthorized",
        "restoreAuthorized","clearDraftAuthorized","deleteDraftAuthorized",
        "exportAuthorized","productionActivation","sourceTrusted"]) {
        assert.equal(r[name],false,name);
    }
}
for(const surface of ["HUB","DETAILS","PLANNER","PROJECTS"]) {
    for(const action of ["KEEP","EXPORT","DELETE"]) {
        test(surface+" / "+action+" returns intent only, retaining review draft",()=>{
            const review=setup(surface);
            const input=choice(review,action);
            const a=choices.select({review,choice:input});
            assert.equal(a.ok,true,a.reason);
            assert.equal(a.reason,"SYNTHETIC_CHOICE_ONLY");
            assert.equal(a.draftDisposition,"KEEP_DRAFT");
            assert.equal(a.proposal.action,action);
            assert.equal(a.proposal.stageId,review.stageId);
            assert.ok(!Object.hasOwn(a.proposal,"draft"));
            assert.ok(!Object.hasOwn(a.proposal,"snapshot"));
            noPower(a);
            if(action==="KEEP") {
                assert.equal(a.state,"KEEP_NOTED_FOR_REVIEW");
                const repeat=choices.confirm({review,proposal:a.proposal,
                    confirmation:second(a.proposal)});
                assert.equal(repeat.ok,false);
                noPower(repeat);
            } else {
                assert.match(a.state,/(HANDOFF_REVIEW_REQUIRED|SECOND_CONFIRMATION_REQUIRED)$/);
                const refused=choices.confirm({review,proposal:a.proposal});
                assert.equal(refused.ok,false);
                noPower(refused);
                const b=choices.confirm({review,proposal:a.proposal,
                    confirmation:second(a.proposal)});
                assert.equal(b.ok,true,b.reason);
                assert.equal(b.action,action);
                assert.equal(b.draftDisposition,"KEEP_DRAFT");
                assert.equal(b.externalExecutionRequired,true);
                noPower(b);
                // A repeat proposal/gesture has no actuation semantics.
                const repeat=choices.confirm({review,proposal:a.proposal,
                    confirmation:second(a.proposal)});
                assert.deepEqual(repeat,b);
                noPower(repeat);
            }
        });
    }
}
test("overdue and rollback may change review urgency but never automatically dispose",()=>{
    for(const clock of ["recent","overdue","rollback"]) {
        const review=setup("HUB","SETTLED",clock);
        const a=choices.select({review,choice:choice(review,"DELETE")});
        assert.equal(a.ok,true,a.reason);
        assert.equal(a.state,"DELETE_SECOND_CONFIRMATION_REQUIRED");
        const b=choices.confirm({review,proposal:a.proposal,
            confirmation:second(a.proposal)});
        assert.equal(b.ok,true,b.reason);
        assert.equal(b.state,"DELETE_AWAITING_EXTERNAL_AUTHORIZATION");
        noPower(a);noPower(b);
    }
});
test("foreign stage, forged review digest and undefined gesture cannot select",()=>{
    const review=setup("DETAILS");
    const bad=[
        choice(review,"PURGE"),
        choice(review,"DELETE",{stageId:"m13d-foreign-stage"}),
        choice(review,"EXPORT",{reviewDigest:"f".repeat(64)}),
        choice(review,"KEEP",{gestureId:"bad"}),
        choice(review,"KEEP",{kind:"M13D_REAL_OPERATOR"}),
        choice(review,"KEEP",{selectedAtMs:-1}),
        {...choice(review),unexpected:true}
    ];
    for(const selection of bad) {
        const out=choices.select({review,choice:selection});
        assert.equal(out.ok,false,JSON.stringify(selection));
        noPower(out);
    }
    for(const modified of [
        {...review,sourceTrusted:true},
        {...review,writeAuthorized:true},
        {...review,deleteDraftAuthorized:true},
        {...review,draftRetention:"DELETE_NOW"},
        {...review,mode:"READY"},
        {...review,stageId:"m13d-foreign-stage"}
    ]) {
        const out=choices.select({review:modified,choice:choice(review)});
        assert.equal(out.ok,false);
        noPower(out);
    }
});
test("confirmation must be separate, exact and restricted to uncertain DRAFT_ONLY",()=>{
    const review=setup("PROJECTS","SETTLED");
    const a=choices.select({review,choice:choice(review,"DELETE")});
    assert.equal(a.ok,true);
    const invalid=[
        second(a.proposal,{gestureId:a.proposal.gestureId}),
        second(a.proposal,{decisionId:"m13d-forged-0001"}),
        second(a.proposal,{action:"EXPORT"}),
        second(a.proposal,{stageId:"m13d-another-stage"}),
        second(a.proposal,{scope:"WHOLE_TASK_DATABASE"}),
        second(a.proposal,{acknowledgedUncertainSave:false}),
        second(a.proposal,{kind:"REAL_OPERATOR_PERMISSION"}),
        {...second(a.proposal),extra:true},
    ];
    for(const entry of invalid) {
        const b=choices.confirm({review,proposal:a.proposal,confirmation:entry});
        assert.equal(b.ok,false,JSON.stringify(entry));
        noPower(b);
    }
    const forged={...a.proposal,decisionId:"m13d-unmatched0001"};
    const rejected=choices.confirm({review,proposal:forged,
        confirmation:second(forged)});
    assert.equal(rejected.ok,false);
    noPower(rejected);
    const stale={...review,draft:{name:"OTHER"}};
    const staleOutcome=choices.confirm({review:stale,proposal:a.proposal,
        confirmation:second(a.proposal)});
    assert.equal(staleOutcome.ok,false);
    noPower(staleOutcome);
});
test("test-only source has no mutation API and live writer remains unchanged",()=>{
    const file=fs.readFileSync(path.join(__dirname,
        "fixtures/TaskOperatorDraftChoiceM13d.cjs"),"utf8");
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.doesNotMatch(file,/\b(?:fs\.|openSync|writeFile|unlinkSync|rmSync|renameSync|spawnSync|setTimeout|FileView|Process\s*\{)/);
    assert.doesNotMatch(store+shell,/TaskOperatorDraftChoiceM13d/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const flag of ["ticketProducerEnabled","guardedWriterEnabled",
        "independentlyAuthenticatedTicketReceipt"])
        assert.match(store,new RegExp("readonly property bool "+flag+":\\s*false"));
});
