#!/usr/bin/env node
"use strict";
// No real files. Tests the exact state transitions imported by the QML gate.
const fs=require("node:fs"),vm=require("node:vm");
const assert=require("node:assert/strict");
const path="services/projects/TaskFileViewGatePolicyM11e.js";
const source=fs.readFileSync(path,"utf8").replace(/^\.pragma library\s*$/m,"");
const policy=vm.createContext({Date,JSON,Object,Array,Number,String,Math,RegExp});
vm.runInContext(source,policy,{filename:path});

const fixture=JSON.stringify({
    fixture:"M11E_SYNTHETIC_ONLY",revision:0,counter:0,marker:"sample"
})+"\n";
function ready() {
    const n=policy.start(policy.idle());
    assert.equal(n.accepted,true);
    assert.equal(n.state.phase,"LOADING");
    assert.equal(policy.writable(n.state),false);
    const r=policy.onLoaded(n.state,fixture);
    assert.equal(r.phase,"READY");
    assert.equal(policy.writable(r),true);
    assert.equal(r.document.counter,0);
    return r;
}
function refusal(state) {
    assert.equal(policy.writable(state),false);
    assert.equal(state.phase,"RECOVERY_REVIEW");
    assert.equal(state.freezeRequested,true);
    assert.equal(policy.requestStage(state).accepted,false);
    assert.equal(policy.requestReload(state).accepted,false);
    assert.equal(policy.requestFreeze(state).accepted,false);
}
const original=ready();
const before=JSON.stringify(original);
let batch=policy.requestStage(original);
assert.equal(batch.accepted,true);
assert.equal(batch.token,1);
assert.equal(batch.state.phase,"SAVING");
assert.equal(batch.state.document.counter,0);
assert.equal(batch.state.pending.counter,1);
assert.equal(policy.requestStage(batch.state).accepted,false);
assert.equal(policy.requestReload(batch.state).accepted,false);
assert.equal(JSON.stringify(original),before); // immutable policy
let saved=policy.onSaved(batch.state);
assert.equal(saved.phase,"VERIFYING");
assert.equal(saved.document.counter,0);
assert.equal(policy.requestStage(saved).accepted,false);
assert.equal(policy.onSaved(saved).phase,"RECOVERY_REVIEW");
let committed=policy.onLoaded(saved,batch.raw);
assert.equal(committed.phase,"READY");
assert.equal(committed.document.counter,1);
assert.equal(committed.completed,1);
assert.equal(committed.pending,null);
assert.equal(committed.activeToken,null);
assert.equal(policy.writable(committed),true);
let second=policy.requestStage(committed);
assert.equal(second.token,2);
assert.equal(second.state.document.counter,1);
let half=policy.requestFreeze(second.state);
assert.equal(half.accepted,true);
assert.equal(half.state.phase,"SAVING");
assert.equal(half.state.freezeRequested,true);
assert.equal(policy.requestStage(half.state).accepted,false);
let verifying=policy.onSaved(half.state);
let frozen=policy.onLoaded(verifying,second.raw);
assert.equal(frozen.phase,"FROZEN");
assert.equal(frozen.document.counter,2);
assert.equal(frozen.completed,2);
assert.equal(policy.writable(frozen),false);
assert.equal(policy.requestStage(frozen).accepted,false);
assert.equal(policy.requestReload(frozen).accepted,false);
assert.equal(policy.requestFreeze(frozen).accepted,false);

// A new unconfirmed value NEVER publishes after a failure, regardless of
// whether the write reported saved but readback does not match exactly.
let base=ready(),staged=policy.requestStage(base);
let wrong=policy.onLoaded(policy.onSaved(staged.state),fixture);
refusal(wrong);
assert.equal(wrong.document.counter,0);
assert.equal(wrong.completed,0);
let bad=policy.onSaveFailed(staged.state);
refusal(bad);
assert.equal(bad.document.counter,0);
assert.equal(bad.completed,0);
refusal(policy.onLoadFailed(base));
refusal(policy.onSaved(base));
refusal(policy.onLoaded(base,fixture));
// Callback from initial loading while a save is in flight fails closed.
refusal(policy.onLoaded(staged.state,fixture));

// A user-triggered read checks against the exact last confirmed bytes,
// refusing an externally modified or missing file rather than reparsing
// that data into a writable document.
let reloaded=policy.requestReload(base);
assert.equal(reloaded.accepted,true);
assert.equal(reloaded.state.phase,"LOADING");
assert.equal(policy.writable(reloaded.state),false);
assert.equal(policy.onLoaded(reloaded.state,fixture).phase,"READY");
const externallyChanged=JSON.stringify({
    fixture:"M11E_SYNTHETIC_ONLY",revision:1,counter:1,marker:"sample"
})+"\n";
refusal(policy.onLoaded(reloaded.state,externallyChanged));
refusal(policy.onLoadFailed(reloaded.state));
const directFreeze=policy.requestFreeze(base);
assert.equal(directFreeze.accepted,true);
assert.equal(directFreeze.state.phase,"FROZEN");
assert.equal(directFreeze.state.document.counter,0);
assert.equal(policy.writable(directFreeze.state),false);
assert.equal(policy.requestStage(directFreeze.state).accepted,false);

// Exact fixture content, never generic TASKS JSON or unspecified versions.
const invalid=[
    "", "{}", "{broken",
    JSON.stringify({...JSON.parse(fixture),unexpected:true}),
    JSON.stringify({...JSON.parse(fixture),fixture:"REAL_TASKS"}),
    JSON.stringify({...JSON.parse(fixture),marker:"external"}),
    JSON.stringify({...JSON.parse(fixture),revision:1,counter:0}),
    JSON.stringify({...JSON.parse(fixture),revision:-1,counter:-1}),
    JSON.stringify({...JSON.parse(fixture),counter:1.5,revision:1.5}),
    "x".repeat(policy.MAX_BYTES+1)
];
for(const value of invalid) {
    assert.equal(policy.decode(value),null);
    refusal(policy.onLoaded(policy.start(policy.idle()).state,value));
}
assert.equal(policy.start(base).accepted,false);
assert.equal(policy.requestStage(policy.idle()).accepted,false);
assert.equal(policy.writable(policy.idle()),false);
console.log("M11e synthetic FileView state, async save readback, freeze, reload and fail-closed refusal: PASS");
