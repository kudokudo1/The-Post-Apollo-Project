#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const filename = path.join(__dirname, "../../services/time/CountdownPolicy.js");
const code = fs.readFileSync(filename, "utf8").replace(/^\.pragma library\s*/m, "");
const p = vm.createContext({});
vm.runInContext(code, p, {filename: "CountdownPolicy.js"});

for (const [h, m, s, value] of [
    ["0", "5", "0", 300000], ["00", "00", "01", 1000],
    ["1", "30", "15", 5415000], ["99", "59", "59", 359999000],
    ["00", "59", "59", 3599000],
]) {
    const x = p.parseDuration(h,m,s);
    assert.equal(x.valid, true);
    assert.equal(x.milliseconds, value);
}
for (const values of [
    ["0","0","0"],["00","00","00"],
    ["100","00","00"],["-1","0","0"],
    ["0","60","0"],["0","0","60"],
    ["a","2","4"],["0","","3"],["0","1.5","0"],
    [0,"1","0"],[null,"1","0"],
    ["0"," 1","0"],["0","1 ","0"],
]) {
    assert.equal(p.parseDuration(...values).valid, false, values.join(","));
}
assert.equal(p.parseDuration("0","0","0").error, "ZERO_DURATION");
assert.equal(p.parseDuration("0","75","0").error, "INVALID_DURATION");
assert.equal(p.remaining(5000, 0), 5000);
assert.equal(p.remaining(5000, 1234), 3766);
assert.equal(p.remaining(5000, 5000), 0);
assert.equal(p.remaining(5000, 8000), 0);
assert.equal(p.remaining(20000, 250000), 0); // UI stalls do not add time
assert.equal(p.remaining(3000, -1), 0);
assert.equal(p.remaining(NaN, 100), 0);
// Pause freezes the remainder. Resuming starts a fresh monotonic segment.
const firstSegment = p.remaining(5000, 1700);
assert.equal(firstSegment, 3300);
const paused = firstSegment;
const resume = p.remaining(paused, 1800);
assert.equal(resume, 1500);
assert.equal(p.remaining(resume, 1500), 0);

assert.equal(p.format(0), "00:00:00");
assert.equal(p.format(1), "00:00:01");
assert.equal(p.format(999), "00:00:01");
assert.equal(p.format(1000), "00:00:01");
assert.equal(p.format(1001), "00:00:02");
assert.equal(p.format(59999), "00:01:00");
assert.equal(p.format(3600000), "01:00:00");
assert.equal(p.format(359999000), "99:59:59");
assert.equal(p.format(-5), "--:--:--");
assert.equal(p.format(Infinity), "--:--:--");
console.log("TIMEW COUNTDOWN POLICY: PASS");
