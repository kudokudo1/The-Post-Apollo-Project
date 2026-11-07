#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalWorkerConnectionPolicy.js"), "utf8"), ctx);

const base = {
    roomId: "room-42", repository: "org/project", patientId: "patient-9", branch: "map-integration",
    roomDoctorId: "doctor-7", sessionDoctorId: "doctor-7",
    roomProviderId: "codex", sessionProviderId: "codex",
    bedPath: "/synthetic/worktree", sessionWorkingDirectory: "/synthetic/worktree",
    assignmentId: "91", assignmentTitle: "Build Map",
    assignmentStatus: "ACTIVE",
    sessionId: "session-3", sessionStatus: "IDLE", hasActiveSession: true,
    statusRecordedAt: "2026-11-07 13:05:00", sessionEndedAt: "",
    providerSessionId: "", sessionActivePid: 0
};
function check(overrides, expectedCode, dispatchAllowed=false) {
    const row = {...base, ...overrides};
    const plan = ctx.inspect(row);
    assert.equal(plan.code, expectedCode);
    assert.equal(plan.canRequestTurn, dispatchAllowed, expectedCode);
    assert.equal(plan.isProviderReachable, false);
    assert.equal(plan.isBrowserChatConnected, false);
    assert.equal(plan.source, "PX ROOM / SESSION RECORDS");
    assert.equal(plan.checks.length, 6);
    assert.equal(ctx.allowsCommand(row, "GO"), dispatchAllowed);
    assert.equal(ctx.allowsCommand(row, "CONTINUE"), dispatchAllowed);
    assert.equal(ctx.allowsCommand(row, "REPORT"), dispatchAllowed);
    assert.equal(ctx.allowsCommand(row, "STATUS"), true);
    assert.equal(ctx.allowsCommand(row, "SOMETHING UNSAFE"), false);
    return plan;
}
const good = check({}, "STRUCTURED", true);
assert.match(good.next, /PX must still check/);
assert.equal(good.checks.every(x=>x.ok), true);
assert.equal(ctx.inspect({...base, assignmentStatus: ""}).canRequestTurn, true);
check({roomId: ""}, "NO_ROOM");
check({repository: ""}, "NO_PATIENT");
check({branch: ""}, "NO_BRANCH");
check({sessionId: "", hasActiveSession: false}, "NO_SESSION");
check({sessionStatus: "FAILED", hasActiveSession: false}, "ENDED_SESSION");
check({sessionEndedAt: "2026-11-07", hasActiveSession: false}, "ENDED_SESSION");
check({roomDoctorId: ""}, "NO_DOCTOR");
check({sessionDoctorId: ""}, "NO_DOCTOR");
check({sessionDoctorId: "doctor-8"}, "DOCTOR_MISMATCH");
check({sessionProviderId: ""}, "NO_PROVIDER");
check({sessionProviderId: "hermes"}, "PROVIDER_MISMATCH");
check({roomProviderId: ""}, "STRUCTURED", true); // session Provider remains authoritative
check({sessionProviderId: "int1-fake", roomProviderId:"int1-fake"}, "FAKE_ONLY");
check({bedPath: ""}, "NO_BED");
check({sessionWorkingDirectory: ""}, "NO_BED");
check({sessionWorkingDirectory: "/another/tree"}, "BED_MISMATCH");
check({assignmentId: ""}, "NO_ASSIGNMENT");
check({assignmentStatus: "DRAFT"}, "ASSIGNMENT_INACTIVE");
check({assignmentStatus: "READY"}, "ASSIGNMENT_INACTIVE");
check({assignmentStatus: "CANCELLED"}, "ASSIGNMENT_INACTIVE");
check({sessionStatus: "WAITING"}, "SESSION_HOLD");
check({sessionStatus: "REVIEW"}, "SESSION_HOLD");
check({sessionStatus: "PAUSED"}, "SESSION_PAUSED");
check({sessionStatus: "OPERATING"}, "SESSION_BUSY");
check({sessionStatus: "THINKING"}, "SESSION_BUSY");
check({sessionActivePid: 99233}, "SESSION_BUSY");
check({sessionStatus: "MYSTERY"}, "UNKNOWN_STATE");
assert.equal(ctx.allowsCommand({...base, sessionDoctorId:"other"}, "PAUSE"), true);
assert.equal(ctx.allowsCommand({...base, sessionId: ""}, "PAUSE"), false);
assert.equal(ctx.countPending([base, {...base, sessionId:""},
    {...base, sessionProviderId:""}, {...base, sessionStatus:"PAUSED"}]), 3);
assert.equal(ctx.countPending(null), 0);
console.log("HOSPITAL WORKER CONNECTION POLICY // PASS // identity, provider, assignment, Bed and exact Session holds");
