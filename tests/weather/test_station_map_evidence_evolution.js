#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/WeatherEventEvolutionPolicy.js");
const ctx = {Date, Math, Number, String, Array, Object, JSON, isFinite};
vm.runInNewContext(source.replace(/^\.pragma library\s*/m, ""), ctx);

for (const fn of [
    "relationKey", "lifecycleLabel", "archivedOffsetHours",
    "analyze", "offsetLabel", "presenceLabel"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.equal(ctx.lifecycleLabel(0, 2, 3, 3), "PERSISTENT");
assert.equal(ctx.lifecycleLabel(1, 2, 2, 3), "CURRENT / LATE");
assert.equal(ctx.lifecycleLabel(1, 1, 1, 3), "SINGLE SNAPSHOT");
assert.equal(ctx.lifecycleLabel(0, 1, 2, 3), "DROPPED");
assert.equal(ctx.lifecycleLabel(0, 2, 2, 3), "INTERMITTENT");

const t1 = Date.parse("2026-11-01T00:00:00Z");
const t2 = Date.parse("2026-11-01T01:00:00Z");
const t3 = Date.parse("2026-11-01T03:00:00Z");

function rel(source, id, title, kind, mentionOnly) {
    return {
        source, id, title,
        latitude:38.5, longitude:-77.2,
        relationKind:kind,
        mentionOnly:mentionOnly === true
    };
}

const eonet = rel("NASA EONET","E1","Fire","TIME + SPACE",false);
const firms = rel("NASA FIRMS","F1","Hotspot","TIME + SPACE",false);
const gdelt = rel("GDELT GKG","P1","Nearby Place","MENTION NEARBY",true);
const usgs = rel("USGS","Q1","Nearby quake","SPACE ONLY",false);

const timeline = {
    anchorKey:"GDACS|WF:1:1",
    snapshots:[
        {
            savedAtMs:t1,
            relations:[eonet, usgs],
            addedCount:2,
            removedCount:0
        },
        {
            savedAtMs:t2,
            relations:[eonet, firms, gdelt],
            addedCount:2,
            removedCount:1
        },
        {
            savedAtMs:t3,
            relations:[eonet, firms, usgs],
            addedCount:1,
            removedCount:1
        }
    ],
    summary:{snapshotCount:3,firstSavedMs:t1,lastSavedMs:t3}
};

const analysis = ctx.analyze(timeline);
assert.equal(analysis.summary.snapshotCount, 3);
assert.equal(analysis.summary.providerCount, 4);
assert.equal(analysis.summary.recordCount, 4);
assert.equal(analysis.summary.currentProviders, 3);
assert.equal(analysis.summary.currentRecords, 3);
assert.equal(analysis.summary.persistentRecords, 1);
assert.equal(analysis.summary.intermittentRecords, 1);
assert.equal(analysis.summary.droppedRecords, 1);
assert.equal(analysis.summary.additions, 3);
assert.equal(analysis.summary.removals, 2);
assert.equal(analysis.summary.totalChurn, 5);
assert.equal(analysis.summary.maxTransitionChurn, 3);

const providers = Object.fromEntries(
    Array.from(analysis.providers).map(row => [row.source, row])
);
assert.equal(providers["NASA EONET"].lifecycle, "PERSISTENT");
assert.equal(providers["NASA EONET"].seenSnapshots, 3);
assert.equal(providers["NASA EONET"].firstOffsetHours, 0);
assert.equal(providers["NASA EONET"].lastOffsetHours, 3);

assert.equal(providers["NASA FIRMS"].lifecycle, "CURRENT / LATE");
assert.equal(providers["NASA FIRMS"].firstOffsetHours, 1);
assert.equal(providers["NASA FIRMS"].current, true);

assert.equal(providers["GDELT GKG"].lifecycle, "SINGLE SNAPSHOT");
assert.equal(providers["GDELT GKG"].current, false);

assert.equal(providers["USGS"].lifecycle, "INTERMITTENT");
assert.equal(providers["USGS"].seenSnapshots, 2);
assert.equal(providers["USGS"].current, true);

const records = Object.fromEntries(
    Array.from(analysis.records).map(row => [row.key, row])
);
assert.equal(records["NASA EONET|E1"].lifecycle, "PERSISTENT");
assert.equal(records["NASA FIRMS|F1"].lifecycle, "CURRENT / LATE");
assert.equal(records["GDELT GKG|P1"].lifecycle, "SINGLE SNAPSHOT");
assert.equal(records["GDELT GKG|P1"].mentionOnly, true);
assert.equal(records["USGS|Q1"].lifecycle, "INTERMITTENT");
assert.deepEqual(
    Array.from(records["USGS|Q1"].relationKinds),
    ["SPACE ONLY"]
);

assert.equal(ctx.offsetLabel(0), "+0M");
assert.equal(ctx.offsetLabel(0.5), "+30M");
assert.equal(ctx.offsetLabel(3), "+3.0H");
assert.match(ctx.presenceLabel(providers["NASA FIRMS"], 3), /2\/3 SNAPSHOTS/);
assert.match(ctx.presenceLabel(providers["NASA FIRMS"], 3), /FIRST \+1\.0H/);

const empty = ctx.analyze({snapshots:[]});
assert.equal(empty.summary.snapshotCount, 0);
assert.equal(empty.providers.length, 0);
assert.equal(empty.records.length, 0);

const policyText = read("services/weather/WeatherEventEvolutionPolicy.js");
assert.match(policyText, /first\/last archived presence/);
assert.match(policyText, /do NOT claim provider discovery time/i);
assert.doesNotMatch(
    policyText,
    /\bProcess\s*\{|\bTimer\s*\{|FileView|curl|XMLHttpRequest/
);

console.log("Weather MAP archived evidence evolution analysis: PASS");
