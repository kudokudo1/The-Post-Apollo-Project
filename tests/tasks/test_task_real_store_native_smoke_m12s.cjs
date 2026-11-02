#!/usr/bin/env node
/* M12s: source + extracted-function contract for the unmounted Quickshell
 * *real store* native observation panel. Mock methods only; no native load.
 */
"use strict";
const assert=require("node:assert/strict");
const test=require("node:test");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const qml=read("TaskNativeStoreSmokeM12s.qml");
const store=read("services/hub/ApolloHubTodoStore.qml");
const shell=read("shell.qml");

function method(name) {
    const start=qml.indexOf("function "+name+"(");
    assert.ok(start>=0,"missing harness function "+name);
    const open=qml.indexOf("{",start);
    let nesting=0;
    for(let i=open;i<qml.length;i++) {
        if(qml[i]==="{") nesting++;
        else if(qml[i]==="}" && --nesting===0)
            return qml.slice(start,i+1);
    }
    throw Error("unbalanced harness function "+name);
}
function harnessContext(flags={}) {
    const calls={submit:0,add:0,reload:0};
    const ctx=vm.createContext({
        guardedPath:flags.guardedPath??false,
        flagsSafe:flags.flagsSafe??true,
        canEditFixture:flags.canEditFixture??false,
        lastAction:"NO ACTION",
        actionRequested:false,
        ApolloHubTodoStore:{
            submit(){calls.submit++;return {admitted:false,reason:"M12Q_DISABLED_NO_WRITER"};},
            addTask(){calls.add++;return true;},
            reloadFromDisk(){calls.reload++;return true;}
        }
    });
    ctx.smoke=ctx;
    for(const n of ["testDisabledTicketRefusal","testLegacyWrite","testReload"])
        vm.runInContext("this."+n+"="+method(n),ctx,{timeout:1000});
    return {ctx,calls};
}
test("isolated DataDir pragma and disposable env marker own any test writes",()=>{
    assert.match(qml,/^\/\/@ pragma DataDir \$BASE\/post-apollo-m12s-fixture$/m);
    assert.match(qml,/^\/\/@ pragma StateDir \$BASE\/post-apollo-m12s-state$/m);
    assert.match(qml,/import qs\.services\.hub/);
    assert.match(qml,/Quickshell\.dataDir\.endsWith\(exactExpectedSuffix\)/);
    assert.match(qml,/storePath === Quickshell\.dataDir \+ "\/apollo-hub-todo-v1\.json"/);
    assert.match(qml,/Quickshell\.env\("POST_APOLLO_M12S_DISPOSABLE"\) === "1"/);
    assert.match(qml,/guardedPath && flagsSafe/);
    assert.doesNotMatch(qml,/\b(?:FileView|Process)\s*\{|execDetached|Qt\.createQmlObject/);
    assert.doesNotMatch(shell,/\bTaskNativeStoreSmokeM12s\b/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.match(store,/readonly property bool ticketProducerEnabled:\s*false/);
    assert.match(store,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.match(store,/readonly property bool independentlyAuthenticatedTicketReceipt:\s*false/);
});
test("no automatic write on construction, no task path or module copy",()=>{
    assert.doesNotMatch(qml,/Component\.onCompleted\s*:/);
    assert.doesNotMatch(qml,/Timer\s*\{/);
    assert.match(qml,/ApolloHubTodoStore\.addTask\("M12S_SYNTHETIC_TASK"\)/);
    assert.match(qml,/ApolloHubTodoStore\.reloadFromDisk\(\)/);
    assert.match(qml,/ApolloHubTodoStore\.submit\(/);
    assert.doesNotMatch(qml,/ticketProducerEnabled\s*:\s*true/);
    assert.doesNotMatch(qml,/guardedWriterEnabled\s*:\s*true/);
});
test("disabled-ticket button refuses if not isolated; otherwise checks refusal only",()=>{
    const {ctx,calls}=harnessContext();
    ctx.testDisabledTicketRefusal();
    assert.equal(calls.submit,0);
    assert.match(ctx.lastAction,/REFUSED/);
    ctx.guardedPath=true;
    ctx.testDisabledTicketRefusal();
    assert.equal(calls.submit,1);
    assert.equal(calls.add,0);
    assert.match(ctx.lastAction,/TICKET ADMISSION REFUSED/);
});
test("legacy write and reload never run when fixture guard blocks",()=>{
    const {ctx,calls}=harnessContext();
    ctx.testLegacyWrite();
    ctx.testReload();
    assert.equal(calls.add,0);
    assert.equal(calls.reload,0);
    ctx.canEditFixture=true; // positive mock-only observation route
    ctx.testLegacyWrite();
    ctx.testReload();
    assert.equal(calls.add,1);
    assert.equal(calls.reload,1);
    assert.equal(ctx.actionRequested,true);
});
test("disabled test never calls legacy write even when permitted",()=>{
    const {ctx,calls}=harnessContext({guardedPath:true,canEditFixture:true});
    ctx.testDisabledTicketRefusal();
    assert.equal(calls.submit,1);
    assert.equal(calls.add,0);
    assert.equal(calls.reload,0);
});
