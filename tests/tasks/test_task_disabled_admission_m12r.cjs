#!/usr/bin/env node
/* TASKS M12r: execute the ACTUAL dormant QML store JS methods in a mock Scope.
 * Test-only in-memory FileView; never imports Quickshell, starts a process,
 * opens TASKS data, or enables the compiled production ticket gate.
 * This is NOT a native QML/Qt callback or durability acceptance test.
 */
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const read=relative=>fs.readFileSync(path.join(ROOT,relative),"utf8");
const STORE=read("services/hub/ApolloHubTodoStore.qml");
function load(relative) {
    const ctx=vm.createContext({unescape,encodeURIComponent});
    vm.runInContext(read(relative).replace(/^\.pragma library\s*/,""),ctx,
                    {filename:relative,timeout:1000});
    return ctx;
}
const policy=load("services/hub/ApolloHubTodoPolicy.js");
const producer=load("services/hub/TaskLocalTicketProducerM12q.js");

// Reuse QML's existing JS function bodies, not a separately reimplemented
// coordinator: scope-level properties are supplied by the mock context.
function functionSource(name) {
    const start=STORE.indexOf("function "+name+"(");
    assert.ok(start>=0,"missing store method "+name);
    const open=STORE.indexOf("{",start);
    let depth=0;
    for(let i=open;i<STORE.length;i++) {
        if(STORE[i]==="{") depth++;
        if(STORE[i]==="}" && --depth===0)
            return STORE.slice(start,i+1);
        // Every brace in the selected store methods is JS syntax, not
        // an interpolated string or a comment containing a brace.
    }
    throw Error("unbalanced QML method: "+name);
}
function mock(initialEnabled=false) {
    const writes=[],events=[];
    const s=vm.createContext({
        TodoPolicy:policy,TicketProducer:producer,
        ticketProducerEnabled:initialEnabled,guardedWriterEnabled:false,
        storageState:"empty",errorCode:"",
        document:policy.emptyDocument(),pendingDocument:null,
        pendingTicket:null,ticketSequence:0,
        ticketSessionNonce:"M12rFixtureSession01",
        todoFile:{setText(raw){writes.push(raw);}},
        ticketEvent(event){events.push(JSON.parse(JSON.stringify(event)));}
    });
    s.todo=s;
    for(const name of ["submit","stage","ticketReview","ticketReadback","acceptLoaded"]) {
        vm.runInContext("this."+name+"="+functionSource(name),s,
                        {filename:"ApolloHubTodoStore.qml:"+name,timeout:1000});
    }
    return {s,writes,events};
}
const admitted=(s)=>s.submit("HUB","addTask",{args:{title:"M12r disposable ticket"}});
test("compiled false gate blocks any actual submit and leaves storage untouched",()=>{
    assert.match(STORE,/readonly property bool ticketProducerEnabled:\s*false/);
    assert.match(STORE,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.match(STORE,/readonly property bool independentlyAuthenticatedTicketReceipt:\s*false/);
    const {s,writes,events}=mock(false);
    const result=admitted(s);
    assert.equal(result.admitted,false);
    assert.equal(result.reason,"M12Q_DISABLED_NO_WRITER");
    assert.equal(s.storageState,"empty");
    assert.equal(s.pendingTicket,null);
    assert.equal(writes.length,0);
    assert.equal(events.length,0);
});
test("mock-only enabled admission reaches exactly one original stage/setText",()=>{
    const {s,writes,events}=mock(true);
    const ticket=admitted(s);
    assert.equal(ticket.admitted,true,ticket.reason);
    assert.equal(ticket.state,"QUEUED");
    assert.equal(s.pendingTicket.ticketId,ticket.ticketId);
    assert.equal(s.pendingTicket.state,"WRITING");
    assert.equal(s.storageState,"saving");
    assert.equal(s.pendingDocument.tasks.length,1);
    assert.equal(s.document.tasks.length,0); // not yet confirmed
    assert.equal(writes.length,1);
    assert.equal(events.length,0); // no premature success
    assert.equal(admitted(s).admitted,false); // no second mutation
    assert.equal(writes.length,1);
    s.pendingTicket=producer.saved(s.pendingTicket); // synthetic onSaved hint
    assert.equal(s.pendingTicket.state,"VERIFYING");
    s.acceptLoaded(writes[0]); // synthetic readback of exact bytes
    assert.equal(s.document.tasks.length,1);
    assert.equal(s.storageState,"ready");
    assert.equal(s.pendingDocument,null);
    assert.equal(s.pendingTicket,null);
    assert.equal(events.length,1);
    assert.equal(events[0].ticketId,ticket.ticketId);
    assert.equal(events[0].state,"CONFIRMED");
    assert.equal(events[0].evidence,"SYNTHETIC_READBACK_RECEIPT");
});
test("wrong early readback forces review without promoting draft or retrying",()=>{
    const {s,writes,events}=mock(true);
    const ticket=admitted(s);
    assert.equal(ticket.admitted,true);
    s.acceptLoaded(writes[0]); // saved callback never observed
    assert.equal(s.document.tasks.length,0);
    assert.equal(s.pendingDocument,null);
    assert.equal(s.pendingTicket,null);
    assert.equal(s.storageState,"error");
    assert.equal(events.length,1);
    assert.equal(events[0].state,"REVIEW_REQUIRED");
    assert.equal(writes.length,1);
    assert.equal(admitted(s).admitted,false);
});
test("mismatched source bytes and explicit save failure preserve confirmed state",()=>{
    for(const scenario of ["mismatch","save-failed"]) {
        const {s,writes,events}=mock(true);
        assert.equal(admitted(s).admitted,true);
        if(scenario==="mismatch") {
            s.pendingTicket=producer.saved(s.pendingTicket);
            s.acceptLoaded(writes[0]+" "); // byte mismatch despite valid JSON
        } else s.ticketReview("FILE_SAVE_FAILED");
        assert.equal(s.document.tasks.length,0);
        assert.equal(s.storageState,"error");
        assert.equal(s.pendingDocument,null);
        assert.equal(s.pendingTicket,null);
        assert.equal(events.length,1);
        assert.equal(events[0].state,"REVIEW_REQUIRED");
        assert.equal(writes.length,1); // no replay
    }
});
test("single writer and legacy boolean path remain structurally unchanged",()=>{
    assert.equal((STORE.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((STORE.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.equal((STORE.match(/return stage\(TodoPolicy\./g)||[]).length,9);
    assert.match(functionSource("submit"),/todo\.stage\(\{ok:true,document:stage\.expectedDocument\}\)/);
    // The fixed submit must not preempt stage()'s READY/EMPTY admission.
    const submit=functionSource("submit");
    const beforeStage=submit.slice(0,submit.indexOf("todo.stage("));
    assert.doesNotMatch(beforeStage,/\bstorageState\s*=\s*"saving"/);
    assert.doesNotMatch(beforeStage,/\bpendingDocument\s*=/);
    assert.match(functionSource("stage"),/storageState\s*=\s*"saving"/);
    const {s,writes}=mock(false);
    const planned=policy.create(s.document,"Legacy fixture",1000);
    assert.equal(s.stage(planned),true);
    assert.equal(s.storageState,"saving");
    assert.equal(writes.length,1);
    assert.equal(s.document.tasks.length,0);
});
