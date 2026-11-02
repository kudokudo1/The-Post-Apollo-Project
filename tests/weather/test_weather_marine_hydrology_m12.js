#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const policySource = read("widgets/weather/WeatherRelationshipPolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const relation = {
    Date, Math, Number, String, Array, Object, JSON, RegExp, isFinite
};
vm.runInNewContext(policySource, relation, {
    filename: "widgets/weather/WeatherRelationshipPolicy.js"
});

const minute = 60000;
const base = Date.UTC(2026, 10, 2, 14, 0, 0);

function sample(minutes, payload) {
    return {
        observedAtMs: base + minutes * minute,
        receivedAtMs: base + minutes * minute + 1000,
        payload
    };
}

// Marine relationships are same-observation comparisons. Zero tolerance must
// keep only metrics that came from the exact same NDBC sample timestamp.
const marine = [
    sample(0,  {windSpeedMs:3, pressureHpa:1018, waveHeightM:0.5}),
    sample(30, {windSpeedMs:5, pressureHpa:1016, waveHeightM:0.8}),
    sample(60, {windSpeedMs:7, pressureHpa:1014, waveHeightM:1.1}),
    sample(90, {windSpeedMs:9, pressureHpa:1012, waveHeightM:1.5})
];

const windWave = relation.relationship(
    marine, "windSpeedMs",
    marine, "waveHeightM",
    0,
    48
);
assert.equal(windWave.count, 4);
assert.ok(windWave.correlation > 0.99);

const pressureWave = relation.relationship(
    marine, "pressureHpa",
    marine, "waveHeightM",
    0,
    48
);
assert.equal(pressureWave.count, 4);
assert.ok(pressureWave.correlation < -0.99);

// A shifted record must not match a zero-tolerance same-observation relation.
const shiftedWaves = marine.map((row, index) => ({
    observedAtMs: row.observedAtMs + (index === 0 ? minute : 0),
    receivedAtMs: row.receivedAtMs,
    payload: {waveHeightM: row.payload.waveHeightM}
}));
const exactOnly = relation.relationship(
    marine, "windSpeedMs",
    shiftedWaves, "waveHeightM",
    0,
    48
);
assert.equal(exactOnly.count, 3);

// River/precipitation is context-only. The underlying alignment can pair
// nearby observations, but the page must not turn this into a correlation
// claim because basin rainfall and response lag are not modeled.
const precip = [
    sample(0,   {precipMm:0.0}),
    sample(30,  {precipMm:1.2}),
    sample(60,  {precipMm:3.5}),
    sample(90,  {precipMm:0.7})
];
const stage = [
    sample(20,  {stage:4.1}),
    sample(50,  {stage:4.2}),
    sample(80,  {stage:4.5}),
    sample(110, {stage:4.8})
];
const riverContext = relation.relationship(
    precip, "precipMm",
    stage, "stage",
    90 * minute,
    48
);
assert.equal(riverContext.count, 4);
assert.ok(Math.abs(riverContext.rightTrend.delta - 0.7) < 1e-9);

const ground = read("widgets/weather/StationGround.qml");

assert.match(ground, /readonly property var marineHistory:/);
assert.match(
    ground,
    /RelationshipPolicy\.relationship\(\s*marineHistory, "windSpeedMs",\s*marineHistory, "waveHeightM",\s*0,\s*48/
);
assert.match(
    ground,
    /RelationshipPolicy\.relationship\(\s*marineHistory, "pressureHpa",\s*marineHistory, "waveHeightM",\s*0,\s*48/
);

assert.match(ground, /NDBC WIND ↔ WAVE HEIGHT/);
assert.match(ground, /NDBC PRESSURE ↔ WAVE HEIGHT/);
assert.match(ground, /SAME NDBC OBS/);
assert.match(ground, /LINEAR ASSOCIATION ONLY, NOT CAUSATION/);

assert.match(ground, /readonly property var riverObservedSamples:/);
assert.match(ground, /riverService\.stageflow\.observed\.data\.map/);
assert.match(ground, /"observedAtMs": Number\(row\.validMillis\)/);
assert.match(ground, /"stage": row\.primary/);
assert.match(
    ground,
    /RelationshipPolicy\.relationship\(\s*pressureHistory, "precipMm",\s*riverObservedSamples, "stage",\s*90 \* 60000,\s*48/
);

assert.match(ground, /LOCAL PRECIP ↔ NWPS OBSERVED STAGE/);
assert.match(ground, /WEATHER-FIX PRECIP ≠ BASIN RAINFALL/);
assert.match(ground, /HYDROLOGIC LAG NOT MODELED/);
assert.match(ground, /CONTEXT ONLY/);
assert.match(ground, /KM GAUGE DISTANCE/);

// The river summary intentionally exposes synchronized count + stage delta,
// never Pearson r or an association-strength label.
const riverSummaryStart = ground.indexOf("function riverPrecipSummary()");
const riverFooterStart = ground.indexOf("function riverPrecipFooter()");
assert.ok(riverSummaryStart >= 0 && riverFooterStart > riverSummaryStart);
const riverSummary = ground.slice(riverSummaryStart, riverFooterStart);
assert.doesNotMatch(riverSummary, /correlation|formatCorrelation|correlationLabel/);
assert.match(riverSummary, /SYNC/);
assert.match(riverSummary, /Δ STAGE/);

// Preserve safety/context ordering.
const official = ground.indexOf('title: "OFFICIAL ALERTS // NWS"');
const coastal = ground.indexOf('title: "LIVE HISTORY // COASTAL RELATIONSHIP"');
const marineSection = ground.indexOf('title: "LIVE HISTORY // MARINE RELATIONSHIPS"');
const riverSection = ground.indexOf('title: "RIVER // NOAA NWPS"');
const riverInspector = ground.indexOf('title: "LOCAL PRECIP ↔ NWPS OBSERVED STAGE"');
const nearby = ground.indexOf('title: "NEARBY COMPARE // SAME NWPS SNAPSHOT"');

assert.ok(official >= 0);
assert.ok(official < coastal);
assert.ok(coastal < marineSection);
assert.ok(marineSection < riverSection);
assert.ok(riverSection < riverInspector);
assert.ok(riverInspector < nearby);

// M12 remains a read-only cross-domain consumer.
assert.doesNotMatch(ground, /liveHistoryStore\.append/);
assert.doesNotMatch(ground, /\bcurl\b|https:\/\//);

const inspector = read("widgets/weather/WeatherTrendInspector.qml");
assert.equal((inspector.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((inspector.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((inspector.match(/\bFileView\s*\{/g) || []).length, 0);

console.log("Weather M12 marine and hydrology context: PASS");
