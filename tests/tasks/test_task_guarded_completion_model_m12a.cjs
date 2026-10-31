"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { SyntheticGuardedModel, sha } =
  require("./fixtures/TaskGuardedCompletionModelM12a.cjs");

const doc = (title = "M12A_LAST_CONFIRMED") => ({
  version: 3, nextId: 2, nextProjectId: 1, projects: [],
  tasks: [{
    id: "t1", title, done: false, createdAtMs: 1000,
    updatedAtMs: 1000, priority: "none", description: "",
    dueDate: null, projectId: null
  }]
});
const STAGE = "m12a-stage-000001";
const SESSION = "m12a-session-000001";
function connect(model, overrides = {}) {
  return model.attachSyntheticOwner({
    testOnly: true, sessionId: SESSION, epoch: 7, generation: 3,
    baselineHash: sha(doc()),
    testTrustCheck: true, testBackupReadback: true,
    ...overrides
  });
}
function baseline() {
  const model = new SyntheticGuardedModel(doc());
  assert.equal(connect(model), true);
  return model;
}
function queued(model, title = "M12A_CANDIDATE") {
  const candidate = doc(title);
  const ticket = model.request({ ok: true, document: candidate }, STAGE);
  assert.deepEqual(ticket, { queued: true, admitted: false, saved: false });
  return candidate;
}
function reservation(model, candidate, overrides = {}) {
  return model.reservation({
    kind: "RESERVED", stageId: STAGE, sessionId: SESSION,
    epoch: 7, generation: 3,
    beforeHash: sha(doc()), expectedHash: sha(candidate),
    durablyReserved: true, ...overrides
  });
}
function settlement(model, candidate, overrides = {}) {
  return model.settlement({
    kind: "SETTLED", stageId: STAGE, sessionId: SESSION,
    epoch: 7, generation: 3,
    beforeHash: sha(doc()), expectedHash: sha(candidate),
    actualReadbackHash: sha(candidate),
    journalSettled: true, testOnly: true, ...overrides
  });
}
function assertOldReadOnly(model, phase = "RECOVERY_REVIEW") {
  const snap = model.snapshot();
  assert.equal(snap.phase, phase);
  assert.equal(snap.writable, false);
  assert.equal(snap.confirmed.tasks[0].title, "M12A_LAST_CONFIRMED");
  assert.equal(snap.items[0].title, "M12A_LAST_CONFIRMED");
  assert.equal(snap.productionWriterAuthorized, false);
  return snap;
}

test("guard starts disabled with last-confirmed rows visible and no write admission", () => {
  const m = new SyntheticGuardedModel(doc());
  assert.equal(m.phase, "DISCONNECTED");
  assert.equal(m.snapshot().writable, false);
  assert.equal(m.snapshot().items[0].title, "M12A_LAST_CONFIRMED");
  assert.deepEqual(m.request({ ok: true, document: doc("x") }, STAGE),
    { queued: false, admitted: false, saved: false });
  assert.equal(m.nativeCallback("onSaved"), false);
  assert.equal(SyntheticGuardedModel.productionWriterAuthorized, false);
});

test("refuses missing test trust/backup proofs and inaccurate baseline", () => {
  for (const wrong of [
    { testTrustCheck: false }, { testBackupReadback: false },
    { baselineHash: "0".repeat(64) }, { testOnly: false },
    { sessionId: "short" }, { epoch: -1 }, { generation: 0 }
  ]) {
    const m = new SyntheticGuardedModel(doc());
    assert.equal(connect(m, wrong), false);
    assertOldReadOnly(m);
    assert.equal(m.snapshot().error, "SYNTHETIC_PREFLIGHT_REFUSED");
    assert.equal(connect(m), false); // No automatic recovery.
  }
});

test("queued means neither admitted nor saved, and never publishes candidate", () => {
  const m = baseline();
  const candidate = queued(m);
  assert.equal(m.snapshot().state, "saving");
  assert.equal(m.phase, "RESERVING");
  assertOldReadOnly(m, "RESERVING");
  assert.equal(m.snapshot().confirmedHash, sha(doc()));
  assert.equal(m.nativeCallback("onSaved"), false); // before reservation
  assert.equal(m.settlement({
    kind: "SETTLED", testOnly: true
  }), false);
  assert.equal(m.snapshot().items[0].title, "M12A_LAST_CONFIRMED");
  assert.deepEqual(m.request({ ok: true, document: candidate }, "m12a-new-stage-02"),
    { queued: false, admitted: false, saved: false });
});

test("durable reservation is the earliest synthetic permission to write, not publish", () => {
  const m = baseline();
  const candidate = queued(m);
  assert.equal(reservation(m, candidate), true);
  assert.equal(m.phase, "RESERVED");
  assertOldReadOnly(m, "RESERVED");
  for (const callback of ["onSaved","onLoaded","onSaved","onLoaded"]) {
    assert.equal(m.nativeCallback(callback), false);
    assertOldReadOnly(m, "RESERVED");
  }
});

test("only a precisely matched settled host record promotes confirmed content", () => {
  const m = baseline();
  const candidate = queued(m);
  assert.equal(reservation(m, candidate), true);
  assert.equal(m.nativeCallback("onSaved"), false);
  assert.equal(settlement(m, candidate), true);
  assert.equal(m.phase, "READY");
  assert.equal(m.snapshot().state, "ready");
  assert.equal(m.snapshot().writable, true);
  assert.equal(m.snapshot().items[0].title, "M12A_CANDIDATE");
  assert.equal(m.snapshot().confirmedHash, sha(candidate));
  assert.equal(m.snapshot().pending, false);
  assert.equal(settlement(m, candidate), false);
  assert.equal(m.snapshot().items[0].title, "M12A_CANDIDATE");
});

test("settlement without a native callback can still be evaluated by host record", () => {
  // Native onSaved has no durable stage ID. It is not a security proof.
  const m = baseline();
  const candidate = queued(m);
  assert.equal(reservation(m, candidate), true);
  assert.equal(settlement(m, candidate), true);
});

test("wrong reservation stage, owner epoch, hash or non-durable frame quarantines", () => {
  const variants = [
    { stageId: "m12a-foreign-stage" },
    { sessionId: "m12a-foreign-session" }, { epoch: 8 },
    { generation: 4 }, { beforeHash: "a".repeat(64) },
    { expectedHash: "0".repeat(64) }, { durablyReserved: false },
    { kind: "SAVED" }
  ];
  for (const variant of variants) {
    const m = baseline();
    const candidate = queued(m);
    assert.equal(reservation(m, candidate, variant), false);
    const snap = assertOldReadOnly(m);
    assert.equal(snap.error, "STAGE_RESERVATION_UNCERTAIN");
    assert.equal(settlement(m, candidate), false);
  }
});

test("wrong settlement, readback mismatch, replay or stale owner never publishes", () => {
  const variants = [
    { stageId: "m12a-stale-stage" }, { sessionId: "m12a-stale-session" },
    { epoch: 8 }, { generation: 2 }, { beforeHash: "0".repeat(64) },
    { expectedHash: "0".repeat(64) }, { actualReadbackHash: "0".repeat(64) },
    { journalSettled: false }, { testOnly: false }, { kind: "READBACK" }
  ];
  for (const variant of variants) {
    const m = baseline();
    const candidate = queued(m);
    assert.equal(reservation(m, candidate), true);
    assert.equal(settlement(m, candidate, variant), false);
    const snap = assertOldReadOnly(m);
    assert.equal(snap.error, "SETTLEMENT_UNCERTAIN");
    assert.equal(settlement(m, candidate), false);
  }
});

test("onSaveFailed and onLoadFailed require review while preserving confirmed rows", () => {
  for (const callback of ["onSaveFailed", "onLoadFailed"]) {
    const m = baseline();
    const candidate = queued(m);
    assert.equal(reservation(m, candidate), true);
    assert.equal(m.nativeCallback(callback), false);
    const snap = assertOldReadOnly(m);
    assert.equal(snap.error, "NATIVE_IO_UNCERTAIN");
    assert.equal(settlement(m, candidate), false);
  }
});

test("host exit after each pending boundary preserves old snapshot and blocks replay", () => {
  for (const afterReserve of [false, true]) {
    const m = baseline();
    const candidate = queued(m);
    if (afterReserve) assert.equal(reservation(m, candidate), true);
    assert.equal(m.hostExit(), false);
    const snap = assertOldReadOnly(m);
    assert.equal(snap.error, "FRESH_OWNER_REVIEW_REQUIRED");
    assert.equal(m.attachSyntheticOwner({
      testOnly: true, sessionId: "m12a-new-session-001", epoch: 8,
      generation: 4, baselineHash: sha(doc()), testTrustCheck: true,
      testBackupReadback: true
    }), false);
    assert.equal(settlement(m, candidate), false);
  }
});

test("even settled content cannot treat a new process as automatic same owner", () => {
  const m = baseline();
  const candidate = queued(m);
  assert.equal(reservation(m, candidate), true);
  assert.equal(settlement(m, candidate), true);
  assert.equal(m.hostExit(), false);
  const snap = m.snapshot();
  assert.equal(snap.phase, "RECOVERY_REVIEW");
  assert.equal(snap.items[0].title, "M12A_CANDIDATE");
  assert.equal(snap.writable, false);
});

test("freeze without a pending stage is read-only and no automatic resume exists", () => {
  const m = baseline();
  assert.equal(m.freeze(), true);
  assert.equal(m.phase, "FROZEN");
  assertOldReadOnly(m, "FROZEN");
  assert.deepEqual(m.request({ ok: true, document: doc("new") }, STAGE),
    { queued: false, admitted: false, saved: false });
  assert.equal(m.attachSyntheticOwner({
    testOnly: true, sessionId: SESSION, epoch: 8, generation: 4,
    baselineHash: sha(doc()), testTrustCheck: true,
    testBackupReadback: true
  }), false);
});

test("freeze with pending stage quarantines rather than silently draining", () => {
  const m = baseline();
  const candidate = queued(m);
  assert.equal(reservation(m, candidate), true);
  assert.equal(m.freeze(), false);
  const snap = assertOldReadOnly(m);
  assert.equal(snap.error, "FREEZE_WITH_PENDING_STAGE");
  assert.equal(settlement(m, candidate), false);
});

test("invalid policy result, unchanged content and invalid stage IDs refuse", () => {
  const m = baseline();
  const expected = { queued: false, admitted: false, saved: false };
  assert.deepEqual(m.request({ ok: false, document: doc("new") }, STAGE), expected);
  assert.deepEqual(m.request({ ok: true, document: doc() }, STAGE), expected);
  assert.deepEqual(m.request({ ok: true, document: doc("new") }, "short"), expected);
  assert.equal(m.phase, "READY");
});

test("last-confirmed snapshot is detached from returned objects", () => {
  const m = baseline();
  const snap = m.snapshot();
  snap.confirmed.tasks[0].title = "TAMPERED";
  snap.items[0].title = "TAMPERED";
  assert.equal(m.snapshot().confirmed.tasks[0].title, "M12A_LAST_CONFIRMED");
});

test("UI state uses only six existing state names and recovery never drops rows", () => {
  const known = new Set(["loading","saving","ready","empty","error","unsupported"]);
  for (const m of [new SyntheticGuardedModel(doc()), baseline()]) {
    assert.ok(known.has(m.snapshot().state));
  }
  const m = baseline();
  const candidate = queued(m);
  assert.equal(reservation(m, candidate), true);
  m.hostExit();
  assert.equal(m.snapshot().state, "error");
  assert.equal(m.snapshot().items.length, 1);
  assert.equal(m.snapshot().writable, false);
});

test("single live FileView and nine mutations are unchanged by synthetic model", () => {
  const root = path.resolve(__dirname, "../..");
  const fixture = fs.readFileSync(
    path.join(__dirname, "fixtures/TaskGuardedCompletionModelM12a.cjs"), "utf8");
  const store = fs.readFileSync(
    path.join(root, "services/hub/ApolloHubTodoStore.qml"), "utf8");
  const shell = fs.readFileSync(path.join(root, "shell.qml"), "utf8");
  assert.ok(store.includes("readonly property bool guardedWriterEnabled: false"));
  assert.equal((store.match(/\bFileView\s*\{/g) || []).length, 1);
  assert.equal((store.match(/return stage\(TodoPolicy\./g) || []).length, 9);
  assert.equal(store.includes("TaskGuardedCompletionModelM12a"), false);
  assert.equal(shell.includes("TaskGuardedCompletionModelM12a"), false);
  for (const forbidden of [
    "apollo-hub-todo-v1.json","Quickshell.dataDir",
    "child_process","fs.readFile","FileView {"
  ]) assert.equal(fixture.includes(forbidden), false, forbidden);
  assert.equal(SyntheticGuardedModel.productionWriterAuthorized, false);
});
