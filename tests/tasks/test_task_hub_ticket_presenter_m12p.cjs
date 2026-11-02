#!/usr/bin/env node
/* TASKS M12p: Hub Mini first consumer ticket seam, strict disabled-by-default. */
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const ROOT=path.resolve(__dirname,"../..");
const load=(relative)=>{
    const sandbox=vm.createContext({});
    const code=fs.readFileSync(path.join(ROOT,relative),"utf8")
        .replace(/^\.pragma library\s*/,"");
    vm.runInContext(code,sandbox,{filename:relative,timeout:1000});
    return sandbox;
};
const policy=load("services/hub/ApolloHubTodoPolicy.js");
const contract=load("services/hub/TaskSaveTicketContractM12o.js");
const presenter=load("widgets/hub/TaskHubTicketPresenterM12p.js");
const copy=x=>JSON.parse(JSON.stringify(x));
const empty=()=>policy.emptyDocument();
const seed=()=>policy.create(empty(),"First",1000).document;
const view=d=>copy(policy.view(d.tasks.length?"ready":"empty",d,""));
const cases=[
    ["add","addTask",empty,d=>policy.create(d,"New",1100),{input:"New",target:""}],
    ["rename","renameTask",seed,d=>policy.update(d,"t1","rename","Changed",1100,false),{input:"Changed",target:"t1"}],
    ["done","setTaskDone",seed,d=>policy.update(d,"t1","done",true,1100,false),{taskId:"t1",wasDone:false}],
    ["remove","removeTask",seed,d=>policy.update(d,"t1","delete",null,1100,true),{taskId:"t1",deleteConfirmed:true}]
];

function setup(kind,method,initial,mutation,draft) {
    const baseline=view(initial());
    const result=mutation(initial());
    assert.equal(result.ok,true,JSON.stringify(result));
    const expected=view(result.document);
    const admission={
        admitted:true,ticketId:"m12o-hub-"+method+"-000001",
        baseline,expected
    };
    const pending=presenter.begin(contract,kind,method,admission,baseline,draft);
    assert.ok(pending);
    return {baseline,expected,admission,pending};
}

test("exactly four Hub actions are supported and no unsupported action admitted",()=>{
    assert.deepEqual(copy(presenter.HUB_METHODS),{
        add:"addTask",rename:"renameTask",done:"setTaskDone",remove:"removeTask"
    });
    const before=view(seed()),expected=view(
        policy.update(seed(),"t1","rename","Edited",1100,false).document);
    const admission={admitted:true,ticketId:"m12o-invalid-hub-00001",expected};
    assert.equal(presenter.begin(contract,"done","renameTask",admission,before,{id:"t1"}),null);
    assert.equal(presenter.begin(contract,"project","deleteProject",admission,before,{id:"p1"}),null);
    assert.equal(presenter.begin(contract,"rename","renameTask",{admitted:false},before,{id:"t1"}),null);
});

for(const [kind,method,initial,mutation,draft] of cases) {
    test(kind+": unrelated receipt, early receipt, then confirmed snapshot",()=>{
        const {pending,baseline,expected}=setup(kind,method,initial,mutation,draft);
        assert.equal(pending.ticket.disposition,"KEEP_DRAFT");
        assert.equal(pending.ticket.state,"QUEUED");

        const other=presenter.advance(contract,pending,{
            ticketId:"m12o-other-00001",state:"CONFIRMED",
            evidence:"SYNTHETIC_READBACK_RECEIPT"},expected);
        assert.equal(other.effect,"KEEP_DRAFT");
        assert.equal(other.pending.ticket.state,"QUEUED");

        const writing=presenter.advance(contract,pending,{
            ticketId:pending.ticket.ticketId,state:"WRITING"},baseline);
        assert.equal(writing.pending.ticket.state,"WRITING");
        assert.equal(writing.effect,"KEEP_DRAFT");

        // Receipt may be emitted before policy.view transitions saving -> ready.
        const interim=copy(expected);interim.state="saving";interim.writable=false;
        const receipt={ticketId:pending.ticket.ticketId,state:"CONFIRMED",
                       evidence:"SYNTHETIC_READBACK_RECEIPT"};
        const early=presenter.advance(contract,writing.pending,receipt,interim);
        assert.equal(early.effect,"KEEP_DRAFT");
        assert.equal(early.pending.ticket.state,"VERIFYING");
        assert.ok(early.pending.bufferedReceipt);

        const done=presenter.advance(contract,early.pending,null,expected);
        assert.equal(done.pending.ticket.state,"CONFIRMED");
        assert.equal(done.effect,"CLEAR_DRAFT");
        assert.equal(done.pending.ticket.disposition,"CLEAR_DRAFT");
        assert.deepEqual(copy(done.pending.ticket.draft),draft);

        // Late save failure must not reverse a legitimately settled ticket.
        const late=presenter.advance(contract,done.pending,{
            ticketId:pending.ticket.ticketId,state:"REVIEW_REQUIRED"},baseline);
        assert.equal(late.effect,"NONE");
        assert.equal(late.pending.ticket.state,"CONFIRMED");
    });

    test(kind+": stale settled snapshots and unverified receipt never clear draft",()=>{
        const {pending,baseline,expected}=setup(kind,method,initial,mutation,draft);
        const receipt={ticketId:pending.ticket.ticketId,state:"CONFIRMED",
                       evidence:"SYNTHETIC_READBACK_RECEIPT"};
        const mismatch=presenter.advance(contract,pending,receipt,baseline);
        assert.equal(mismatch.effect,"KEEP_DRAFT_FINAL");
        assert.equal(mismatch.pending.ticket.state,"REVIEW_REQUIRED");
        const unsigned=presenter.advance(contract,pending,{
            ticketId:pending.ticket.ticketId,state:"CONFIRMED"},expected);
        assert.equal(unsigned.effect,"KEEP_DRAFT_FINAL");
        assert.equal(unsigned.pending.ticket.state,"REVIEW_REQUIRED");
        const hardError=presenter.advance(contract,pending,null,{
            state:"error",writable:false,items:[],projects:[],total:0,remaining:0
        });
        assert.equal(hardError.effect,"KEEP_DRAFT_FINAL");
        assert.equal(hardError.pending.ticket.state,"REVIEW_REQUIRED");
    });

    test(kind+": admission with a mismatched baseline is refused",()=>{
        const {admission,baseline}=setup(kind,method,initial,mutation,draft);
        const bad=copy(admission);
        bad.baseline.total=999;
        assert.equal(presenter.begin(contract,kind,method,bad,baseline,draft),null);
    });
}

test("production Hub Mini old write path is still default, readonly-disabled new path",()=>{
    const mini=fs.readFileSync(path.join(ROOT,"widgets/hub/ApolloHubTodoMini.qml"),"utf8");
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.match(mini,/readonly property bool ticketUiEnabled: false/);
    assert.match(mini,/property var ticketProducer: null/);
    assert.match(mini,/TicketPresenter\.begin\(TicketContract/);
    assert.match(mini,/TicketPresenter\.advance\(TicketContract/);
    assert.match(mini,/target: todoMini\.ticketUiEnabled \? todoMini\.ticketProducer : null/);
    assert.match(mini,/if \(ticketUiEnabled\) \{\s*processTicketEvent\(null\)/);
    for(const method of ["addTask","renameTask","setTaskDone","removeTask"])
        assert.match(mini,new RegExp("todoStore\\."+method+"\\("));
    assert.match(mini,/if \(!todoStore\.removeTask\(task\.id, true\)\)/);
    assert.match(mini,/if \(!todoStore\.setTaskDone\(task\.id, task\.done !== true\)\)/);
    assert.match(mini,/if \(pendingWriteKind === "remove"\)/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/return stage\(TodoPolicy\./g)||[]).length,9);
    assert.match(store,/readonly property bool guardedWriterEnabled: false/);
    assert.doesNotMatch(shell+store,/TaskHubTicketPresenterM12p|TaskSaveTicketFacadeM12o/);
    assert.doesNotMatch(mini,/\bFileView\s*\{|\bProcess\s*\{|Quickshell\.dataDir/);
    // No unapproved privileged broker, native host or external data path.
    assert.doesNotMatch(mini,/\.exec\(|https?:\/\/|\.setText\(/);
});

test("disabled facade still refuses any request; other three consumers not changed",()=>{
    const facade=fs.readFileSync(path.join(ROOT,"services/hub/TaskSaveTicketFacadeM12o.qml"),"utf8");
    assert.match(facade,/readonly property bool enabled: false/);
    assert.match(facade,/reason:"M12O_DISABLED_NO_WRITER"/);
    for(const file of ["widgets/tasks/TaskDetailsPane.qml",
                       "widgets/tasks/TaskPlannerSchedulePane.qml",
                       "widgets/tasks/TaskProjectsPane.qml"]) {
        const src=fs.readFileSync(path.join(ROOT,file),"utf8");
        assert.doesNotMatch(src,/TaskHubTicketPresenterM12p|ticketUiEnabled/);
    }
});
