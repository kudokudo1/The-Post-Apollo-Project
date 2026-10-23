#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const filename = path.join(__dirname, "../../services/time/MachineTimelinePolicy.js");
const code = fs.readFileSync(filename, "utf8").replace(/^\.pragma library\s*/m, "");
const p = vm.createContext({});
vm.runInContext(code, p, {filename: "MachineTimelinePolicy.js"});

assert.equal(p.MAX_MARKERS, 24);
assert.equal(p.MAX_NAME_LENGTH, 48);
assert.equal(p.ageLabel(0), "00D 00:00:00");
assert.equal(p.ageLabel(999), "00D 00:00:00");
assert.equal(p.ageLabel(61000), "00D 00:01:01");
assert.equal(p.ageLabel(90061000), "01D 01:01:01");
assert.equal(p.ageLabel(25 * 86400000 + 3700000), "25D 01:01:40");
for (const bad of [-1, Infinity, NaN, null, "1000"]) {
    assert.equal(p.ageLabel(bad), "--D --:--:--");
}
assert.equal(p.utcStamp(Date.UTC(2026, 9, 23, 2, 40, 12)),
             "2026-10-23 02:40:12 UTC");
assert.equal(p.utcStamp(-1), "");
assert.equal(p.utcStamp(8640000000000001), "");

const t = Date.UTC(2026, 9, 23, 2, 40, 12);
const first = p.createMarker(1, "  Start session  ", t, 12345);
assert.equal(first.id, 1);
assert.equal(first.label, "Start session");
assert.equal(first.utc, "2026-10-23 02:40:12 UTC");
assert.equal(first.elapsedMs, 12345);
const unnamed = p.createMarker(2, "   ", t + 1000, 20000);
assert.equal(unnamed.label, "MARKER 02");
assert.equal(p.createMarker(0, "x", t, 0), null);
assert.equal(p.createMarker(1, "x".repeat(49), t, 0), null);
assert.equal(p.createMarker(1, "x", t, -1), null);
assert.equal(p.createMarker(1, "x", -1, 0), null);
assert.equal(p.createMarker(1, null, t, 0), null);
assert.equal(p.createMarker(1.25, "x", t, 0), null);

let list = [];
list = p.appendMarker(list, first);
assert.equal(list.length, 1);
assert.equal(p.appendMarker(list, first), null); // duplicate identity
const unchanged = list;
list = p.appendMarker(list, unnamed);
assert.equal(list[0].id, 2);
assert.equal(list[1].id, 1);
assert.equal(unchanged.length, 1); // immutable write
assert.equal(p.removeMarker(list, 99).length, 2);
const afterDelete = p.removeMarker(list, 1);
assert.equal(afterDelete.length, 1);
assert.equal(afterDelete[0].id, 2);
assert.equal(list.length, 2);

for (let i = 3; i <= p.MAX_MARKERS; i++) {
    const marker = p.createMarker(i, "checkpoint " + i, t + i * 1000, i * 10);
    list = p.appendMarker(list, marker);
}
assert.equal(list.length, p.MAX_MARKERS);
assert.equal(p.appendMarker(list, p.createMarker(25, "full", t, 1)), null);
assert.equal(new Set(list.map(x => x.id)).size, p.MAX_MARKERS);
assert.equal(list[0].id, 24);
console.log("TIMEW MACHINE SESSION POLICY: PASS");
