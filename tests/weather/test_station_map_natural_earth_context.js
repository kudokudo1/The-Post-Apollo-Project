#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const sourceText = read("widgets/weather/StationNaturalEarthContext110.js");
const ctx = {Math, Number, String, Array, Object, JSON, isFinite};
vm.runInNewContext(
    sourceText.replace(/^\.pragma library\s*/m, ""),
    ctx
);

assert.equal(ctx.source.name, "Natural Earth 1:110m Context");
assert.equal(
    ctx.source.revision,
    "ca96624a56bd078437bca8184e78163e5039ad19"
);
assert.equal(ctx.source.license, "PUBLIC DOMAIN");
assert.equal(ctx.source.coordinateSystem, "CRS84 / LONGITUDE-LATITUDE");
assert.equal(ctx.source.admin0LineCount, 333);
assert.equal(ctx.source.admin0PointCount, 2995);
assert.equal(ctx.source.admin1LineCount, 109);
assert.equal(ctx.source.admin1PointCount, 903);
assert.equal(ctx.source.placeCount, 243);

assert.equal(ctx.admin0Lines.length, 333);
assert.equal(ctx.admin1Lines.length, 109);
assert.equal(ctx.places.length, 243);
assert.equal(typeof ctx.placesForZoom, "function");

const boundaryClasses = new Set(
    ctx.admin0Lines.map(row => row.className)
);
for (const value of [
    "International boundary (verify)",
    "Disputed (please verify)",
    "Claim boundary",
    "Indefinite (please verify)",
    "Indeterminant frontier",
    "Line of control (please verify)"
]) {
    assert.equal(boundaryClasses.has(value), true, value);
}

for (const row of ctx.admin0Lines.concat(ctx.admin1Lines)) {
    assert.ok(Array.isArray(row.line));
    assert.ok(row.line.length >= 2);
    for (const point of row.line) {
        assert.equal(point.length, 2);
        assert.ok(Number.isFinite(point[0]));
        assert.ok(Number.isFinite(point[1]));
        // Dateline-unwrapped line strings may extend beyond +/-180 before
        // map-copy offsets are applied.
        assert.ok(Math.abs(point[0]) <= 540);
        assert.ok(Math.abs(point[1]) <= 90);
    }
}

for (const row of ctx.places) {
    assert.ok(row.name.length > 0);
    assert.ok(Number.isFinite(row.longitude));
    assert.ok(Number.isFinite(row.latitude));
    assert.ok(Math.abs(row.longitude) <= 180);
    assert.ok(Math.abs(row.latitude) <= 90);
    assert.equal(typeof row.adm0cap, "boolean");
    assert.equal(typeof row.worldcity, "boolean");
    assert.equal(typeof row.megacity, "boolean");
}

const worldRows = Array.from(ctx.placesForZoom(1));
const regionalRows = Array.from(ctx.placesForZoom(3));
const detailRows = Array.from(ctx.placesForZoom(8));
assert.ok(worldRows.length > 0);
assert.ok(worldRows.length < regionalRows.length);
assert.ok(regionalRows.length < detailRows.length);
assert.equal(detailRows.length, 243);

assert.doesNotMatch(
    sourceText,
    /\bProcess\s*\{|\bTimer\s*\{|XMLHttpRequest|curl|Qt\.openUrlExternally/
);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(
    ui,
    /import "StationNaturalEarthContext110\.js" as NaturalEarthContext/
);
assert.match(ui, /property bool mapShowCountryBorders: true/);
assert.match(ui, /property bool mapShowAdmin1: false/);
assert.match(ui, /property bool mapShowPlaces: true/);
assert.match(
    ui,
    /NaturalEarthContext\.placesForZoom\(mapZoom\)/
);
assert.match(ui, /label: "BORDERS: "/);
assert.match(ui, /label: "STATES: "/);
assert.match(ui, /label: "PLACES: "/);
assert.match(
    ui,
    /REFERENCE CARTOGRAPHY \/\/ DISPUTED \/ CLAIM LINES ARE DISTINCT \/\/ NOT A LEGAL POSITION/
);

assert.match(ui, /id: mapContextLineCanvas/);
assert.match(ui, /z: 0\.08/);
assert.match(ui, /NaturalEarthContext\.admin0Lines/);
assert.match(ui, /NaturalEarthContext\.admin1Lines/);
assert.match(ui, /function disputedClass\(value\)/);
assert.match(ui, /text\.indexOf\("disputed"\) >= 0/);
assert.match(ui, /text\.indexOf\("claim"\) >= 0/);
assert.match(ui, /text\.indexOf\("line of control"\) >= 0/);
assert.match(ui, /rgba\(242,190,78,0\.74\)/);
assert.match(ui, /rgba\(220,243,250,0\.34\)/);
assert.match(ui, /rgba\(91,95,212,0\.30\)/);
assert.match(ui, /showAdmin1 && viewZoom >= 1\.6/);

assert.match(ui, /id: mapPlaceLabelCanvas/);
assert.match(ui, /z: 0\.45/);
assert.match(ui, /function collides\(box, used\)/);
assert.match(ui, /row\.adm0cap \? "#C74EC7"/);
assert.match(ui, /row\.worldcity \|\| row\.megacity/);
assert.match(ui, /ctx\.fillText\(/);

assert.match(
    ui,
    /NATURAL EARTH ADMIN-0 REFERENCE BOUNDARIES/
);
assert.match(
    ui,
    /NATURAL EARTH ADMIN-1 STATE\/PROVINCE LINES/
);
assert.match(
    ui,
    /NATURAL EARTH POPULATED PLACES/
);

const borderStart = ui.indexOf("id: mapContextLineCanvas");
const radarStart = ui.indexOf("id: radarImage", borderStart);
const smokeStart = ui.indexOf("id: smokeCanvas", radarStart);
const placeStart = ui.indexOf("id: mapPlaceLabelCanvas", smokeStart);
const panStart = ui.indexOf("id: mapPanArea", placeStart);
assert.ok(borderStart >= 0);
assert.ok(radarStart > borderStart);
assert.ok(smokeStart > radarStart);
assert.ok(placeStart > smokeStart);
assert.ok(panStart > placeStart);

for (const area of [
    ui.slice(borderStart, radarStart),
    ui.slice(placeStart, panStart)
]) {
    assert.doesNotMatch(
        area,
        /\bProcess\s*\{|\bTimer\s*\{|XMLHttpRequest|curl|Qt\.openUrlExternally|https?:\/\//
    );
}

const workflow = read(".github/workflows/weather-teardown-contracts.yml");
assert.match(
    workflow,
    /node tests\/weather\/test_station_map_natural_earth_context\.js/
);

console.log("Weather MAP Natural Earth boundaries and places context: PASS");
