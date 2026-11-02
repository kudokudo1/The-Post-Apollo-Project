#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {
    Date, Math, Number, String, Array, Object, JSON, RegExp,
    isFinite, isNaN
};
vm.runInNewContext(
    read("widgets/weather/StationEventContextPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx,
    {filename:"widgets/weather/StationEventContextPolicy.js"}
);

for (const fn of [
    "compactOffsetMinutes",
    "timeRelationship",
    "spatialRelationship",
    "relationshipRow",
    "evidenceRelationships"
]) {
    assert.equal(typeof ctx[fn], "function", fn);
}

const base = Date.UTC(2026, 10, 2, 16, 30, 0);

assert.equal(ctx.parseMillis(-1), -1);
assert.equal(ctx.parseMillis(0), -1);
assert.equal(ctx.parseMillis("-1"), -1);
assert.equal(
    ctx.parseMillis("2026-11-02T16:30:00Z"),
    base
);

assert.equal(ctx.compactOffsetMinutes(0.25), "<1M");
assert.equal(ctx.compactOffsetMinutes(10), "10M");
assert.equal(ctx.compactOffsetMinutes(90), "1.5H");

let time = ctx.timeRelationship(base, base - 30 * 60000);
assert.equal(time.available, true);
assert.equal(time.deltaMinutes, 30);
assert.equal(time.direction, "BEFORE SELECTED SOURCE TIME");
assert.equal(time.band, "WITHIN 1H");
assert.match(time.label, /30M BEFORE SELECTED SOURCE TIME/);

time = ctx.timeRelationship(base, base + 5 * 60000);
assert.equal(time.available, true);
assert.equal(time.direction, "AFTER SELECTED SOURCE TIME");
assert.equal(time.band, "WITHIN 15M");

time = ctx.timeRelationship(base, base);
assert.equal(time.direction, "SAME SELECTED SOURCE TIME");
assert.equal(time.band, "WITHIN 15M");

time = ctx.timeRelationship(-1, base);
assert.equal(time.available, false);
assert.equal(time.label, "TIME OFFSET UNAVAILABLE");

assert.equal(ctx.spatialRelationship(10).band, "LOCAL");
assert.equal(ctx.spatialRelationship(80).band, "NEAR");
assert.equal(ctx.spatialRelationship(200).band, "REGIONAL");
assert.equal(ctx.spatialRelationship(500).band, "DISTANT");
assert.equal(ctx.spatialRelationship(-1).available, false);

const selected = ctx.normalizeSelected("gdacs", {
    id:"FL:300:1",
    name:"Relationship Test Flood",
    eventTypeLabel:"FLOOD",
    latitude:38.90,
    longitude:-77.00,
    timeMs:base,
    toUtc:"2026-11-02 16:30 UTC"
});

const companions = [
    {
        sourceLabel:"NASA EONET",
        typeLabel:"Floods",
        title:"Nearby EONET record",
        distanceKm:12,
        timeMs:base - 30 * 60000
    },
    {
        sourceLabel:"USGS",
        typeLabel:"EARTHQUAKE",
        title:"Independent earthquake record",
        distanceKm:120,
        timeMs:base + 120 * 60000
    }
];

const radar = {
    available:true,
    covered:true,
    timeMs:base + 5 * 60000
};
const lightning = {
    available:true,
    covered:true,
    timeMs:base - 10 * 60000
};
const flood = {
    relevant:true,
    available:true,
    eventGaugeDistanceKm:40,
    latestObserved:{
        timeMs:base - 20 * 60000
    }
};

const rows = Array.from(ctx.evidenceRelationships(
    selected,
    companions,
    radar,
    lightning,
    flood,
    8
));

assert.equal(rows.length, 5);
assert.deepEqual(
    rows.map(row => row.sourceLabel),
    ["NASA EONET", "USGS", "NOAA MRMS", "NOAA NOWCOAST", "NOAA NWPS"]
);
assert.deepEqual(
    rows.map(row => row.evidenceClass),
    [
        "EVENT RECORD",
        "EVENT RECORD",
        "REMOTE SENSING",
        "REMOTE SENSING",
        "GAUGE OBSERVATION"
    ]
);
assert.deepEqual(
    rows.map(row => row.relationClass),
    [
        "CROSS-SOURCE PROXIMITY",
        "CROSS-SOURCE PROXIMITY",
        "FRAME COVERAGE",
        "FRAME COVERAGE",
        "FLOOD-GATED PROXIMITY"
    ]
);

assert.equal(rows[0].spatialLabel, "12 KM // LOCAL");
assert.match(rows[0].temporalLabel, /30M BEFORE SELECTED SOURCE TIME/);
assert.match(rows[0].reason, /250 KM PROXIMITY RULE/);
assert.match(rows[0].limitation, /DO NOT ESTABLISH SAME INCIDENT/);

assert.equal(
    rows[2].spatialLabel,
    "EVENT POINT INSIDE LOADED MRMS FRAME"
);
assert.match(rows[2].temporalLabel, /5M AFTER SELECTED SOURCE TIME/);
assert.match(rows[2].limitation, /DO NOT INTERPRET RADAR PIXELS/);

assert.equal(
    rows[3].spatialLabel,
    "EVENT POINT INSIDE LOADED LIGHTNING FRAME"
);
assert.match(rows[3].limitation, /DO NOT PROVE LIGHTNING AT EVENT/);

assert.equal(rows[4].distanceKm, 40);
assert.match(rows[4].spatialLabel, /40 KM \/\/ NEAR/);
assert.match(rows[4].reason, /WITHIN 100 KM EVENT GATE/);
assert.match(rows[4].limitation, /EVENT CATCHMENT OR INCIDENT IDENTITY/);

assert.ok(rows.every(row =>
    row.sourceLabel.length > 0
    && row.evidenceClass.length > 0
    && row.relationClass.length > 0
    && row.spatialLabel.length > 0
    && row.temporalLabel.length > 0
    && row.reason.length > 0
    && row.limitation.length > 0
));

const excluded = Array.from(ctx.evidenceRelationships(
    selected,
    [],
    {available:true, covered:false, timeMs:base},
    {available:true, covered:false, timeMs:base},
    {
        relevant:true,
        available:false,
        eventGaugeDistanceKm:20,
        latestObserved:{timeMs:base}
    },
    8
));
assert.equal(excluded.length, 0);

const nonFloodGauge = Array.from(ctx.evidenceRelationships(
    selected,
    [],
    null,
    null,
    {
        relevant:false,
        available:true,
        eventGaugeDistanceKm:20,
        latestObserved:{timeMs:base}
    },
    8
));
assert.equal(nonFloodGauge.length, 0);

assert.equal(
    ctx.evidenceRelationships(null, companions, radar, lightning, flood, 8).length,
    0
);

const capped = Array.from(ctx.evidenceRelationships(
    selected,
    companions,
    radar,
    lightning,
    flood,
    2
));
assert.equal(capped.length, 2);

const map = read("widgets/weather/StationDiscovery.qml");
const card = read("widgets/weather/StationEventContextCard.qml");
const policy = read("widgets/weather/StationEventContextPolicy.js");

assert.match(
    map,
    /readonly property var selectedEvidenceRelationships:/
);
assert.match(
    map,
    /EventContextPolicy\.evidenceRelationships\(/
);
assert.match(
    map,
    /relationshipRows:\s*stationDiscovery\.selectedEvidenceRelationships/
);

assert.match(card, /property var relationshipRows: \[\]/);
assert.match(card, /readonly property int relationshipCount:/);
for (const phrase of [
    "RELATIONSHIP BASIS // WHY THIS EVIDENCE IS SHOWN",
    "SPACE // ",
    " // TIME // ",
    "RELATIONSHIP BASIS EXPLAINS INCLUSION ONLY",
    "NO SCORE",
    "NO CAUSAL CLAIM",
    "NO INCIDENT MERGE"
]) {
    assert.ok(card.includes(phrase), phrase);
}
assert.match(card, /modelData\.evidenceClass/);
assert.match(card, /modelData\.sourceLabel/);
assert.match(card, /modelData\.relationClass/);
assert.match(card, /modelData\.spatialLabel/);
assert.match(card, /modelData\.temporalLabel/);
assert.match(card, /modelData\.reason/);
assert.match(card, /modelData\.limitation/);

assert.equal((card.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bFileView\s*\{/g) || []).length, 0);
assert.doesNotMatch(policy, /curl|https:\/\//);
assert.doesNotMatch(policy, /Timer\s*\{|Process\s*\{|FileView\s*\{/);

console.log("Weather M17 evidence relationship basis: PASS");
