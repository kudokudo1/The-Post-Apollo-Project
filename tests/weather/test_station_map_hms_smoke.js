#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
function load(relative) {
    const source = read(relative).replace(/^\.pragma library\s*/m, "");
    const context = {Date, Number, String, Array, JSON, Object, Math, isFinite};
    vm.runInNewContext(source, context, {filename: relative});
    return context;
}

const smoke = load("services/weather/HmsSmokePolicy.js");
const projection = load("widgets/weather/StationMapProjectionPolicy.js");

assert.equal(smoke.normalizeDensity("Light"), "light");
assert.equal(smoke.normalizeDensity("16"), "medium");
assert.equal(smoke.normalizeDensity("21"), "heavy");
assert.equal(smoke.normalizeDensity("garbage"), "unknown");
assert.match(smoke.fillStyle("heavy"), /237,152,26/);
assert.match(smoke.strokeStyle("light"), /85,207,202/);

const seam = Array.from(smoke.unwrapRing([
    [179, 50], [-179, 50], [-178, 51], [179, 50]
]));
assert.equal(seam.length, 4);
assert.deepEqual(seam.map(p => p[0]), [179, 181, 182, 179]);
for (let i = 1; i < seam.length; i++)
    assert.ok(Math.abs(seam[i][0] - seam[i - 1][0]) <= 180);

assert.equal(typeof projection.projectUnwrapped, "function");
let point = projection.projectUnwrapped(181, 50, 1000, 500, 1, 0, 0);
assert.equal(point.valid, true);
assert.ok(point.x > 1000);
point = projection.projectUnwrapped(181, 50, 1000, 500, 8, 157.5, 50);
assert.equal(point.valid, true);
assert.equal(point.visible, false);

const summary = smoke.summary([
    {density:"Light", ring:[[0,0],[1,0],[1,1],[0,0]]},
    {density:"Medium", ring:[[0,0],[1,0],[1,1],[0,0]]},
    {density:"Heavy", ring:[[0,0],[1,0],[1,1],[0,0]]},
    {density:"?", ring:[[0,0],[1,0],[1,1],[0,0]]},
]);
assert.equal(summary.count, 4);
assert.equal(summary.light, 1);
assert.equal(summary.medium, 1);
assert.equal(summary.heavy, 1);
assert.equal(summary.unknown, 1);
assert.equal(summary.vertices, 16);

const service = read("services/weather/HmsSmokeService.qml");
assert.match(service, /scripts\/weather\/hms_smoke_fetch\.py/);
assert.match(service, /property var polygons: \[\]/);
assert.match(service, /property string analysisDate: ""/);
assert.match(service, /lastRequestMs > 0 && now - lastRequestMs < 30000/);
assert.match(service, /HMS REQUEST COOLDOWN/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 0);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui, /WeatherServices\.HmsSmokeService\s*\{/);
assert.match(ui, /title: "SMOKE PLUMES \/\/ NOAA HMS"/);
assert.match(ui, /"REFRESH SMOKE" : "LOAD SMOKE"/);
assert.match(ui, /LATEST AVAILABLE DAILY ANALYSIS \/\/ NO AUTO-FETCH/);
assert.match(ui, /QUALITATIVE PLUME DENSITY \/\/ NOT GROUND-LEVEL PM2\.5/);
assert.match(ui, /id: smokeCanvas/);
assert.match(ui, /z: 0\.2/);
assert.match(ui, /SmokePolicy\.unwrapRing\(row\.ring\)/);
assert.match(ui, /MapProjection\.projectUnwrapped\(/);
assert.match(ui, /const offsets = \[-360, 0, 360\]/);
assert.match(ui, /SmokePolicy\.fillStyle\(row\.density\)/);
assert.match(ui, /SmokePolicy\.strokeStyle\(row\.density\)/);
assert.match(ui, /RADAR \+ SMOKE ARE DATA LAYERS, NOT BASEMAP/);
assert.match(ui, /NOAA HMS \/\/ SMOKE PLUME POLYGONS/);
assert.match(ui, /BASEMAP \/ OTHER POLYGON LAYERS", state:"NOT WIRED"/);

console.log("Weather MAP NOAA HMS smoke polygon overlay: PASS");
