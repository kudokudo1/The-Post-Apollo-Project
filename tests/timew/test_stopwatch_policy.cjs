#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const file = path.join(__dirname, "../../services/time/StopwatchPolicy.js");
const code = fs.readFileSync(file, "utf8").replace(/^\.pragma library\s*/m, "");
const p = vm.createContext({});
vm.runInContext(code, p, {filename: "StopwatchPolicy.js"});

assert.equal(p.MAX_LAPS, 100);
assert.equal(p.format(0), "00:00:00.00");
assert.equal(p.format(9), "00:00:00.00");
assert.equal(p.format(10), "00:00:00.01");
assert.equal(p.format(997), "00:00:00.99");
assert.equal(p.format(1000), "00:00:01.00");
assert.equal(p.format(61002), "00:01:01.00");
assert.equal(p.format(3600000), "01:00:00.00");
assert.equal(p.format(25 * 3600000 + 60 * 1000 + 2345),
             "25:01:02.34");
for (const bad of [-1, null, undefined, NaN, Infinity, "1200"]) {
    assert.equal(p.format(bad), "00:00:00.00");
}
assert.equal(p.sample(1200, 1702.8), 2902);
assert.equal(p.sample(1200, 0), 1200); // pause freezes accumulated value
assert.equal(p.sample(1200, 300000), 301200); // stalled UI catches up
assert.equal(p.sample(-3, 20), 0);
assert.equal(p.sample(5, NaN), 0);

// Monotonic samples preserve elapsed time across pause -> resume segments;
// lap is a marker, NOT a timer restart, so totals remain cumulative.
const first = p.appendLap([], 1100, 0, 1);
assert.equal(first[0].index, 1);
assert.equal(first[0].splitMs, 1100);
assert.equal(first[0].totalMs, 1100);
const second = p.appendLap(first, 3200, 1100, 2);
assert.equal(second[0].index, 2);
assert.equal(second[0].splitMs, 2100);
assert.equal(second[1].splitMs, 1100);
assert.equal(first.length, 1); // immutable append
assert.equal(p.appendLap(second, 300, 400, 3), null);
assert.equal(p.appendLap([], -1, 0, 1), null);
assert.equal(p.appendLap([], 100, 0, 0), null);

let laps = [];
let previous = 0;
for (let i = 1; i <= 115; i++) {
    laps = p.appendLap(laps, i * 1000, previous, i);
    previous = i * 1000;
}
assert.equal(laps.length, 100);
assert.equal(laps[0].index, 115);
assert.equal(laps[99].index, 16);
assert.equal(laps.every(x => x.splitMs === 1000), true);
console.log("TIMEW STOPWATCH POLICY: PASS");
