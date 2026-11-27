// Actual disposable child outputs replayed into existing UI2 consumers.
// Not native Process/Loader joining or a production bridge.
const assert = require("node:assert/strict");
const fs = require("node:fs"), vm = require("node:vm"), path = require("node:path");
const {execFileSync} = require("node:child_process");
const root=path.resolve(__dirname,"../..");
function load(name) {
    const c=vm.createContext({});
    vm.runInContext(fs.readFileSync(path.join(root,"widgets/forest/ui2",name),"utf8"),c);
    return c;
}
const d=JSON.parse(execFileSync("python3",["-B",path.join(__dirname,"ui2_r6d_child_fixture.py")],
    {encoding:"utf8",timeout:90000,maxBuffer:131072}));
const history=load("PublicHistoryDisplay.js").createController();
const status=load("PublicRuntimeStatusDisplay.js").createConsumer();
function deliver(ref,units) {
    let s;
    for(const u of units) {
        s=status.receive(u,ref);
        assert.equal(s.state,"DISPLAYING");
        assert.equal(s.permissionGranted,false);
    }
    return s;
}
function read(scope,entry,continuation=false) {
    const p=continuation?history.next(scope,entry.requestId,2):history.open(scope,entry.requestId,2);
    assert.equal(p.state,"PENDING");
    assert.equal(p.request.after,entry.after);
    assert.equal(entry.frame.requestId,p.request.requestId,"fixture request correlation");
    const result=history.receive(entry.frame,scope);
    assert.equal(result.permissionGranted,false);
    assert.equal(result.request,null);
    return result;
}
assert.equal(status.open(d.a,d.a).state,"ATTACHED");
assert.equal(deliver(d.a,d.unitsA).status,"LOCAL_COMMIT_RECORDED");
assert.equal(history.observe(d.h1).state,"CLOSED");
const first=read(d.h1,d.first);
assert.equal(first.state,"COMPLETE");
assert.equal(first.messages.length,2);
assert.equal(status.open(d.b,d.b).state,"ATTACHED");
assert.equal(deliver(d.b,d.unitsB).status,"LOCAL_COMMIT_RECORDED");
assert.equal(history.observe(d.h1).messages.length,2);
assert.equal(d.h1.sessionId,d.h2.sessionId);
assert.notEqual(d.h1.viewKey,d.h2.viewKey);
assert.equal(history.observe(d.h2).messages.length,0);
const partial=read(d.h2,d.second[0]);
assert.equal(partial.state,"PARTIAL");
assert.equal(partial.nextAfter,2);
assert.deepEqual(JSON.stringify(partial.messages),JSON.stringify(first.messages));
const full=read(d.h2,d.second[1],true);
assert.equal(full.state,"COMPLETE");
assert.equal(full.messages.length,4);
assert.equal(new Set(full.messages.map(x=>x.turnId)).size,4);
assert.equal(full.messages.filter(x=>x.direction==="incoming").length,2);
assert.equal(d.h3.sessionId,d.h2.sessionId);
assert.notEqual(d.h3.viewKey,d.h2.viewKey);
assert.equal(history.observe(d.h3).messages.length,0);
assert.equal(read(d.h3,d.reopened[0]).state,"PARTIAL");
const reopened=read(d.h3,d.reopened[1],true);
assert.equal(reopened.state,"COMPLETE");
assert.equal(JSON.stringify(reopened.messages),JSON.stringify(full.messages));
assert.equal(status.open(d.c,d.c).state,"ATTACHED");
assert.equal(deliver(d.c,d.unitsC).status,"GENERATING");
assert.equal(status.receive(d.unitsB[0],d.c).status,"GENERATING");
assert.equal(deliver(d.c,d.stop).status,"STOP_REQUESTED");
assert.equal(history.observe(d.h3).messages.length,4);
// STOP observation alone is not a cancellation outcome. An old typed
// result must not change the current attempt or the retained history.
assert.equal(status.observe(d.c).localOutcome,"");
assert.equal(status.recordLocalAbort(d.b,d.abortCode,d.stop[0].sequence,d.c).status,"STOP_REQUESTED");
assert.equal(status.observe(d.c).localOutcome,"");
// The disposable child fixture has independently verified the STEP result,
// durable ABORTED row, and absence of an assistant reply. Consume the whole
// actual batch before applying that typed local result; no inferred abort.
assert.equal(d.abortCode,"ABORTED_LOCAL");
assert.equal(d.abort.length,1);
assert.equal(d.abort[0].kind,"STATUS");
assert.equal(d.abort[0].statusPacket.status,"UNKNOWN_HOLD");
assert.equal(d.abort[0].sequence,d.stop[0].sequence+1);
const unresolved=deliver(d.c,d.abort);
assert.equal(unresolved.status,"UNKNOWN_HOLD");
assert.equal(unresolved.localOutcome,"");
assert.equal(unresolved.label,"UNKNOWN HOLD // NO AUTOMATIC RETRY");
assert.equal(JSON.stringify(history.observe(d.h3).messages),JSON.stringify(full.messages));
const settled=status.recordLocalAbort(d.c,d.abortCode,d.abort[0].sequence,d.c);
assert.equal(settled.localOutcome,"ABORTED_LOCAL");
assert.equal(settled.label,"LOCAL ABORT RECORDED // DELIVERY UNCONFIRMED");
for(const k of ["sourceAuthenticated","permissionGranted","productionAuthority","modelExecutionPermitted","sendEnabled","stopEnabled"])
    assert.equal(settled[k],false);
assert.equal(settled.safeActions.length,0);
assert.equal(JSON.stringify(history.observe(d.h3).messages),JSON.stringify(full.messages));
assert.equal(status.observe(null).state,"CLOSED");
assert.equal(status.observe(d.c).localOutcome,"");
console.log("UI2_R6D_CHILD_CONSUMER_PASS");
