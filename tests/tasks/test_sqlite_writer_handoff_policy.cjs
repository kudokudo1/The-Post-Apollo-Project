#!/usr/bin/env node
"use strict";
// Proxy 1 M10o: detached, synthetic handoff only. No live Quickshell,
// database migration, GitHub call, or real writer ownership changes.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const source=fs.readFileSync("services/projects/TaskSqliteWriterHandoffPolicy.js","utf8")
    .replace(/^\.pragma library\s*$/m,"");
const policy=vm.createContext({JSON,Array,Object,Number,String,RegExp,Math});
vm.runInContext(source,policy,{filename:"TaskSqliteWriterHandoffPolicy.js"});

const session="session-20261024-a123";
const oldWriter="json-writer-generation-18";
const SHA_A="a".repeat(64),SHA_B="b".repeat(64),SHA_C="c".repeat(64);
function ok(r,label) {
    assert.equal(r.ok,true,label+":"+r.reason);
    assert.equal(r.writeReady,false,label);
    assert.equal(r.sqliteWriteAuthorized,false,label);
    assert.equal(r.liveChangePerformed,false,label);
    return r.state;
}
function reject(r,reason) {
    assert.equal(r.ok,false,r.reason);
    assert.equal(r.reason,reason);
    assert.equal(r.writeReady,false);
    assert.equal(r.sqliteWriteAuthorized,false);
}
function view(s) {
    const v=policy.inspect(s);
    assert.equal(v.ok,true);
    assert.equal(v.writeReady,false);
    assert.equal(v.sqliteWriteAuthorized,false);
    assert.equal(v.activationAvailable,false);
    return v;
}
function gate(s) {
    const g=policy.gate(s);
    assert.equal(g.ok,true);
    assert.equal(g.sqliteWriteAuthorized,false);
    assert.equal(g.writeReady,false);
    return g;
}
// Mock guard ONLY: tests whether a hypothetical host checking the pure
// policy could admit both writes. This is NOT the real FileView.
function simulateHost(s) {
    const g=gate(s);
    const mayStageOld=g.legacyStagePermittedByContract;
    const mayWriteNew=g.sqliteWriteAuthorized;
    assert.equal(mayStageOld && mayWriteNew,false,"dual-writer authority");
    return {mayStageOld,mayWriteNew};
}
const zero=ok(policy.begin(session,oldWriter),"start");
assert.equal(zero.phase,"JSON_ACTIVE");
assert.equal(zero.sequence,0);
assert.equal(simulateHost(zero).mayStageOld,true);
assert.equal(view(zero).requiresOperator,true);
reject(policy.begin("short","short"),"INVALID_IDENTITIES");

const freeze=ok(policy.requestFreeze(zero,session,0),"request freeze");
assert.equal(freeze.phase,"FREEZE_REQUESTED");
assert.equal(freeze.sequence,1);
assert.equal(simulateHost(freeze).mayStageOld,false);
reject(policy.requestFreeze(zero,session,1),"STALE_SEQUENCE");
reject(policy.requestFreeze(freeze,session,1),"UNEXPECTED_PHASE");
reject(policy.requestFreeze(zero,"wrong-session",0),"STALE_SESSION");

// Existing FileView onSaved/onSaveFailed may not have fired yet.
// The freeze request must block all new stage calls, then drain in-flight.
const draining={writerId:oldWriter,stageGateClosed:true,pendingSave:true,
    saveCallbacksSettled:false,storageState:"saving",
    diskSha256:SHA_A,secondReadSha256:SHA_A};
reject(policy.observeDrain(freeze,session,1,draining),"WAIT_FOR_PENDING_SAVE");
assert.equal(simulateHost(freeze).mayStageOld,false);
reject(policy.observeDrain(freeze,session,1,
    {...draining,pendingSave:false,saveCallbacksSettled:true,
     stageGateClosed:false,storageState:"ready"}),"LEGACY_STAGE_GATE_NOT_CLOSED");
reject(policy.observeDrain(freeze,session,1,
    {...draining,pendingSave:false,saveCallbacksSettled:true,
     writerId:"other-writer",storageState:"ready"}),"LEGACY_STAGE_GATE_NOT_CLOSED");
reject(policy.observeDrain(freeze,session,1,
    {...draining,pendingSave:false,saveCallbacksSettled:false,
     storageState:"ready"}),"WAIT_FOR_PENDING_SAVE");
reject(policy.observeDrain(freeze,session,1,
    {...draining,pendingSave:false,saveCallbacksSettled:true,
     storageState:"error"}),"LEGACY_STORE_NOT_SETTLED");
reject(policy.observeDrain(freeze,session,1,
    {...draining,pendingSave:false,saveCallbacksSettled:true,
     storageState:"ready",secondReadSha256:SHA_B}),"SOURCE_READBACK_UNSTABLE");
const faulted=ok(policy.observeDrain(freeze,session,1,
    {...draining,saveFailed:true}),"failed file-save callback");
assert.equal(faulted.phase,"RECOVERY_REVIEW");
assert.equal(faulted.reason,"LEGACY_SAVE_FAILED");
assert.equal(simulateHost(faulted).mayStageOld,false);
reject(policy.observeDrain(faulted,session,2,draining),"UNEXPECTED_PHASE");

// A successful settled saved callback and matching double read is a
// prototype evidence receipt, not a real QML lock or disk authority.
const settled={...draining,pendingSave:false,saveCallbacksSettled:true,
    storageState:"ready",diskSha256:SHA_B,secondReadSha256:SHA_B};
const quiesced=ok(policy.observeDrain(freeze,session,1,settled),"drain");
assert.equal(quiesced.phase,"JSON_QUIESCED");
assert.equal(quiesced.sourceSha256,SHA_B);
assert.equal(quiesced.sequence,2);
assert.equal(simulateHost(quiesced).mayStageOld,false);
reject(policy.observeDrain(freeze,session,9,settled),"STALE_SEQUENCE");

// Shadow evidence must bind to the frozen *raw JSON* hash, exact v2
// model hash on both copies, revision zero, and zero blocked operations.
const proof={sourceSha256:SHA_B,candidateModelSha256:SHA_C,
    shadowModelSha256:SHA_C,sqliteBackupModelSha256:SHA_C,
    sqliteRevision:0,sqliteBackupRevision:0,blockedOperations:0,
    legacyWriterStillQuiesced:true};
for(const change of [
    {sourceSha256:SHA_A},{shadowModelSha256:SHA_A},
    {sqliteBackupModelSha256:SHA_A},{sqliteRevision:1},
    {sqliteBackupRevision:1},{blockedOperations:1},
    {legacyWriterStillQuiesced:false}
]) {
    reject(policy.verifyShadow(quiesced,session,2,{...proof,...change}),
           "SHADOW_PARITY_OR_FREEZE_NOT_PROVEN");
}
const verified=ok(policy.verifyShadow(quiesced,session,2,proof),"shadow");
assert.equal(verified.phase,"SHADOW_VERIFIED");
assert.equal(verified.shadowModelSha256,SHA_C);
assert.equal(simulateHost(verified).mayStageOld,false);
reject(policy.verifyShadow(verified,session,3,proof),"UNEXPECTED_PHASE");

const allEvidence=Object.fromEntries(Array.from(policy.REVIEW_FIELDS)
    .map(field=>[field,true]));
for(const key of Array.from(policy.REVIEW_FIELDS)) {
    reject(policy.prepareReview(verified,session,3,
        {...allEvidence,[key]:false}),"REVIEW_GATE_OPEN_"+key);
}
const approved=ok(policy.prepareReview(verified,session,3,allEvidence),
    "review complete, not activated");
assert.equal(approved.phase,"AWAITING_OPERATOR");
assert.equal(simulateHost(approved).mayStageOld,false);
assert.equal(simulateHost(approved).mayWriteNew,false);
assert.equal(view(approved).activationAvailable,false);
// Extra spoofed operator flags are NOT credentials for deployment.
const spoofed=ok(policy.prepareReview(verified,session,3,
    {...allEvidence,operatorApproved:true,activate:true,writeReady:true}),
    "spoofed flags ignored");
assert.equal(spoofed.phase,"AWAITING_OPERATOR");
assert.equal(view(spoofed).activationAvailable,false);

// Immutable and copy-based transitions, with no accidental live ownership.
assert.equal(zero.phase,"JSON_ACTIVE");
assert.equal(freeze.phase,"FREEZE_REQUESTED");
assert.equal(quiesced.phase,"JSON_QUIESCED");
assert.equal(verified.phase,"SHADOW_VERIFIED");
assert.equal(zero.sequence,0);
assert.equal(view(zero).legacyStagePermittedByContract,true);

// A process restart (including from old JSON_ACTIVE) always invalidates
// the session's presumed legacy staging capability.
for(const past of [zero,freeze,quiesced,verified,approved,faulted]) {
    const raw=policy.checkpoint(past);
    assert.equal(raw.ok,true);
    const resumed=ok(policy.restartFromCheckpoint(raw.raw),
        "restart invalidates phase "+past.phase);
    assert.equal(resumed.phase,"RECOVERY_REVIEW");
    assert.equal(resumed.reason,"SESSION_RESTART_REQUIRES_INSPECTION");
    assert.equal(simulateHost(resumed).mayStageOld,false);
    reject(policy.requestFreeze(resumed,session,resumed.sequence),
        "UNEXPECTED_PHASE");
}
reject(policy.restartFromCheckpoint("{garbage"),"INVALID_CHECKPOINT_JSON");
reject(policy.restartFromCheckpoint(JSON.stringify({...zero,phase:"SQLITE_ACTIVE"})),
    "INVALID_CHECKPOINT_STATE");
reject(policy.restartFromCheckpoint(JSON.stringify({...zero,
    sqliteWriteAuthorized:true})),"INVALID_CHECKPOINT_STATE");
reject(policy.restartFromCheckpoint(JSON.stringify({...zero,
    sessionId:"short"})),"INVALID_CHECKPOINT_STATE");
reject(policy.restartFromCheckpoint(JSON.stringify({...zero,
    sourceSha256:SHA_A})),"INVALID_CHECKPOINT_STATE");

// Fault after any evidence/review phase refuses automatic re-enable.
for(const state of [freeze,quiesced,verified,approved]) {
    const blocked=ok(policy.fault(state,session,state.sequence,"TEST_CRASH"),
        "abnormal termination");
    assert.equal(blocked.phase,"RECOVERY_REVIEW");
    assert.equal(simulateHost(blocked).mayStageOld,false);
    assert.equal(simulateHost(blocked).mayWriteNew,false);
}
reject(policy.fault(freeze,session,0,"TEST_CRASH"),
       "STALE_OR_UNEXPECTED_SESSION");
reject(policy.fault(freeze,session,1,"bad reason"),
       "INVALID_FAULT_REASON");

// Fail closed before any actor uses the record to gate writes.
assert.equal(policy.gate({phase:"JSON_ACTIVE"}).ok,false);
assert.equal(policy.gate({phase:"JSON_ACTIVE"}).legacyStagePermittedByContract,
             false);
for(const forbidden of [
    "FileView {","Process {","Quickshell.execDetached(","setText(",
    "fetch(","XMLHttpRequest","require(","sqlite3.connect",
    "GitHubProjectsService {","function activate(","function writeSqlite("
]) assert.ok(!source.includes(forbidden),"side effect: "+forbidden);
console.log("TASKS M10o pure single-writer freeze/drain/shadow-review/restart contract: PASS");
