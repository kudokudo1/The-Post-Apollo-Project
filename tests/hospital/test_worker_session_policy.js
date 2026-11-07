#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalWorkerSessionPolicy.js"), "utf8");
const policy = vm.createContext({});
vm.runInContext(source, policy);

const room = {
    roomId: "room-map", sessionId: "session-812",
    hasActiveSession: true, sessionStatus: "OPERATING"
};
const verified = { session: { id: "session-812", status: "OPERATING" } };

assert.equal(policy.roomMatches(room, "room-map"), true);
assert.equal(policy.roomMatches(room, "room-map-other"), false);
assert.equal(policy.sessionMatches(room, "room-map", "session-812"), true);
assert.equal(policy.sessionMatches(room, "room-map", "session-813"), false);
assert.equal(policy.sessionMatches(room, "another-room", "session-812"), false);
assert.equal(policy.sessionMatches({ ...room, hasActiveSession: false },
    "room-map", "session-812"), false);
assert.equal(policy.sessionMatches({ ...room, sessionId: "" },
    "room-map", "session-812"), false);
assert.equal(policy.statusMatches(verified, "session-812"), true);
assert.equal(policy.statusMatches(verified, "session-999"), false);
assert.equal(policy.statusMatches({}, "session-812"), false);

const good = {
    active: true, sessionMatches: true, runtimeStatusVerified: true,
    runtimeSessionMatches: true, hasError: false,
    busy: false, operating: false, command: "CONTINUE"
};
assert.equal(policy.canIssueQuick(good), true);
for (const field of ["active", "sessionMatches", "runtimeStatusVerified",
                     "runtimeSessionMatches"]) {
    assert.equal(policy.canIssueQuick({ ...good, [field]: false }), false, field);
}
assert.equal(policy.canIssueQuick({ ...good, hasError: true }), false);
assert.equal(policy.canIssueQuick({ ...good, busy: true }), false);
assert.equal(policy.canIssueQuick({ ...good, command: "MERGE" }), false);
assert.equal(policy.canIssueQuick({ ...good, command: "" }), false);
assert.equal(policy.canIssueQuick({ ...good, operating: true }), false);
assert.equal(policy.canIssueQuick({ ...good, operating: true, command: "STATUS" }), true);
assert.equal(policy.canIssueQuick({ ...good, operating: true, command: "PAUSE" }), true);
assert.equal(policy.canIssueQuick({ ...good, operating: true, command: "REPORT" }), false);

console.log("HOSPITAL EXACT SESSION QUICK // PASS // Room mismatch, session mismatch, stale status, prohibited commands");
