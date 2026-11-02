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
const base = Date.UTC(2026, 10, 2, 12, 0, 0);

function sample(minutes, payload) {
    return {
        observedAtMs: base + minutes * minute,
        receivedAtMs: base + minutes * minute + 1000,
        payload
    };
}

const left = [
    sample(0, {a:1}),
    sample(10, {a:2}),
    sample(20, {a:3}),
    sample(30, {a:4}),
    sample(40, {a:5})
];

const right = [
    sample(1, {b:5}),
    sample(11, {b:4}),
    sample(21, {b:3}),
    sample(31, {b:2}),
    sample(41, {b:1})
];

const pairs = relation.nearestPairs(
    left, "a", right, "b", 2 * minute, 48
);
assert.equal(pairs.length, 5);
assert.deepEqual(
    Array.from(pairs.map(row => row.left)),
    [1,2,3,4,5]
);
assert.deepEqual(
    Array.from(pairs.map(row => row.right)),
    [5,4,3,2,1]
);
assert.equal(relation.pearson(pairs), -1);
assert.equal(relation.correlationLabel(-1), "STRONG NEGATIVE");

// One right-side observation can be paired only once.
const reuseGuard = relation.nearestPairs(
    [
        sample(0, {a:1}),
        sample(1, {a:2}),
        sample(2, {a:3})
    ],
    "a",
    [sample(1, {b:9})],
    "b",
    5 * minute,
    48
);
assert.equal(reuseGuard.length, 1);

// Out-of-tolerance observations do not get silently interpolated.
const noMatch = relation.nearestPairs(
    [sample(0, {a:1})],
    "a",
    [sample(60, {b:1})],
    "b",
    10 * minute,
    48
);
assert.equal(noMatch.length, 0);

// Correlation requires at least four aligned pairs.
assert.equal(relation.pearson(pairs.slice(0,3)), null);
assert.equal(
    relation.correlationLabel(null),
    "NEED ≥4 PAIRS"
);

const positive = relation.summarizePairs([
    {timeMs:base, left:1, right:10, distanceMs:0},
    {timeMs:base+minute, left:2, right:20, distanceMs:0},
    {timeMs:base+2*minute, left:3, right:30, distanceMs:0},
    {timeMs:base+3*minute, left:4, right:40, distanceMs:0}
]);
assert.equal(positive.correlation, 1);
assert.equal(positive.leftTrend.delta, 3);
assert.equal(positive.rightTrend.delta, 30);
assert.deepEqual(Array.from(positive.leftValues), [1,2,3,4]);
assert.deepEqual(Array.from(positive.rightValues), [10,20,30,40]);

const normalized = relation.normalized([-10, 0, 10]);
assert.deepEqual(Array.from(normalized), [0, 0.5, 1]);
assert.deepEqual(
    Array.from(relation.normalized([5,5,5])),
    [0.5,0.5,0.5]
);
assert.equal(relation.formatCorrelation(0.345), "0.34");
assert.equal(relation.formatDelta(2.25, 1), "+2.3");
assert.equal(relation.formatDelta(-2.25, 1), "-2.3");
assert.equal(relation.spanLabel(95 * minute), "1h 35m");

const inspector = read("widgets/weather/WeatherTrendInspector.qml");
assert.match(inspector, /SystemServices\.GraphHistory\s*\{/);
assert.match(inspector, /graphHistory\.downsampleHistory/);
assert.match(inspector, /graphHistory\.linePoints/);
assert.match(inspector, /NORMALIZED SHAPE/);
assert.equal((inspector.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((inspector.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((inspector.match(/\bFileView\s*\{/g) || []).length, 0);

const home = read("widgets/weather/StationHome.qml");
assert.match(home, /WeatherRelationshipPolicy\.js/);
assert.match(home, /AQI ↔ HUMIDITY/);
assert.match(home, /AQI ↔ WIND/);
assert.match(
    home,
    /RelationshipPolicy\.relationship\([\s\S]*?"aqi"[\s\S]*?"humidity"[\s\S]*?20 \* 60000/
);
assert.match(
    home,
    /RelationshipPolicy\.relationship\([\s\S]*?"aqi"[\s\S]*?"windMph"[\s\S]*?20 \* 60000/
);
assert.match(home, /LINEAR ASSOCIATION ONLY, NOT CAUSATION/);
assert.ok(
    home.indexOf('title: "OFFICIAL ALERT \/\/ NWS"')
    < home.indexOf('title: "LIVE HISTORY \/\/ AQI RELATIONSHIPS"')
);

const ground = read("widgets/weather/StationGround.qml");
assert.match(ground, /WeatherRelationshipPolicy\.js/);
assert.match(ground, /PRESSURE ↔ COASTAL WATER LEVEL/);
assert.match(
    ground,
    /RelationshipPolicy\.relationship\([\s\S]*?"pressureHpa"[\s\S]*?"waterLevel"[\s\S]*?45 \* 60000/
);
assert.match(ground, /CO-OPS OBSERVED WATER LEVEL \/\/ ASSOCIATION ONLY/);
assert.ok(
    ground.indexOf('title: "OFFICIAL ALERTS \/\/ NWS"')
    < ground.indexOf('title: "LIVE HISTORY \/\/ COASTAL RELATIONSHIP"')
);
assert.ok(
    ground.indexOf('title: "LIVE HISTORY \/\/ COASTAL RELATIONSHIP"')
    < ground.indexOf('title: "RIVER \/\/ NOAA NWPS"')
);

const space = read("widgets/weather/StationSpace.qml");
assert.match(space, /WeatherRelationshipPolicy\.js/);
assert.match(space, /SOLAR WIND ↔ IMF BZ/);
assert.match(
    space,
    /RelationshipPolicy\.relationship\([\s\S]*?"solarWindSpeed"[\s\S]*?"bz"[\s\S]*?10 \* 60000/
);
assert.match(space, /CURRENT KP/);
assert.match(space, /OVATION LOCAL/);
assert.match(space, /CONTEXT ONLY, NO CAUSAL MODEL/);
assert.ok(
    space.indexOf('title: "SOLAR \/\/ GEOMAGNETIC"')
    < space.indexOf('title: "LIVE HISTORY \/\/ SOLAR CONTEXT"')
);
assert.ok(
    space.indexOf('title: "LIVE HISTORY \/\/ SOLAR CONTEXT"')
    < space.indexOf('title: "NOAA SCALES \/\/ CURRENT SNAPSHOT"')
);

// M11 must consume M10 history, never become another writer/fetcher.
for (const page of [home, ground, space]) {
    assert.doesNotMatch(page, /liveHistoryStore\.append/);
}
assert.doesNotMatch(inspector, /curl|https:\/\//);

// The source-of-truth storage contract remains the M10 history store.
const historyStore = read("services/weather/WeatherLiveHistoryStore.qml");
assert.equal((historyStore.match(/\bFileView\s*\{/g) || []).length, 1);
assert.equal((historyStore.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((historyStore.match(/\bTimer\s*\{/g) || []).length, 0);

console.log("Weather M11 history inspectors and relationships: PASS");
