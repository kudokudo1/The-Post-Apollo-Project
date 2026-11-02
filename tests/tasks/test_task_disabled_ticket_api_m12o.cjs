#!/usr/bin/env node
/* TASKS M12o // Four-consumer reconciliation, PURE & DISABLED. No QML runtime. */
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const ROOT=path.resolve(__dirname,"../..");
function loadJs(p) {
    const code=fs.readFileSync(path.join(ROOT,p),"utf8")
        .replace(/^\.pragma library\s*/, "");
    const sandbox=vm.createContext({});
    vm.runInContext(code,sandbox,{timeout:1000,filename:p});
    return sandbox;
}
const policy=loadJs("services/hub/ApolloHubTodoPolicy.js");
const contract=loadJs("services/hub/TaskSaveTicketContractM12o.js");
const copy=x=>JSON.parse(JSON.stringify(x));
const seedTask=()=>policy.create(policy.emptyDocument(),"Seed task",1000).document;
const seedProject=()=>policy.createProject(seedTask(),"Alpha",1100).document;
const seedProjectOnly=()=>policy.createProject(policy.emptyDocument(),"Alpha",1100).document;
const view=d=>copy(policy.view(d.tasks.length ? "ready":"empty",d,""));
const accept=(t,snapshot)=>contract.reconcile(t,{
    ticketId:t.ticketId,state:"CONFIRMED",evidence:"SYNTHETIC_READBACK_RECEIPT"
},snapshot);
const scenarios=[
    ["HUB","addTask",()=>policy.emptyDocument(), d=>policy.create(d,"A task",1200)],
    ["HUB","renameTask",seedTask, d=>policy.update(d,"t1","rename","Renamed",1200,false)],
    ["HUB","setTaskDone",seedTask, d=>policy.update(d,"t1","done",true,1200,false)],
    ["HUB","removeTask",seedTask, d=>policy.update(d,"t1","delete",null,1200,true)],
    ["DETAILS","updateTaskDetails",seedTask,
        d=>policy.updateDetails(d,"t1","high","Details note","2026-11-02",1200)],
    ["PLANNER","addTask",()=>policy.emptyDocument(), d=>policy.create(d,"Undated",1200)],
    ["PLANNER","updateTaskDetails",seedTask,
        d=>policy.updateDetails(d,"t1","medium","Scheduled","2026-11-03",1200)],
    ["PROJECTS","createProject",()=>policy.emptyDocument(),
        d=>policy.createProject(d,"New project",1200)],
    ["PROJECTS","renameProject",seedProject,
        d=>policy.renameProject(d,"p1","Beta",1200)],
    ["PROJECTS","deleteProject",seedProject,
        d=>policy.deleteProject(d,"p1",1200,true)],
    ["PROJECTS","assignTaskProject",seedProject,
        d=>policy.assignProject(d,"t1","p1",1200)]
];

test("all four caller surfaces and nine storage mutation routes are enumerated",()=>{
    const allowed=Object.values(contract.OPERATIONS).map(x=>Array.from(x)).flat();
    assert.equal(new Set(allowed).size,9);
    assert.deepEqual([...new Set(scenarios.map(x=>x[0]))].sort(),
        ["DETAILS","HUB","PLANNER","PROJECTS"]);
    for(const [surface,method] of scenarios)
        assert.equal(contract.supported(surface,method),true);
    assert.equal(contract.supported("OTHER","addTask"),false);
    assert.equal(contract.supported("DETAILS","deleteProject"),false);
});

for(const [surface,method,initial,mutation] of scenarios) {
    test(surface+" / "+method+": only exact matching ticket and expected snapshot clear draft",()=>{
        const before=initial();
        const result=mutation(before);
        assert.equal(result.ok,true,JSON.stringify(result));
        const beforeView=view(before), afterView=view(result.document);
        const id="m12o-test-"+surface+"-"+method;
        const draft={surface,method,sent:false,description:"Uncommitted user input"};
        const ticket=contract.begin(surface,method,id,beforeView,afterView,draft);
        assert.equal(ticket.state,"QUEUED");
        assert.equal(ticket.disposition,"KEEP_DRAFT");

        const admitted=contract.reconcile(ticket,{ticketId:id,state:"QUEUED"},beforeView);
        assert.equal(admitted.disposition,"KEEP_DRAFT");
        const writing=contract.reconcile(admitted,{ticketId:id,state:"WRITING"},beforeView);
        assert.equal(writing.state,"WRITING");
        const verify=contract.reconcile(writing,{ticketId:id,state:"VERIFYING"},beforeView);
        assert.equal(verify.state,"VERIFYING");

        // No matching snapshot means a claimed completion is not accepted.
        const bad=accept(verify,beforeView);
        assert.equal(bad.state,"REVIEW_REQUIRED");
        assert.equal(bad.reason,"COMPLETION_SNAPSHOT_MISMATCH");
        assert.equal(bad.disposition,"KEEP_DRAFT");
        const late=accept(bad,afterView);
        assert.equal(late.state,"REVIEW_REQUIRED");

        const real=accept(verify,afterView);
        assert.equal(real.state,"CONFIRMED");
        assert.equal(real.disposition,"CLEAR_DRAFT");
        assert.deepEqual(copy(real.draft),draft);
        assert.equal(contract.reconcile(real,{ticketId:id,state:"WRITING"},beforeView).state,
                     "CONFIRMED");
    });
}
test("foreign ticket completion cannot clear another consumer's draft",()=>{
    const d=seedTask();
    const r=policy.update(d,"t1","rename","New title",1200,false);
    const ticket=contract.begin("HUB","renameTask","m12o-foreign-000001",view(d),view(r.document),{text:"New title"});
    const foreign=contract.reconcile(ticket,{
        ticketId:"m12o-foreign-000002",state:"CONFIRMED",
        evidence:"SYNTHETIC_READBACK_RECEIPT"},view(r.document));
    assert.equal(foreign.state,"QUEUED");
    assert.equal(foreign.disposition,"KEEP_DRAFT");
});
test("no bool, no self-reported event, no success-only snapshot can confirm",()=>{
    const d=seedTask(), r=policy.update(d,"t1","done",true,1200,false);
    const t=contract.begin("HUB","setTaskDone","m12o-proof-0000001",view(d),view(r.document),{done:true});
    assert.equal(contract.reconcile(t,{ticketId:t.ticketId,state:"WRITING"},view(r.document)).disposition,
                 "KEEP_DRAFT");
    const forged=contract.reconcile(t,{ticketId:t.ticketId,state:"CONFIRMED"},view(r.document));
    assert.equal(forged.state,"REVIEW_REQUIRED");
    assert.equal(forged.reason,"UNVERIFIED_COMPLETION");
    assert.equal(contract.reconcile(t,true,view(r.document)).state,"QUEUED");
});
test("reject, block and uncertain recovery never discard drafts",()=>{
    const d=seedTask(),r=policy.update(d,"t1","rename","X",1200,false);
    const t=contract.begin("HUB","renameTask","m12o-error-0000001",view(d),view(r.document),{text:"X"});
    for(const state of ["REJECTED","BLOCKED","REVIEW_REQUIRED"]) {
        const done=contract.reconcile(t,{ticketId:t.ticketId,state},view(r.document));
        assert.equal(done.state,state);
        assert.equal(done.disposition,"KEEP_DRAFT");
        assert.equal(done.draft.text,"X");
    }
});
test("invalid ticket, unsupported surface or unchanged mutation cannot create an intent",()=>{
    const d=seedTask(),v=view(d);
    assert.equal(contract.begin("HUB","addTask","bad",v,v,{text:"unchanged"}),null);
    assert.equal(contract.begin("SETTINGS","addTask","m12o-invalid-00001",v,v,{text:"x"}),null);
    assert.equal(contract.begin("HUB","addTask","m12o-invalid-00001",v,v,{text:"x"}),null);
});
test("returned views and retained drafts are defensive copies",()=>{
    const d=seedTask(),r=policy.update(d,"t1","rename","Future",1200,false),before=view(d),expected=view(r.document);
    const draft={text:"Future"};
    const t=contract.begin("HUB","renameTask","m12o-clone-0000001",before,expected,draft);
    before.items[0].title="Tampered";
    expected.items[0].title="Tampered";
    draft.text="Tampered";
    assert.equal(t.draft.text,"Future");
    assert.equal(t.expected.items[0].title,"Future");
});
test("unmounted QML facade cannot admit a live write or create a second writer",()=>{
    const facade=fs.readFileSync(path.join(ROOT,"services/hub/TaskSaveTicketFacadeM12o.qml"),"utf8");
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.match(facade,/readonly property bool enabled: false/);
    assert.match(facade,/productionWriterAuthorized: false/);
    assert.match(facade,/M12O_DISABLED_NO_WRITER/);
    for(const raw of [facade]) {
        assert.doesNotMatch(raw,/\bFileView\s*\{|\bProcess\s*\{/);
        assert.doesNotMatch(raw,/\.setText\(|\.exec\(|\.write\(/);
        assert.doesNotMatch(raw,/Quickshell\.dataDir|apollo-hub-todo-v1\.json/);
    }
    assert.match(store,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/return stage\(TodoPolicy\./g)||[]).length,9);
    assert.doesNotMatch(store+shell,/TaskSaveTicketFacadeM12o|TaskSaveTicketContractM12o/);
});
test("four live consumer files remain legacy boolean clients, not accidentally migrated",()=>{
    const expected={
        "widgets/hub/ApolloHubTodoMini.qml":["addTask","renameTask","setTaskDone","removeTask"],
        "widgets/tasks/TaskDetailsPane.qml":["updateTaskDetails"],
        "widgets/tasks/TaskPlannerSchedulePane.qml":["addTask","updateTaskDetails"],
        "widgets/tasks/TaskProjectsPane.qml":["createProject","renameProject","deleteProject","assignTaskProject"]
    };
    for(const [file,methods] of Object.entries(expected)) {
        const qml=fs.readFileSync(path.join(ROOT,file),"utf8");
        for(const method of methods)
            assert.match(qml,new RegExp("todoStore\\."+method+"\\("));
        if(file === "widgets/hub/ApolloHubTodoMini.qml") {
            // M12p introduces an *inert* future UI seam only. It is not a
            // migrated writer: this literal false guard cannot be toggled
            // by the operator or by an injected provider at runtime.
            assert.match(qml,/readonly property bool ticketUiEnabled: false/);
            assert.match(qml,/property var ticketProducer: null/);
            assert.match(qml,/TaskSaveTicketContractM12o\.js/);
            assert.doesNotMatch(qml,/TaskSaveTicketFacadeM12o\.qml/);
            assert.doesNotMatch(qml,/\bFileView\s*\{|\bProcess\s*\{/);
        } else {
            assert.doesNotMatch(qml,/TaskSaveTicketFacadeM12o|TaskSaveTicketContractM12o/);
        }
    }
});
