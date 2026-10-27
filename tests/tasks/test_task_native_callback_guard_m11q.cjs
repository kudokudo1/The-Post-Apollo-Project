#!/usr/bin/env node
"use strict";
// Exercise the pure helper that the M11m Quickshell standalone bridge imports.
// No FileView, user task files, network or host process is started here.
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
function load(file) {
    const src=fs.readFileSync(file,"utf8").replace(/^\.pragma library\s*$/m,"");
    const ctx=vm.createContext({Number,JSON,Array,Object,Math});
    vm.runInContext(src,ctx,{filename:file});
    return ctx;
}
const guard=load("services/projects/TaskJsonNativeCallbackGuardM11q.js");
const evidence=load("services/projects/TaskFileViewNativeEvidenceM11i.js");
const qml=fs.readFileSync("services/projects/TaskJsonGateHostBridgeM11m.qml","utf8");
const panel=fs.readFileSync("TaskJsonGateHarnessM11m.qml","utf8");
const store=fs.readFileSync("services/hub/ApolloHubTodoStore.qml","utf8");
const shell=fs.readFileSync("shell.qml","utf8");
const active={
    attached:true,connected:true,hostRunning:true,
    fileState:"VERIFYING",pendingRaw:'{"synthetic":true}\n',
    pendingStageId:"m11q-stage-001",fixturePath:"/synthetic/m11l-tasks-copy/todo-copy.json",
    generation:5,epoch:2
};
const ticket=guard.ticket(active.generation,active.epoch,
                          active.pendingStageId,active.fixturePath);
assert.equal(guard.canDeferredReadback(active,ticket),true);
for(const change of [
    {attached:false}, {connected:false}, {hostRunning:false},
    {fileState:"RECOVERY_REVIEW"}, {fileState:"SAVING"},
    {pendingRaw:""}, {pendingStageId:""},
    {pendingStageId:"m11q-stage-002"}, {generation:6}, {epoch:3},
    {fixturePath:"/synthetic/m11l-tasks-copy/other.json"},
    {generation:null}, {epoch:null}
]) {
    const state={...active,...change};
    assert.equal(guard.canDeferredReadback(state,ticket),false,
                 JSON.stringify(change));
}
for(const mutation of [
    {generation:6}, {epoch:3}, {stageId:"m11q-stage-002"},
    {fixturePath:"/synthetic/m11l-tasks-copy/other.json"}
]) {
    assert.equal(guard.canDeferredReadback(active,{...ticket,...mutation}),
                 false,JSON.stringify(mutation));
}
assert.equal(guard.canDeferredReadback(null,ticket),false);
assert.equal(guard.canDeferredReadback(active,null),false);
const settled={
    attached:true,connected:true,hostRunning:true,
    fileState:"SETTLING",pendingRaw:active.pendingRaw,
    pendingStageId:active.pendingStageId,epoch:2
};
const receipt={kind:"verify",ok:true,phase:"JSON_ACTIVE",pending:false,
               stageId:active.pendingStageId,epoch:2};
assert.equal(guard.settledReplyEligible(settled,receipt,2),true);
for(const [stateDelta,replyDelta,expectedEpoch] of [
    [{connected:false},{},2], [{hostRunning:false},{},2],
    [{fileState:"VERIFYING"},{},2], [{pendingStageId:"other"},{},2],
    [{pendingRaw:""},{},2], [{epoch:3},{},2],
    [{},{kind:"reserve"},2], [{},{ok:false},2],
    [{},{pending:true},2], [{},{phase:"RECOVERY_REVIEW"},2],
    [{},{stageId:"stale"},2], [{},{epoch:3},2],
    [{},{},3]
]) {
    assert.equal(guard.settledReplyEligible({...settled,...stateDelta},
        {...receipt,...replyDelta},expectedEpoch),false);
}
function chain(record,tag,phase="JSON_ACTIVE") {
    return evidence.append(record,tag,phase);
}
let state=evidence.empty();
for(const tag of ["ATTACH_REQUEST","HOST_HELLO","FILE_INITIAL_LOAD",
    "STAGE_REQUEST","HOST_ADMIT","FILE_SAVED",
    "FILE_READBACK_OK","HOST_SETTLED",
    "STAGE_REQUEST","HOST_ADMIT","FILE_SAVED",
    "FILE_READBACK_OK","HOST_SETTLED","FREEZE_REQUEST","HOST_FROZEN"])
    state=chain(state,tag);
let summary=evidence.summarize(state);
assert.equal(summary.saveChains,2);
assert.equal(summary.frozen,true);
assert.equal(summary.recoveryObserved,false);
assert.equal(summary.label,"OBSERVATION_ONLY_NOT_NATIVE_ACCEPTED");
state=chain(state,"HOST_EXIT","RECOVERY_REVIEW");
summary=evidence.summarize(state);
assert.equal(summary.saveChains,2);
assert.equal(summary.recoveryObserved,true);
assert.equal(state.events.some(e=>e.stageId!==undefined),false);
for(const bad of [
    ["STAGE_REQUEST","HOST_ADMIT","FILE_SAVED","HOST_EXIT","FILE_READBACK_OK","HOST_SETTLED"],
    ["STAGE_REQUEST","HOST_ADMIT","FILE_SAVE_FAILURE","FILE_SAVED","FILE_READBACK_OK","HOST_SETTLED"],
    ["STAGE_REQUEST","HOST_ADMIT","FILE_SAVED","FILE_READBACK_MISMATCH","FILE_READBACK_OK","HOST_SETTLED"]
]) {
    let rec=evidence.empty();
    for(const tag of bad) rec=chain(rec,tag);
    assert.equal(evidence.summarize(rec).saveChains,0,bad.join("/"));
}
// These source checks ensure Qt actually imports the exercised policy; tests
// never claim they drove a native Quickshell FileView.
for(const text of [
    'import "TaskJsonNativeCallbackGuardM11q.js" as CallbackGuard',
    'import "TaskFileViewNativeEvidenceM11i.js" as NativeEvidence',
    'CallbackGuard.canDeferredReadback({',
    'CallbackGuard.settledReplyEligible({',
    'var savedTicket = CallbackGuard.ticket(',
    'bridge.sessionGeneration',
    'var previousEpoch = epoch;',
    'reply.epoch !== previousEpoch + 1',
    'Qt.callLater(function()',
    'bridge.event("FILE_READBACK_MISMATCH")',
    'bridge.event("FILE_LOAD_FAILED")',
    'function maybeSyntheticFault(point)',
    'if (maybeSyntheticFault("AFTER_RESERVE")) return;',
    'if (bridge.maybeSyntheticFault("AFTER_SAVED")) return;',
    'if (bridge.maybeSyntheticFault("AFTER_READBACK")) return;',
    'if (maybeSyntheticFault("AFTER_SETTLEMENT")) return;'
]) assert.ok(qml.includes(text),text);
assert.ok(panel.includes('"ARM FAULT"'));
assert.ok(panel.includes("bridge.cycleSyntheticFault()"));
assert.ok(panel.includes("bridge.nativeSummary.saveChains"));
assert.ok(panel.includes("bridge.nativeRecent"));
assert.ok(!shell.includes("TaskJsonGateHostBridgeM11m"));
assert.ok(!shell.includes("TaskJsonNativeCallbackGuardM11q"));
assert.ok(!store.includes("TaskJsonGateHostBridgeM11m"));
assert.ok(!store.includes("TaskJsonNativeCallbackGuardM11q"));
assert.ok(store.includes("readonly property bool guardedWriterEnabled: false"));
assert.equal(store.split("FileView {").length-1,1);
assert.equal(store.split("todoFile.setText(").length-1,1);
console.log("M11q exact-native-ticket callback guard, evidence, fault gates and no-mount: PASS");
