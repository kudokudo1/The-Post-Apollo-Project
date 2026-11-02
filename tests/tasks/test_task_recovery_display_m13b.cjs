#!/usr/bin/env node
"use strict";
// M13b // synthetic composition of existing M13a/M12o/M12p contracts only.
// Zero native QML, filesystem writes, user drafts or production activation.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const project=require("./fixtures/TaskRecoveryDisplayM13b.cjs").project;
const m13a=require("./fixtures/TaskRestartReviewM13a.cjs");
const copy=x=>JSON.parse(JSON.stringify(x));
function load(file) {
    const context=vm.createContext({unescape,encodeURIComponent});
    vm.runInContext(fs.readFileSync(path.join(ROOT,file),"utf8")
        .replace(/^\.pragma library\s*/,""),context,{filename:file,timeout:1000});
    return context;
}
const policy=load("services/hub/ApolloHubTodoPolicy.js");
const contract=load("services/hub/TaskSaveTicketContractM12o.js");
const presenter=load("widgets/hub/TaskHubTicketPresenterM12p.js");
function view(doc) {
    return copy(policy.view(doc.tasks.length?"ready":"empty",doc,""));
}
function sample(surface,phase="RESERVED",sourceCase="candidate") {
    const before=policy.create(policy.emptyDocument(),"M13B_CONFIRMED",1000).document;
    const entry={
        HUB:{kind:"add",method:"addTask",
            change:()=>policy.create(before,"M13B_HUB_DRAFT",1200),
            draft:{title:"M13B_HUB_DRAFT"}},
        DETAILS:{method:"updateTaskDetails",
            change:()=>policy.updateDetails(before,"t1","high","M13B_DETAILS_DRAFT",null,1200),
            draft:{taskId:"t1",description:"M13B_DETAILS_DRAFT"}},
        PLANNER:{method:"addTask",
            change:()=>policy.create(before,"M13B_PLANNER_DRAFT",1200),
            draft:{title:"M13B_PLANNER_DRAFT",dueDate:"2026-11-04"}},
        PROJECTS:{method:"createProject",
            change:()=>policy.createProject(before,"M13B_PROJECT_DRAFT",1200),
            draft:{name:"M13B_PROJECT_DRAFT"}}
    }[surface];
    assert.ok(entry);
    const mutation=entry.change();
    assert.equal(mutation.ok,true,JSON.stringify(mutation));
    const candidate=mutation.document;
    const v0=view(before),v1=view(candidate);
    const ticketId="m12o-m13b-"+surface+"-ticket001";
    const draft=copy(entry.draft);
    const ticket=contract.begin(surface,entry.method,ticketId,v0,v1,draft);
    assert.ok(ticket);
    const checkpoint=m13a.make({policy,confirmed:before,candidate,
        draft:{surface,method:entry.method,value:draft},
        sessionId:"M13bOwnerOld012",ownerEpoch:5,generation:2,sequence:1,phase});
    assert.equal(checkpoint.ok,true,checkpoint.reason);
    const raw=JSON.parse(checkpoint.recordRaw);
    const sourceRaw=sourceCase==="candidate"?raw.expectedRaw
        :sourceCase==="before"?raw.beforeRaw
        :sourceCase==="missing"?null:"OUTSIDE_SOURCE";
    const review=m13a.reopen({recordRaw:checkpoint.recordRaw,
        sourceRaw,policy,freshSessionId:"M13bOwnerNew034",freshEpoch:6});
    assert.equal(review.ok,true,review.reason);
    const link={stageId:review.stageId,priorSessionId:review.priorSessionId,
        priorOwnerEpoch:review.priorOwnerEpoch,
        ticketId,surface,method:entry.method};
    const pendingHub=surface==="HUB"
        ?presenter.begin(contract,entry.kind,entry.method,
           {admitted:true,ticketId,baseline:v0,expected:v1},v0,draft)
        :undefined;
    if(surface==="HUB")assert.ok(pendingHub);
    return {review,ticket,link,pendingHub,before,candidate,sourceRaw,
        input:{review,ticket,link,contract,presenter,pendingHub}};
}
function assertSafe(result) {
    assert.equal(result.writeAuthorized,false);
    assert.equal(result.replayAuthorized,false);
    assert.equal(result.restoreAuthorized,false);
    assert.equal(result.clearDraftAuthorized,false);
}
for(const surface of ["HUB","DETAILS","PLANNER","PROJECTS"]) {
    for(const phase of ["RESERVED","SETTLED"]) {
        test(surface+"/"+phase+": last confirmed rows remain read-only and draft retained",()=>{
            const s=sample(surface,phase);
            const beforeTicket=copy(s.ticket);
            const beforeReview=copy(s.review);
            const result=project(s.input);
            assert.equal(result.ok,true,result.reason);
            assert.equal(result.mode,"READ_ONLY_RECOVERY");
            assert.equal(result.effect,"KEEP_DRAFT_FINAL");
            assert.equal(result.overlay.state,"error");
            assert.equal(result.overlay.error,"RECOVERY_REVIEW");
            assert.equal(result.overlay.writable,false);
            assert.equal(result.overlay.items.length,1);
            assert.equal(result.overlay.items[0].title,"M13B_CONFIRMED");
            assert.equal(result.overlay.total,1);
            assert.equal(result.overlay.remaining,1);
            assert.equal(result.overlay.completed,0);
            assert.equal(result.ticket.state,"REVIEW_REQUIRED");
            assert.equal(result.ticket.disposition,"KEEP_DRAFT");
            assert.equal(result.ticket.ticketId,s.ticket.ticketId);
            assert.deepEqual(result.draft,s.ticket.draft);
            assertSafe(result);
            assert.equal(result.productionActivation,false);
            assert.deepEqual(copy(s.ticket),beforeTicket);
            assert.deepEqual(copy(s.review),beforeReview);
            // Once the old ticket reaches terminal REVIEW_REQUIRED, late
            // claimed completion cannot erase draft or promote candidate.
            const late=contract.reconcile(result.ticket,{
                ticketId:s.ticket.ticketId,state:"CONFIRMED",
                evidence:"SYNTHETIC_READBACK_RECEIPT"
            },view(s.candidate));
            assert.equal(late.state,"REVIEW_REQUIRED");
            assert.equal(late.disposition,"KEEP_DRAFT");
        });
    }
}
for(const sourceCase of ["before","candidate","missing","foreign"]) {
    test("source "+sourceCase+": recovery display never upgrades even with SETTLED",()=>{
        const s=sample("HUB","SETTLED",sourceCase);
        const result=project(s.input);
        assert.equal(result.ok,true,result.reason);
        assert.equal(result.sourceStatus,s.review.sourceStatus);
        assert.equal(result.overlay.items[0].title,"M13B_CONFIRMED");
        assert.equal(result.overlay.writable,false);
        assertSafe(result);
    });
}
test("mismatched stage-ticket association or foreign ticket cannot clear another draft",()=>{
    const a=sample("HUB"),b=sample("HUB");
    const alternate={...b.link,ticketId:"m12o-m13b-HUB-foreign0002"};
    const bad=[
        {...a.link,stageId:"m13b-fake-foreign"},
        {...a.link,priorSessionId:"DifferentOwner01"},
        {...a.link,priorOwnerEpoch:99},
        {...a.link,ticketId:"m12o-m13b-HUB-foreign0002"},
        {...a.link,surface:"DETAILS"},
        {...a.link,method:"renameTask"},
        alternate
    ];
    for(const link of bad) {
        const outcome=project({...a.input,link});
        assert.equal(outcome.ok,false);
        assertSafe(outcome);
    }
    const foreignTicket=copy(a.ticket);foreignTicket.ticketId="m12o-m13b-HUB-foreign0002";
    const other=project({...a.input,ticket:foreignTicket});
    assert.equal(other.ok,false);
    assertSafe(other);
});
test("wrong baseline, missing draft, switched method and malformed counts fail closed",()=>{
    const a=sample("DETAILS");
    const wrong=[
        {ticket:{...a.ticket,baseline:{...a.ticket.baseline,total:99}}},
        {ticket:{...a.ticket,draft:{description:"Other"}}},
        {ticket:{...a.ticket,method:"renameTask"}},
        {review:{...a.review,items:[]}},
        {review:{...a.review,items:[{...a.review.items[0],title:"forged"}]}},
        {review:{...a.review,draft:{...a.review.draft,surface:"HUB"}}},
        {review:{...a.review,writable:true}},
        {review:{...a.review,writeAuthorized:true}},
        {review:{...a.review,sourceStatus:"SOURCE_CONFIRMED"}},
        {review:{...a.review,priorOwnerEpoch:a.review.freshEpoch}}
    ];
    for(const override of wrong) {
        const result=project({...a.input,...override});
        assert.equal(result.ok,false,JSON.stringify(override));
        assertSafe(result);
    }
});
test("Hub requires M12p presentation and cannot synthesize a new ticket",()=>{
    const s=sample("HUB");
    for(const pendingHub of [undefined,null,
        {...s.pendingHub,ticket:{...s.pendingHub.ticket,ticketId:"m12o-other-0000001"}}]) {
        const result=project({...s.input,pendingHub});
        assert.equal(result.ok,false);
        assertSafe(result);
    }
});
test("M13b is not mounted, production writer and four legacy surfaces untouched",()=>{
    const source=fs.readFileSync(path.join(__dirname,
        "fixtures/TaskRecoveryDisplayM13b.cjs"),"utf8");
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.doesNotMatch(source,/\b(?:require|FileView|Process|openSync|writeFile|spawnSync|fetch)\s*\(/);
    assert.doesNotMatch(store+shell,/TaskRecoveryDisplayM13b/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const flag of ["ticketProducerEnabled","guardedWriterEnabled",
            "independentlyAuthenticatedTicketReceipt"])
        assert.match(store,new RegExp("readonly property bool "+flag+":\\s*false"));
    const files=["widgets/hub/ApolloHubTodoMini.qml",
        "widgets/tasks/TaskDetailsPane.qml",
        "widgets/tasks/TaskPlannerSchedulePane.qml",
        "widgets/tasks/TaskProjectsPane.qml"];
    for(const file of files) {
        const text=fs.readFileSync(path.join(ROOT,file),"utf8");
        assert.doesNotMatch(text,/TaskRecoveryDisplayM13b/);
    }
});
