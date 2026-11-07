#!/usr/bin/env node
"use strict";
// PX records only; no browser tabs or live provider interaction.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const policyText = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalWorkerAttentionPolicy.js"), "utf8");
const p = vm.createContext({});
vm.runInContext(policyText, p);

function room(status, extra = {}) {
    return Object.assign({
        roomId: "company-map", sessionId: "px-session-44",
        sessionStatus: status, statusRecordedAt: "2026-11-07 11:25:00",
        sessionLastError: "", sessionLastExitCode: null,
        sessionEndedAt: ""
    }, extra);
}
function check(status, label, severity, extras) {
    const result = p.describe(room(status, extras));
    assert.equal(result.label, label, status);
    assert.equal(result.severity, severity, status);
    assert.equal(result.source, "PX SESSION RECORD");
    assert.equal(result.recordedAt, "2026-11-07 11:25:00");
    return result;
}

check("IDLE", "IDLE", 0);
check("THINKING", "WORKING", 0);
check("OPERATING", "WORKING", 0);
check("PAUSED", "PAUSED", 1);
check("WAITING", "WAITING", 2);
const review = check("REVIEW", "NEEDS REVIEW", 2);
assert.equal(review.requiresReview, true);
check("FAILED", "STOPPED", 3);
check("COMPLETE", "COMPLETE", 0);
check("ENDED", "COMPLETE", 0);
check("BROKEN", "UNKNOWN", 0);
assert.equal(p.describe(room("WAITING", {sessionId:""})).label, "UNCONNECTED");
assert.equal(p.describe({}).label, "UNCONNECTED");
assert.equal(p.describe(room("FAILED", {
    sessionLastError: "provider exited due to sandbox refusal",
    sessionLastExitCode: 12
})).reason, "provider exited due to sandbox refusal");
const error = p.describe(room("IDLE", {sessionLastError:
    "provider\nerror\tfrom runtime  "}));
assert.equal(error.label, "NEEDS ATTENTION");
assert.equal(error.reason, "provider error from runtime");
assert.equal(error.severity, 2);
assert.equal(p.describe(room("IDLE", {sessionLastExitCode: 0})).severity, 0);
assert.equal(p.describe(room("IDLE", {sessionLastExitCode: 13})).label,
    "NEEDS ATTENTION");
assert.equal(p.describe(room("WAITING", {sessionEndedAt:"2026-11-07"})).label,
    "ENDED");
assert.equal(p.describe(room("COMPLETE", {sessionLastError:"old failure"})).label,
    "COMPLETE");
assert.equal(p.describe(room("OPERATING")).reason.includes("heartbeat not verified"), true);
assert.equal(p.describe(room("OPERATING")).label === "FROZEN", false);
assert.equal(p.describe(room("REVIEW")).reason.includes("approval granted"), false);
assert.equal(p.describe(room("WAITING")).reason.includes("cause is not classified"), true);
assert.equal(p.countAttention([
    room("IDLE"), room("REVIEW"), room("FAILED"), room("PAUSED"),
    room("WAITING"), room("COMPLETE"),
    room("IDLE", {sessionLastError:"error"})
]), 4);
assert.equal(p.countAttention(null), 0);
console.log("HOSPITAL RECORDED ATTENTION // PASS // evidence-based states, errors, missing sessions, no fabricated heartbeat");
