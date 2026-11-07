#!/usr/bin/env node
// Pure fixture verification; never touches the running Hospital store.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalWorkforceRosterPolicy.js"), "utf8");
const policy = vm.createContext({});
vm.runInContext(source, policy);

const rooms = [
    { id: "job-2", team: "finance", repository: "owner/finance",
      doctorId: "doc-2", providerId: "codex", assignmentId: "42" },
    { id: "job-1", team: "map", repository: "owner/company",
      doctorId: "doc-1", assignmentId: "41" },
    { id: "job-1", team: "DUPLICATE" },
    { id: "" }
];
const sessions = [
    { id: "s-old", roomId: "job-1", doctorId: "doc-1",
      status: "FAILED", updatedAt: "2026-11-06 09:00:00" },
    { id: "s-now", roomId: "job-1", doctorId: "doc-1",
      providerId: "hermes", status: "IDLE",
      updatedAt: "2026-11-07 08:00:00" },
    { id: "s-failed", roomId: "job-2", doctorId: "doc-2",
      status: "FAILED", endedAt: "2026-11-07 08:30:00" }
];
const doctors = [
    { id: "doc-1", name: "Map Specialist" }
];
const roster = policy.buildRoster(rooms, sessions, doctors);
assert.equal(roster.length, 2);
assert.equal(roster[0].roomId, "job-2"); // sorted by visible fallback name
assert.equal(roster[1].roomId, "job-1");
assert.equal(roster[1].name, "map");
assert.equal(roster[1].doctorName, "Map Specialist");
assert.equal(roster[1].sessionId, "s-now");
assert.equal(roster[1].sessionStatus, "IDLE");
assert.equal(roster[1].hasActiveSession, true);
assert.equal(roster[1].assignmentId, "41");
assert.equal(roster[0].doctorName, "doc-2");
assert.equal(roster[0].hasActiveSession, false);
assert.equal(roster[0].sessionStatus, "FAILED");
assert.equal(roster[0].nameIsFallback, true);

const renamed = policy.buildRoster(
    [{ id: "job-1", displayName: "Company Map", doctorId: "doc-1" }],
    [], doctors);
assert.equal(renamed[0].name, "Company Map");
assert.equal(renamed[0].nameIsFallback, false);
assert.equal(renamed[0].sessionStatus, "NO SESSION");
assert.equal(renamed[0].hasActiveSession, false);
assert.equal(policy.buildRoster([{ id: "branch-only" }], [], []).length, 1);
assert.equal(policy.buildRoster([], [{ roomId: "phantom" }], []).length, 0);
console.log("HOSPITAL WORKFORCE ROSTER // PASS // durable rooms only, session precedence, no phantom workers");
