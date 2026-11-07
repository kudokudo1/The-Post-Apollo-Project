#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const script = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalSurgeryStartupPolicy.js"), "utf8");
const policy = vm.createContext({});
vm.runInContext(script, policy);

const now = 2000000;
const past = now - 8000;
const floor = (last, count, win=120000) =>
    policy.canReuseFloor(last, now, win, count);
const audit = (last, available, error="", win=600000) =>
    policy.canReuseAudit(last, now, win, available, error);

// A successfully discovered Floor is reused during rapid menu toggles.
assert.equal(floor(past, 4), true);
assert.equal(floor(past, 0), false); // missing Floor must rediscover
assert.equal(floor(0, 4), false); // no first discovery yet
assert.equal(floor(now - 121000, 4), false); // stale
assert.equal(floor(now + 1000, 4), false); // clock moved backwards
assert.equal(floor(past, 4, 0), false);
assert.equal(floor(past, 4, -1), false);

// The old bug: a timestamp written at the START of an audit was
// considered fresh even after floorChanged resetResult() had cleared rooms.
assert.equal(audit(past, false, ""), false); // empty snapshot
assert.equal(audit(past, false, "PX AUDIT TIMEOUT"), false);
assert.equal(audit(past, true, "PX AUDIT PARSE FAILED"), false);
assert.equal(audit(past, true, ""), true);
assert.equal(audit(now - 601000, true), false);
assert.equal(audit(now + 1000, true), false);
assert.equal(audit(0, true), false);
assert.equal(audit(past, true, "", 0), false);
assert.equal(audit(past, true, "", -1), false);

console.log("HOSPITAL SURGERY STARTUP POLICY // PASS // real snapshot reuse, retry on missing or failed cache");
