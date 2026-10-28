#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {Date, Number, String, Array, Object, Math, isFinite};
vm.runInNewContext(
    read("services/weather/AuroraPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "validTarget", "signedLongitude", "wrappedLongitudeDelta",
    "distanceKm", "parseOvation", "utcLabel"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.deepEqual(
    JSON.parse(JSON.stringify(ctx.validTarget(38.9, -77.0))),
    {latitude:38.9, longitude:-77.0}
);
assert.equal(ctx.validTarget("", -77), null);
assert.equal(ctx.validTarget(38.9, ""), null);
assert.equal(ctx.validTarget(91, -77), null);
assert.equal(ctx.validTarget(38.9, -181), null);

assert.equal(ctx.signedLongitude(283), -77);
assert.equal(ctx.signedLongitude(181), -179);
assert.equal(ctx.signedLongitude(180), 180);
assert.ok(Number.isNaN(ctx.signedLongitude("bad")));

assert.equal(ctx.wrappedLongitudeDelta(179, -179), -2);
assert.equal(ctx.wrappedLongitudeDelta(-179, 179), 2);
assert.equal(ctx.wrappedLongitudeDelta(10, 350), 20);

const acrossDateline = ctx.distanceKm(0, 179, 0, -179);
assert.ok(acrossDateline > 200 && acrossDateline < 230);
assert.equal(ctx.distanceKm("bad", 0, 0, 0), -1);

const fixture = {
    "Observation Time":"2026-10-28T08:00:00Z",
    "Forecast Time":"2026-10-28T08:45:00Z",
    coordinates:[
        [283.0, 39.0, 37],
        [282.0, 38.0, 22],
        [280.0, 45.0, 65],
        [100.0, 70.0, 91],
        [120.0, -45.0, 72],
        [200.0, -60.0, 88],
        [null, 50, 99],
        [250, "", 80],
        [250, 50, null]
    ]
};

let result = ctx.parseOvation(fixture, 38.9, -77.1);
assert.equal(result.northPeak, 91);
assert.equal(result.southPeak, 88);
assert.equal(result.northCells, 4);
assert.equal(result.southCells, 2);
assert.equal(result.localReady, true);
assert.equal(result.localIntensity, 37);
assert.equal(result.localLatitude, 39.0);
assert.equal(result.localLongitude, -77.0);
assert.ok(result.localDistanceKm >= 0 && result.localDistanceKm < 20);

// Invalid target must leave global hemisphere context intact while refusing
// to invent a local cell.
result = ctx.parseOvation(fixture, "", "");
assert.equal(result.northPeak, 91);
assert.equal(result.southPeak, 88);
assert.equal(result.localReady, false);
assert.equal(result.localIntensity, -1);
assert.equal(result.localDistanceKm, -1);

// Wrapped longitudes must make a cell just across the dateline nearer than a
// superficially smaller numeric longitude difference.
const datelineFixture = {
    "Observation Time":"2026-10-28T08:00:00Z",
    "Forecast Time":"2026-10-28T08:45:00Z",
    coordinates:[
        [181, 0.5, 44],
        [170, 0.5, 70],
        [10, 60, 80],
        [20, -60, 75]
    ]
};
result = ctx.parseOvation(datelineFixture, 0.5, 179);
assert.equal(result.localReady, true);
assert.equal(result.localLongitude, -179);
assert.equal(result.localIntensity, 44);
assert.ok(result.localDistanceKm > 200 && result.localDistanceKm < 230);

assert.throws(() => ctx.parseOvation({
    "Observation Time":"bad",
    "Forecast Time":"2026-10-28T08:45:00Z",
    coordinates:[[10,50,1],[10,-50,1]]
}, 0, 0));

assert.throws(() => ctx.parseOvation({
    "Observation Time":"2026-10-28T08:00:00Z",
    "Forecast Time":"2026-10-28T08:45:00Z",
    coordinates:[[10,50,1]]
}, 0, 0));

const policy = read("services/weather/AuroraPolicy.js");
assert.doesNotMatch(
    policy,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

const service = read("services/weather/AuroraService.qml");
assert.match(
    service,
    /^import QtQuick\s*\nimport Quickshell\s*\nimport Quickshell\.Io/m
);
assert.match(service, /property string targetLatitude: ""/);
assert.match(service, /property string targetLongitude: ""/);
assert.match(service, /property bool localReady: false/);
assert.match(service, /property real localIntensity: -1/);
assert.match(service, /property real localCellLatitude: 0/);
assert.match(service, /property real localCellLongitude: 0/);
assert.match(service, /property real localCellDistanceKm: -1/);
assert.match(
    service,
    /AuroraPolicy\.parseOvation\([\s\S]*?targetLatitude,[\s\S]*?targetLongitude/
);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/interval: 900000/g) || []).length, 1);
assert.equal((service.match(/interval: 60000/g) || []).length, 1);
assert.match(service, /onTargetLatitudeChanged: localReady = false/);
assert.match(service, /onTargetLongitudeChanged: localReady = false/);

const latHandler = service.match(/onTargetLatitudeChanged:[^\n]*/)[0];
const lonHandler = service.match(/onTargetLongitudeChanged:[^\n]*/)[0];
assert.doesNotMatch(latHandler, /refresh\(|running\s*=\s*true/);
assert.doesNotMatch(lonHandler, /refresh\(|running\s*=\s*true/);

// Existing OVATION endpoint/fetch ownership remains singular.
assert.equal(
    (service.match(/ovation_aurora_latest\.json/g) || []).length,
    1
);

const windowSource = read("widgets/weather/WeatherStationW.qml");
assert.match(
    windowSource,
    /id: spaceViewComponent[\s\S]*?StationSpace\s*\{[\s\S]*?spaceService: weatherStation\.spaceService[\s\S]*?weatherService: weatherStation\.weatherService/
);

const space = read("widgets/weather/StationSpace.qml");
assert.match(space, /property var weatherService: null/);
assert.match(
    space,
    /WeatherServices\.AuroraService\s*\{[\s\S]*?targetLatitude: space\.weatherService[\s\S]*?space\.weatherService\.latitude/
);
assert.match(
    space,
    /WeatherServices\.AuroraService\s*\{[\s\S]*?targetLongitude: space\.weatherService[\s\S]*?space\.weatherService\.longitude/
);
assert.match(space, /WEATHER FIX \/\/ NEAREST OVATION CELL/);
assert.match(space, /MODEL INTENSITY/);
assert.match(space, /localCellLatitude/);
assert.match(space, /localCellLongitude/);
assert.match(space, /KM FROM WEATHER FIX/);
assert.match(space, /NOT A LOCAL OBSERVATION/);
assert.match(
    space,
    /MODEL INTENSITY, NOT A GUARANTEE OF VISIBLE AURORA \/\/ NO EXTRA NOAA REQUEST/
);
assert.match(
    space,
    /30–90 MIN LOCATION \+ INTENSITY FORECAST \/\/ HEMISPHERE PEAKS \+ WEATHER-FIX CELL/
);
assert.doesNotMatch(
    space,
    /LOCAL AURORA PROBABILITY|CHANCE OF SEEING|VISIBILITY PROBABILITY|GUARANTEED VISIBLE/i
);

const auroraStart = space.indexOf(
    'title: "AURORA // 30-90 MIN FORECAST"'
);
const xrayStart = space.indexOf(
    'title: "SOLAR // LIVE X-RAY FLUX"',
    auroraStart
);
assert.ok(auroraStart >= 0 && xrayStart > auroraStart);
const auroraArea = space.slice(auroraStart, xrayStart);
assert.doesNotMatch(
    auroraArea,
    /Process\s*\{|Timer\s*\{|curl|Qt\.openUrlExternally|WebEngine/
);

console.log("Weather SPACE local OVATION nearest-cell reconstruction: PASS");
