#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const dataSource = read("widgets/weather/StationNaturalEarthLand110.js");
const data = {};
vm.runInNewContext(
    dataSource.replace(/^\.pragma library\s*/m, ""),
    data
);

assert.equal(typeof data.source, "object");
assert.equal(data.source.name, "Natural Earth 1:110m Land");
assert.equal(
    data.source.revision,
    "ca96624a56bd078437bca8184e78163e5039ad19"
);
assert.equal(data.source.license, "PUBLIC DOMAIN");
assert.equal(data.source.coordinateSystem, "CRS84 / LONGITUDE-LATITUDE");
assert.equal(data.source.polygonCount, 127);
assert.equal(data.source.pointCount, 5004);
assert.equal(Array.isArray(data.polygons), true);
assert.equal(data.polygons.length, 127);

let points = 0;
let holes = 0;
let minLon = Infinity;
let maxLon = -Infinity;
let minLat = Infinity;
let maxLat = -Infinity;

for (const polygon of data.polygons) {
    assert.equal(Array.isArray(polygon), true);
    assert.ok(polygon.length >= 1);
    for (let ringIndex = 0; ringIndex < polygon.length; ringIndex++) {
        const ring = polygon[ringIndex];
        assert.equal(Array.isArray(ring), true);
        assert.ok(ring.length >= 3);
        if (ringIndex > 0) holes++;
        for (const point of ring) {
            assert.equal(Array.isArray(point), true);
            assert.equal(point.length, 2);
            assert.ok(Number.isFinite(point[0]));
            assert.ok(Number.isFinite(point[1]));
            assert.ok(Math.abs(point[0]) <= 180);
            assert.ok(Math.abs(point[1]) <= 90);
            minLon = Math.min(minLon, point[0]);
            maxLon = Math.max(maxLon, point[0]);
            minLat = Math.min(minLat, point[1]);
            maxLat = Math.max(maxLat, point[1]);
            points++;
        }
    }
}

assert.equal(points, 5004);
assert.equal(holes, 1);
assert.ok(minLon <= -179.9);
assert.ok(maxLon >= 179.9);
assert.ok(minLat <= -89.9);
assert.ok(maxLat >= 83.5);

assert.doesNotMatch(
    dataSource,
    /\bProcess\s*\{|\bTimer\s*\{|XMLHttpRequest|curl|Qt\.openUrlExternally/
);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(
    ui,
    /import "StationNaturalEarthLand110\.js" as NaturalEarthLand/
);
assert.match(ui, /id: basemapCanvas/);
assert.match(ui, /property var landPolygons: NaturalEarthLand\.polygons/);
assert.match(ui, /z: 0\.05/);
assert.match(ui, /SmokePolicy\.unwrapRing\(rawRing\)/);
assert.match(ui, /MapProjection\.projectUnwrapped\(/);
assert.match(ui, /rgba\(22,5,31,0\.96\)/);
assert.match(ui, /rgba\(85,207,202,0\.58\)/);
assert.match(ui, /NATURAL EARTH 1:110m LAND BASEMAP", state:"CONNECTED"/);
assert.match(
    ui,
    /BASEMAP \/\/ NATURAL EARTH 1:110m LAND \/\/ PUBLIC DOMAIN \/\/ LOCAL ASSET \/\/ NO TILE NETWORK/
);
assert.match(
    ui,
    /NATURAL EARTH LAND \/\/ LAT\/LON GRID \/\/ RADAR \+ SMOKE OVERLAYS/
);

const basemapStart = ui.indexOf("id: basemapCanvas");
const radarStart = ui.indexOf("id: radarImage", basemapStart);
const smokeStart = ui.indexOf("id: smokeCanvas", radarStart);
assert.ok(basemapStart >= 0);
assert.ok(radarStart > basemapStart);
assert.ok(smokeStart > radarStart);

const basemapArea = ui.slice(basemapStart, radarStart);
assert.doesNotMatch(
    basemapArea,
    /\bProcess\s*\{|\bTimer\s*\{|XMLHttpRequest|curl|Qt\.openUrlExternally|https?:\/\//
);
assert.match(basemapArea, /ctx\.fill\(\)/);
assert.match(basemapArea, /ctx\.stroke\(\)/);

const radarArea = ui.slice(radarStart, smokeStart);
assert.match(radarArea, /z: 0\.1/);
const smokeTail = ui.slice(smokeStart, ui.indexOf("model: mapPlot.longitudeGrid", smokeStart));
assert.match(smokeTail, /z: 0\.2/);

const workflow = read(".github/workflows/weather-teardown-contracts.yml");
assert.match(
    workflow,
    /node tests\/weather\/test_station_map_natural_earth_basemap\.js/
);

console.log("Weather MAP local Natural Earth basemap: PASS");
