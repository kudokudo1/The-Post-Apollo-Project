"use strict";

/** M12e callback ambiguity lab: simulated ordering + unmounted native QML. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { callbackTranscript, CallbackAttributionProbe, digest } =
  require("./fixtures/TaskCallbackAttributionM12e.cjs");

const ROOT = path.resolve(__dirname, "../..");
const OLD = { version: 3, projects: [], tasks: [{id:"t1", title:"M12E_CONFIRMED"}] };
const NEXT = { version: 3, projects: [], tasks: [{id:"t1", title:"M12E_PENDING"}] };
const OLD_RAW = JSON.stringify(OLD) + "\n";
const NEXT_RAW = JSON.stringify(NEXT) + "\n";
const OWNER = {sessionId:"m12e-session-00001", epoch:11, generation:8, fixtureOnly:true};
const STAGE = "m12e-stage-00001";
function fresh() {
  const model = new CallbackAttributionProbe(OLD_RAW, OLD);
  assert.equal(model.attach(OWNER), true);
  return model;
}
function queue(model) {
  assert.equal(model.stage({
    stageId:STAGE, raw:NEXT_RAW, candidate:NEXT,
    baselineHash:digest(OLD_RAW)
  }),true);
}
function reserve(model, extra={}) {
  return model.reserve({
    kind:"RESERVED", stageId:STAGE, sessionId:OWNER.sessionId,
    epoch:OWNER.epoch, generation:OWNER.generation,
    baselineHash:digest(OLD_RAW), expectedHash:digest(NEXT_RAW),
    durableFixtureReservation:true,...extra
  });
}
function ticket(extra={}) {
  return {
    stageId:STAGE, sessionId:OWNER.sessionId,
    epoch:OWNER.epoch, generation:OWNER.generation,...extra
  };
}
function settle(model, extra={}) {
  return model.settle({
    kind:"SETTLED",stageId:STAGE,sessionId:OWNER.sessionId,
    epoch:OWNER.epoch,generation:OWNER.generation,
    baselineHash:digest(OLD_RAW),actualSourceHash:digest(NEXT_RAW),
    expectedHash:digest(NEXT_RAW),journalSettled:true,testOnly:true,...extra
  });
}
function retained(model, phase="RECOVERY_REVIEW") {
  const snap=model.snapshot();
  assert.equal(snap.phase,phase);
  assert.equal(snap.writable,false);
  assert.equal(snap.confirmed.tasks[0].title,"M12E_CONFIRMED");
  assert.equal(snap.nativeCallbackAloneConfirmsNothing,true);
  assert.equal(snap.productionWriterAuthorized,false);
}

test("two distinct physical source stages generate identical native FileView events", () => {
  const current=callbackTranscript("current");
  const previous=callbackTranscript("stale");
  assert.notEqual(current.physicalOrigin,previous.physicalOrigin);
  assert.deepEqual(current.observable,previous.observable);
  assert.equal(current.observable.every(item=>!Object.hasOwn(item,"stageId")),true);
  assert.equal(current.observable.every(item=>!Object.hasOwn(item,"epoch")),true);
  assert.equal(current.observable.every(item=>!Object.hasOwn(item,"sessionId")),true);
  // A callback-only algorithm sees the same inputs in both physical worlds.
  // It cannot safely decide to publish a candidate in one but not the other.
});

test("default disconnected model never grants TASKS authority or native success", () => {
  const model=new CallbackAttributionProbe(OLD_RAW,OLD);
  assert.equal(model.snapshot().phase,"DISCONNECTED");
  assert.equal(model.snapshot().writable,false);
  assert.equal(model.nativeEvent("FILE_SAVED"),false);
  assert.equal(model.snapshot().confirmed.tasks[0].title,"M12E_CONFIRMED");
  assert.equal(model.stage({}),false);
});

test("queued stage then native onSaved before reservation is quarantined", () => {
  const model=fresh();queue(model);
  assert.equal(model.nativeEvent("FILE_SAVED"),false);
  retained(model);
  assert.equal(model.snapshot().reason,"NATIVE_CALLBACK_AMBIGUOUS");
  assert.equal(reserve(model),false);
});

test("admitted callback and tag-only readback never publish", () => {
  const model=fresh();queue(model);
  assert.equal(reserve(model),true);
  model.nativeEvent("FILE_SAVED");
  model.nativeEvent("FILE_READBACK_OK");
  model.nativeEvent("HOST_SETTLED");
  const s=model.snapshot();
  assert.equal(s.phase,"RESERVED");
  assert.equal(s.confirmed.tasks[0].title,"M12E_CONFIRMED");
  assert.equal(s.writable,false);
});

test("exact deferred raw readback + matching mock durable settlement promotes once", () => {
  const model=fresh();queue(model);
  assert.equal(reserve(model),true);
  model.nativeEvent("FILE_SAVED");
  assert.equal(model.readback(ticket(),NEXT_RAW),true);
  assert.equal(model.snapshot().phase,"VERIFYING");
  assert.equal(model.snapshot().confirmed.tasks[0].title,"M12E_CONFIRMED");
  assert.equal(settle(model),true);
  const confirmed=model.snapshot();
  assert.equal(confirmed.phase,"READY");
  assert.equal(confirmed.confirmed.tasks[0].title,"M12E_PENDING");
  assert.equal(confirmed.confirmedHash,digest(NEXT_RAW));
  assert.equal(confirmed.productionWriterAuthorized,false);
  assert.equal(settle(model),false);
  assert.equal(model.snapshot().confirmed.tasks[0].title,"M12E_PENDING");
});

test("wrong native readback bytes quarantine without publishing", () => {
  const model=fresh();queue(model);assert.equal(reserve(model),true);
  model.nativeEvent("FILE_SAVED");
  assert.equal(model.readback(ticket(),OLD_RAW),false);
  retained(model);
  assert.equal(model.snapshot().reason,"DEFERRED_READBACK_UNCERTAIN");
  assert.equal(settle(model),false);
});

test("stale ticket (stage, session, epoch, generation) cannot read back", () => {
  for(const changes of [
    {stageId:"m12e-stale-stage"},{sessionId:"m12e-stale-session"},
    {epoch:12},{generation:9}
  ]) {
    const model=fresh();queue(model);
    assert.equal(reserve(model),true);
    model.nativeEvent("FILE_SAVED");
    assert.equal(model.readback(ticket(changes),NEXT_RAW),false);
    retained(model);
  }
});

test("second or extra onSaved during reserved stage fails closed", () => {
  const model=fresh();queue(model);assert.equal(reserve(model),true);
  model.nativeEvent("FILE_SAVED");
  model.nativeEvent("FILE_SAVED");
  retained(model);
  assert.equal(model.snapshot().reason,"NATIVE_CALLBACK_AMBIGUOUS");
  assert.equal(settle(model),false);
});

test("wrong reserved stage, session, epoch, generation or hash quarantines", () => {
  for(const change of [
    {stageId:"m12e-different-stage"},{sessionId:"m12e-different-session"},
    {epoch:10},{generation:7},{baselineHash:"0".repeat(64)},
    {expectedHash:"f".repeat(64)},{durableFixtureReservation:false}
  ]) {
    const model=fresh();queue(model);
    assert.equal(reserve(model,change),false);
    retained(model);
    assert.equal(model.snapshot().reason,"RESERVATION_UNCERTAIN");
  }
});

test("wrong mock settlement cannot promote, even with valid deferred source bytes", () => {
  for(const change of [
    {stageId:"m12e-stale-stage"},{sessionId:"m12e-stale-session"},
    {epoch:12},{generation:9},{baselineHash:"0".repeat(64)},
    {expectedHash:"f".repeat(64)},{actualSourceHash:"a".repeat(64)},
    {journalSettled:false},{testOnly:false},{kind:"READBACK"}
  ]) {
    const model=fresh();queue(model);assert.equal(reserve(model),true);
    model.nativeEvent("FILE_SAVED");
    assert.equal(model.readback(ticket(),NEXT_RAW),true);
    assert.equal(settle(model,change),false);
    retained(model);
    assert.equal(model.snapshot().reason,"HOST_SETTLEMENT_UNCERTAIN");
  }
});

test("native load/save errors and host exit preserve last confirmed", () => {
  for(const tag of [
    "FILE_SAVE_FAILURE","FILE_LOAD_FAILED","FILE_READBACK_MISMATCH","HOST_EXIT"
  ]) {
    const model=fresh();queue(model);assert.equal(reserve(model),true);
    model.nativeEvent(tag);
    retained(model);
    assert.equal(settle(model),false);
  }
});

test("freeze while pending is review-only; no auto replay", () => {
  const model=fresh();queue(model);assert.equal(reserve(model),true);
  model.freeze();retained(model);
  assert.equal(model.snapshot().reason,"EXPLICIT_FREEZE_REVIEW");
  assert.equal(model.attach(OWNER),false);
  assert.equal(settle(model),false);
});

test("returned confirmed snapshot cannot mutate stored confirmed document", () => {
  const model=fresh();
  const returned=model.snapshot();
  returned.confirmed.tasks[0].title="TAMPER";
  assert.equal(model.snapshot().confirmed.tasks[0].title,"M12E_CONFIRMED");
});

test("native observer reuses M11g, remains unmounted and displays non-attestation", () => {
  const source=fs.readFileSync(path.join(
    ROOT,"tests/tasks/fixtures/TaskNativeCallbackLabM12e.qml"),"utf8");
  const existing=fs.readFileSync(path.join(
    ROOT,"services/projects/TaskFileViewHostBridgeM11g.qml"),"utf8");
  const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
  const production=fs.readFileSync(path.join(
    ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
  assert.ok(source.includes('import "../../../services/projects"'));
  assert.ok(source.includes("TaskFileViewHostBridgeM11g {"));
  assert.ok(source.includes("onObserved: lab.capture()"));
  assert.ok(source.includes("bridge.nativeSummary.saveChains"));
  assert.ok(source.includes("bridge.nativeRecent"));
  assert.ok(source.includes("NATIVE STAGE ATTRIBUTION: NOT PROVEN"));
  for(const s of [
    "liveWriterAuthorized: false", "productionActivation: false",
    "sqliteTaskMigrationAuthorized: false","nativeStageAttributionProven: false",
    'model: ["NEW TEST", "EXISTING", "INCREMENT", "FREEZE", "STOP"]',
    "WlrKeyboardFocus.OnDemand", "exclusiveZone: 0"
  ]) assert.ok(source.includes(s),s);
  for(const forbidden of [
    "FileView {","Process {","Quickshell.dataDir",
    "apollo-hub-todo-v1.json","Component.onCompleted:",
    "TaskSignedOwnerBoundaryM12d","Qt.openUrlExternally"
  ]) assert.ok(!source.includes(forbidden),forbidden);
  assert.equal((existing.match(/\bFileView\s*\{/g)||[]).length,1);
  assert.ok(existing.includes("Qt.callLater(function()"));
  assert.ok(existing.includes("fixtureFile.reload();"));
  assert.ok(existing.includes('bridge.observeNative("FILE_SAVED")'));
  assert.ok(existing.includes('bridge.observeNative("FILE_READBACK_OK")'));
  assert.ok(existing.includes('observeNative("HOST_SETTLED")'));
  for(const forbidden of [
    "TaskNativeCallbackLabM12e","TaskCallbackAttributionM12e"
  ]) assert.ok(!shell.includes(forbidden)&&!production.includes(forbidden));
  assert.ok(production.includes("readonly property bool guardedWriterEnabled: false"));
  assert.equal((production.match(/\bFileView\s*\{/g)||[]).length,1);
  assert.equal((production.match(/return stage\(TodoPolicy\./g)||[]).length,9);
});
