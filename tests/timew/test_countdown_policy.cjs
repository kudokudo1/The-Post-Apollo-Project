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

// Independent named timers share the same monotonic timeline; no timer can
// alter another timer's starting tick, pause state or remaining budget.
assert.equal(p.MAX_TIMERS, 8);
assert.equal(p.MAX_NAME_LENGTH, 32);
assert.equal(p.createTimer(0), null);
let timers = [p.createTimer(1), p.createTimer(2), p.createTimer(3)];
assert.equal(p.byId(timers, 2).name, "TIMER 2");
assert.equal(p.byId(timers, 999), null);
assert.equal(p.runningCount(timers), 0);
timers = p.update(timers, 1, {minutes: "1", seconds: "0", name: "Tea"});
timers = p.update(timers, 2, {minutes: "2", seconds: "0", name: "Laundry"});
timers = p.update(timers, 3, {hours: "0", minutes: "0", seconds: "1"});
assert.equal(p.displayMs(p.byId(timers, 1)), 60000);
assert.equal(p.displayMs(p.byId(timers, 2)), 120000);
assert.equal(p.displayMs(p.byId(timers, 3)), 1000);
const originals = timers;
timers = p.act(timers, 1, "start", 1000);
timers = p.act(timers, 2, "start", 1500);
timers = p.act(timers, 3, "start", 2000);
assert.equal(p.runningCount(timers), 3);
assert.equal(p.byId(originals, 1).status, "ready");
timers = p.tick(timers, 2900);
assert.equal(p.byId(timers, 1).remainingMs, 58100);
assert.equal(p.byId(timers, 2).remainingMs, 118600);
assert.equal(p.byId(timers, 3).remainingMs, 100);
timers = p.act(timers, 1, "pause", 3000);
assert.equal(p.byId(timers, 1).remainingMs, 58000);
assert.equal(p.byId(timers, 1).status, "paused");
timers = p.tick(timers, 4500);
assert.equal(p.byId(timers, 1).remainingMs, 58000); // pause truly freezes
assert.equal(p.byId(timers, 3).status, "finished");
assert.equal(p.byId(timers, 3).remainingMs, 0);
assert.equal(p.byId(timers, 2).remainingMs, 117000);
assert.equal(p.runningCount(timers), 1);
timers = p.act(timers, 1, "start", 6000); // resume existing 58 seconds
timers = p.tick(timers, 7000);
assert.equal(p.byId(timers, 1).remainingMs, 57000);
assert.equal(p.byId(timers, 2).remainingMs, 114500);
timers = p.act(timers, 2, "reset", 7500); // independent reset
assert.equal(p.byId(timers, 2).status, "ready");
assert.equal(p.byId(timers, 2).name, "Laundry");
assert.equal(p.byId(timers, 1).status, "running");
timers = p.tick(timers, 70000); // UI outage; both timers catch up
assert.equal(p.byId(timers, 1).status, "finished");
assert.equal(p.runningCount(timers), 0);
timers = p.act(timers, 1, "start", 71000); // finished timer restarts
assert.equal(p.byId(timers, 1).remainingMs, 60000);
assert.equal(p.byId(timers, 2).status, "ready");

// Invalid inputs cannot launch and do not contaminate other timer records.
timers = p.update(timers, 2, {minutes: "75"});
timers = p.act(timers, 2, "start", 72000);
assert.equal(p.byId(timers, 2).status, "ready");
assert.equal(p.byId(timers, 2).error, "INVALID_DURATION");
assert.equal(p.byId(timers, 1).status, "running");
assert.equal(p.runningCount(timers), 1);
assert.equal(p.act(timers, 999, "pause", 1), timers);
assert.equal(p.tick(timers, -1), timers);
assert.equal(p.act(timers, 1, "invalid", 74000), timers);
assert.equal(p.byId(p.update(timers, 1, {name: "Updated"}), 2).name,
             "Laundry");

// The UI caps creation at eight and refuses deleting the last record;
// the pure policy must support stable, unique identities across updates.
const eight = Array.from({length: p.MAX_TIMERS}, (_, i) => p.createTimer(i + 1));
assert.equal(new Set(eight.map(item => item.id)).size, p.MAX_TIMERS);
assert.equal(p.byId(eight, 8).name, "TIMER 8");

console.log("TIMEW COUNTDOWN POLICY: PASS");
