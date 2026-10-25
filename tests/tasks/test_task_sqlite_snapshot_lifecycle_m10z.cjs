#!/usr/bin/env node
"use strict";
// Test the exact pure lifecycle object used by the new unmounted QML bridge.
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const source=fs.readFileSync(
    "services/projects/TaskSqliteSnapshotLifecycleM10z.js","utf8")
    .replace(/^\.pragma library\s*$/m,"");
const ctx=vm.createContext({Number,String,Math,Object,Array});
vm.runInContext(source,ctx);
function run(order) {
    let flight=ctx.begin(ctx.idle());
    assert.equal(flight.active,true);
    assert.equal(flight.generation,1);
    assert.equal(ctx.begin(flight),null);
    for(const step of order) {
        if(step==="exit") flight=ctx.onExit(flight,0);
        else flight=ctx.onStreamFinished(flight,'{"protocol":1}');
        if(flight.exited && flight.streamed) break;
        assert.equal(ctx.outcome(flight).kind,"waiting");
    }
    assert.equal(ctx.outcome(flight).kind,"response");
    assert.equal(ctx.outcome(flight).text,'{"protocol":1}');
    flight=ctx.settle(flight);
    assert.equal(flight.active,false);
    assert.equal(flight.stdout,"");
    let fresh=ctx.begin(flight);
    assert.equal(fresh.generation,2);
    assert.equal(ctx.outcome(fresh).kind,"waiting");
    return fresh;
}
let a=run(["exit","stream"]);
let b=run(["stream","exit"]);
assert.equal(a.generation,2);
assert.equal(b.generation,2);

// Cancel before ANY result, between the two possible signal orderings,
// and after stdout exists, must discard output and prevent publication.
for(const order of [
    [], ["exit"], ["stream"], ["stream","exit"], ["exit","stream"]
]) {
    let flight=ctx.begin(ctx.idle());
    for(const step of order)
        flight=step==="exit" ? ctx.onExit(flight,0)
            : ctx.onStreamFinished(flight,"private task description");
    flight=ctx.cancel(flight);
    flight=ctx.onExit(flight,0);
    flight=ctx.onStreamFinished(flight,"private task description");
    assert.equal(ctx.outcome(flight).kind,"cancelled");
    assert.equal(ctx.outcome(flight).text,undefined);
    let after=ctx.settle(flight);
    assert.equal(after.stdout,"");
    assert.equal(after.active,false);
    assert.equal(ctx.begin(after).generation,2);
}
let duplicate=ctx.begin(ctx.idle());
duplicate=ctx.onExit(duplicate,0);
assert.equal(ctx.onExit(duplicate,77).exitCode,0);
duplicate=ctx.onStreamFinished(duplicate,"first");
assert.equal(ctx.onStreamFinished(duplicate,"second").stdout,"first");

// Never publish failed or malformed subprocess outcomes.
for(const [exit,payload] of [[1,"{}"],[-1,"{}"],[0,""],
                             [0,"x".repeat(ctx.MAX_TEXT+1)]]) {
    let flight=ctx.begin(ctx.idle());
    flight=ctx.onStreamFinished(flight,payload);
    flight=ctx.onExit(flight,exit);
    assert.equal(ctx.outcome(flight).kind,"failed");
    assert.equal(ctx.settle(flight).active,false);
}
assert.equal(ctx.outcome(ctx.idle()).kind,"idle");
assert.equal(ctx.onStreamFinished(ctx.idle(),"secret").stdout,"");
assert.equal(ctx.onExit(ctx.idle(),0).exited,false);
console.log("M10z Quickshell subprocess callback ordering, cancellation, reset: PASS");
