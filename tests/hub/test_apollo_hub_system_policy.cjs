#!/usr/bin/env node
"use strict";

// Execute the production pure-JS policy (minus the QML-only pragma) in Node.
// These cases exercise values and state transitions, not just string matching.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const script = fs.readFileSync(
    path.join(__dirname, "../../services/hub/ApolloHubSystemPolicy.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const ctx = vm.createContext({});
vm.runInContext(script, ctx, {filename: "ApolloHubSystemPolicy.js"});
const now = 1000000;

function row(id, usage, metric) {
    return {id, _systemRecord: true, usage, metric};
}
const rows = [
    row("system:cpu", 42.26, "42.3% BUSY"),
    row("system:memory", 68.04, "68.0% USED"),
    row("system:swap", 0, "0.0% USED"),
    row("system:rootfs", 81.77, "81.8% USED")
];
function snap(connected=true, loading=false, error="", sample=rows,
              observedAt=now - 10000, current=now) {
    return ctx.snapshot(connected, loading, error, sample, observedAt, current);
}
assert.equal(snap(false).state, "disconnected");
assert.equal(snap(false).cpuPercent, -1);
assert.equal(snap(true, false, "", rows, 0).state, "unobserved");
assert.equal(snap(true, false, "", rows, 0).fresh, false);
assert.equal(snap(true, true).state, "loading");
assert.equal(snap(true, false, "MONITOR FAILURE").state, "error");
assert.equal(snap(true, false, "MONITOR FAILURE").cpuMetric, "");
assert.equal(snap(true, false, "", rows, now - 300001).state, "stale");
assert.equal(snap(true, false, "", rows, now - 300000).state, "ready");
assert.equal(snap(true, false, "", rows, now + 1000).state, "stale");
assert.equal(snap(true, false, "", [], now).state, "unavailable");
assert.equal(snap(true, false, "", [rows[0]], now).state, "unavailable");

const good = snap();
assert.equal(good.state, "ready");
assert.equal(good.fresh, true);
assert.equal(good.ageMinutes, 0);
assert.equal(good.cpuPercent, 42.3);
assert.equal(good.memoryPercent, 68);
assert.equal(good.swapPercent, 0);
assert.equal(good.rootFilesystemPercent, 81.8);
assert.equal(good.cpuMetric, "42.3% BUSY");
assert.equal(good.observedAtMs, now - 10000);
assert.equal(snap(true, false, "", rows, now - 120000).ageMinutes, 2);

// Fake or malformed rows may not be mistaken for valid monitor output.
assert.equal(ctx.rowById([row("system:cpu", 22), {_systemRecord: false, id:"system:cpu", usage:7}], "system:cpu").usage, 22);
assert.equal(ctx.rowById([{id:"system:cpu", usage:7}], "system:cpu"), null);
assert.equal(ctx.usagePercent(row("system:cpu", -1)), -1);
assert.equal(ctx.usagePercent(row("system:cpu", 101)), -1);
assert.equal(ctx.usagePercent(row("system:cpu", "NaN")), -1);
assert.equal(ctx.usagePercent(row("system:cpu", null)), -1);
assert.equal(ctx.usagePercent(row("system:cpu", "0")), 0);
assert.equal(ctx.metric({metric: {unsafe: true}}), "");

const missingOptional = snap(true, false, "", rows.slice(0, 2));
assert.equal(missingOptional.state, "ready");
assert.equal(missingOptional.swapPercent, -1);
assert.equal(missingOptional.rootFilesystemPercent, -1);
assert.equal(snap(true, false, "", rows, now - 300001).cpuPercent, -1);

// Actuator metadata cannot escape in the scalar-only snapshot.
const armed = [{...rows[0], controlKind:"system-reboot", canReboot:true}, ...rows.slice(1)];
const serialized = JSON.stringify(snap(true, false, "", armed));
assert.equal(serialized.includes("system-reboot"), false);
assert.equal(serialized.includes("canReboot"), false);
console.log("ApolloHub CPU++ policy behavior tests passed");
