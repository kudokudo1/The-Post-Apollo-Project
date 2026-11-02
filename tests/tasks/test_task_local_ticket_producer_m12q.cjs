#!/usr/bin/env node
/* M12q: test the REAL v3 policy + hard-disabled store ticket source path.
 * No task file, Quickshell, local machine, broker or native host is touched.
 */
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
function load(relative) {
    const sandbox=vm.createContext({unescape,encodeURIComponent});
    const code=fs.readFileSync(path.join(ROOT,relative),"utf8")
        .replace(/^\.pragma library\s*/,"");
    vm.runInContext(code,sandbox,{filename:relative,timeout:1000});
    return sandbox;
}
const producer=load("services/hub/TaskLocalTicketProducerM12q.js");
const policy=load("services/hub/ApolloHubTodoPolicy.js");
const contract=load("services/hub/TaskSaveTicketContractM12o.js");
const presentation=load("widgets/hub/TaskHubTicketPresenterM12p.js");
const clone=v=>JSON.parse(JSON.stringify(v));
const empty=()=>policy.emptyDocument();
const oneTask=()=>policy.create(empty(),"First",1000).document;
const oneProject=()=>policy.createProject(oneTask(),"Alpha",1100).document;
const at=2000, session="M12qTestingSession01";
const cases=[
  ["HUB","addTask",empty,{title:"New task"}],
  ["HUB","renameTask",oneTask,{id:"t1",title:"New title"}],
  ["HUB","setTaskDone",oneTask,{id:"t1",done:true}],
  ["HUB","removeTask",oneTask,{id:"t1",confirmed:true}],
  ["DETAILS","updateTaskDetails",oneTask,{id:"t1",priority:"high",
                                       description:"Saved",dueDate:"2026-11-10"}],
  ["PLANNER","addTask",empty,{title:"Planner task"}],
  ["PLANNER","updateTaskDetails",oneTask,{id:"t1",priority:"medium",
                                       description:"Schedule",dueDate:"2026-11-11"}],
  ["PROJECTS","createProject",empty,{name:"New project"}],
  ["PROJECTS","renameProject",oneProject,{id:"p1",name:"Beta"}],
  ["PROJECTS","deleteProject",oneProject,{id:"p1",confirmed:true}],
  ["PROJECTS","assignTaskProject",oneProject,{taskId:"t1",projectId:"p1"}]
];

for (const [surface,method,initial,args] of cases) {
    test(surface+"/"+method+": admission != saved, exact readback confirms expected view",()=>{
        const original=initial();
        const baseline=clone(original);
        const stage=producer.plan(policy,original,surface,method,args,at,session,1);
        assert.equal(stage.admitted,true,stage.reason);
        assert.equal(stage.state,"WRITING");
        assert.match(stage.ticketId,/^m12o-local-M12qTestingSession01-1$/);
        assert.equal(contract.validTicketId(stage.ticketId),true);
        assert.deepEqual(clone(original),baseline); // mutation policy clones source
        assert.notDeepEqual(clone(stage.baseline),clone(stage.expected));
        const early=producer.verify(policy,stage,stage.expectedRaw);
        assert.equal(early.confirmed,false);
        assert.equal(early.state,"REVIEW_REQUIRED");
        const ready=producer.saved(stage);
        assert.equal(ready.state,"VERIFYING");
        assert.equal(producer.verify(policy,ready,stage.expectedRaw).confirmed,true);
        const final=producer.verify(policy,ready,stage.expectedRaw);
        assert.equal(final.evidence,"SYNTHETIC_READBACK_RECEIPT");
        assert.deepEqual(clone(final.snapshot),clone(stage.expected));
        assert.deepEqual(clone(final.document),clone(stage.expectedDocument));
        assert.equal(policy.parse(stage.expectedRaw).ok,true);
        const corrupted=producer.verify(policy,ready,stage.expectedRaw+" ");
        assert.equal(corrupted.confirmed,false);
        assert.equal(corrupted.reason,"SOURCE_BYTES_MISMATCH");
        assert.equal(producer.saved(ready).state,"REVIEW_REQUIRED");
    });
}
test("all recognized mutation routes are explicit; never generic JS invocation",()=>{
    const mapping=clone(producer.ROUTES);
    assert.deepEqual(mapping,clone(contract.OPERATIONS));
    assert.equal(producer.plan(policy,empty(),"OTHER","addTask",
                              {title:"x"},at,session,1).admitted,false);
    assert.equal(producer.plan(policy,empty(),"HUB","constructor",
                              {},at,session,1).admitted,false);
    assert.equal(producer.plan(policy,empty(),"HUB","addTask",
                              {title:"x",confirmed:true},at,session,1).admitted,false);
    assert.equal(producer.plan(policy,empty(),"HUB","removeTask",
                              {id:"t1",confirmed:false},at,session,1).admitted,false);
});
test("invalid baseline, unsupported version and malformed request refuse",()=>{
    assert.equal(producer.plan(policy,{version:999},"HUB","addTask",
                              {title:"X"},at,session,1).admitted,false);
    assert.equal(producer.plan(policy,empty(),"HUB","addTask",
                              {title:""},at,session,1).admitted,false);
    assert.equal(producer.plan(policy,empty(),"HUB","addTask",
                              {title:"X"},at,"x",1).admitted,false);
    assert.equal(producer.plan(policy,empty(),"HUB","addTask",
                              {title:"X"},at,session,0).admitted,false);
    assert.equal(producer.plan(policy,empty(),"HUB","addTask",
                              {title:"X"},0,session,1).admitted,false);
});
test("failed or unknown completion never promotes, even if bytes happen to match",()=>{
    const stage=producer.plan(policy,empty(),"HUB","addTask",
                             {title:"New"},at,session,4);
    assert.equal(producer.verify(policy,{...stage,state:"REJECTED"},stage.expectedRaw)
                     .confirmed,false);
    assert.equal(producer.verify(policy,{...stage,state:"RECOVERY_REVIEW"},
                                stage.expectedRaw).confirmed,false);
    assert.equal(producer.verify(policy,producer.saved(stage),undefined)
                     .confirmed,false);
    assert.equal(producer.saved(null).state,"REVIEW_REQUIRED");
});
test("M12p first-consumer contract accepts only matching ticket AND synthetic receipt",()=>{
    const doc=oneTask(), stage=producer.plan(policy,doc,"HUB","renameTask",
                      {id:"t1",title:"New"},at,session,6);
    assert.equal(stage.admitted,true);
    const admission={admitted:true,ticketId:stage.ticketId,
                     baseline:stage.baseline,expected:stage.expected};
    const pending=presentation.begin(contract,"rename","renameTask",
                                      admission,stage.baseline,{text:"New"});
    assert.ok(pending);
    const saved=producer.saved(stage);
    const proof=producer.verify(policy,saved,stage.expectedRaw);
    const result=presentation.advance(contract,pending,{
        ticketId:stage.ticketId,state:proof.state,evidence:proof.evidence
    },proof.snapshot);
    assert.equal(result.effect,"CLEAR_DRAFT");
    assert.equal(result.pending.ticket.state,"CONFIRMED");
    const stale=presentation.advance(contract,pending,{
        ticketId:stage.ticketId,state:proof.state,evidence:proof.evidence
    },stage.baseline);
    assert.equal(stale.effect,"KEEP_DRAFT_FINAL");
});
test("live singleton remains exactly one FileView and ticket path compile-time disabled",()=>{
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const mini=fs.readFileSync(path.join(ROOT,"widgets/hub/ApolloHubTodoMini.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    const facade=fs.readFileSync(path.join(ROOT,"services/hub/TaskSaveTicketFacadeM12o.qml"),"utf8");
    assert.match(store,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.match(store,/readonly property bool ticketProducerEnabled:\s*false/);
    assert.match(store,/readonly property bool independentlyAuthenticatedTicketReceipt:\s*false/);
    assert.match(mini,/readonly property bool ticketUiEnabled:\s*false/);
    assert.match(facade,/readonly property bool enabled:\s*false/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/return stage\(TodoPolicy\./g)||[]).length,9);
    assert.match(store,/todo\.stage\(\{ok:true,document:stage\.expectedDocument\}\)/);
    assert.equal((store.match(/todoFile\.setText\(/g)||[]).length,1);
    assert.match(store,/todoFile\.reload\(\)/);
    assert.match(store,/TicketProducer\.verify\(TodoPolicy,stage,raw\)/);
    assert.match(store,/if \(ticketProducerEnabled && storageState === "saving"\)/);
    assert.match(store,/if \(todo\.ticketProducerEnabled\) \{/);
    assert.match(store,/if \(todo\.ticketProducerEnabled && todo\.pendingTicket\)/);
    assert.doesNotMatch(shell,/TaskLocalTicketProducerM12q|ticketProducerEnabled/);
    // Disallow second process/socket/write path and dynamic enabling.
    assert.doesNotMatch(store,/\bProcess\s*\{|execDetached|HttpClient|TcpSocket|UnixSocket/);
    assert.doesNotMatch(store,/ticketProducerEnabled\s*:\s*true/);
});
test("normal legacy code still publishes onSaved, and nine booleans still stage",()=>{
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    assert.match(store,/todoFile\.setText\(JSON\.stringify\(pendingDocument, null, 2\)/);
    assert.match(store,/todo\.document = todo\.pendingDocument/);
    assert.match(store,/todo\.pendingDocument = null/);
    assert.match(store,/if \(todo\.storageState !== "saving" \|\| !todo\.pendingDocument\)/);
    assert.match(store,/function submit\(surface, method, payload\)/);
    assert.match(store,/M12Q_DISABLED_NO_WRITER/);
});
