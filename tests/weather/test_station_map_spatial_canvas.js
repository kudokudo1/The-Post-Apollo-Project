#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {Date, Number, String, Array, JSON, Object, Math, isFinite};
vm.runInNewContext(
    read("widgets/weather/StationMapProjectionPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of ["clampView","project","unproject","visibleBounds","pan","zoomAt","plottable"])
    assert.equal(typeof ctx[fn], "function", fn);

let view = ctx.clampView(1, 90, 40);
assert.equal(view.zoom, 1);
assert.equal(view.centerLon, 0);
assert.equal(view.centerLat, 0);

view = ctx.clampView(2, 180, 90);
assert.equal(view.zoom, 2);
assert.equal(view.centerLon, 90);
assert.equal(view.centerLat, 45);

let point = ctx.project(0, 0, 720, 360, 1, 0, 0);
assert.equal(point.valid, true);
assert.equal(point.visible, true);
assert.equal(point.x, 360);
assert.equal(point.y, 180);

point = ctx.project(180, 90, 720, 360, 1, 0, 0);
assert.equal(point.x, 720);
assert.equal(point.y, 0);

assert.equal(ctx.project(181, 0, 720, 360, 1, 0, 0).valid, false);
assert.equal(ctx.project(null, 0, 720, 360, 1, 0, 0).valid, false);

let geo = ctx.unproject(360, 180, 720, 360, 1, 0, 0);
assert.equal(geo.valid, true);
assert.equal(geo.longitude, 0);
assert.equal(geo.latitude, 0);

geo = ctx.unproject(540, 90, 720, 360, 2, 0, 0);
assert.ok(Math.abs(geo.longitude - 45) < 1e-9);
assert.ok(Math.abs(geo.latitude - 22.5) < 1e-9);

// Dragging the map right should move the geographic center west.
view = ctx.pan(2, 0, 0, 72, 0, 720, 360);
assert.ok(Math.abs(view.centerLon + 18) < 1e-9);
assert.equal(view.centerLat, 0);

// Cursor-anchored zoom should preserve the geographic point under the cursor.
const before = ctx.unproject(540, 90, 720, 360, 1, 0, 0);
view = ctx.zoomAt(1, 0, 0, 540, 90, 720, 360, 1);
const after = ctx.unproject(
    540, 90, 720, 360,
    view.zoom, view.centerLon, view.centerLat
);
assert.ok(Math.abs(before.longitude - after.longitude) < 1e-9);
assert.ok(Math.abs(before.latitude - after.latitude) < 1e-9);
assert.ok(view.zoom > 1);

// Zoom is bounded and centers cannot pan past the visible world.
view = ctx.zoomAt(8, 0, 0, 360, 180, 720, 360, 1);
assert.equal(view.zoom, 8);
view = ctx.pan(8, 0, 0, -100000, -100000, 720, 360);
assert.ok(view.centerLon <= 157.5 && view.centerLon >= -157.5);
assert.ok(view.centerLat <= 78.75 && view.centerLat >= -78.75);

const rows = [
    {id:"a", latitude:38.6, longitude:-77.0},
    {id:"b", latitude:null, longitude:12},
    {id:"c", latitude:95, longitude:12},
    {id:"d", latitude:-12, longitude:151},
];
const plotted = Array.from(ctx.plottable(rows));
assert.deepEqual(plotted.map(x => x.id), ["a","d"]);
assert.deepEqual(Array.from(ctx.plottable(null)), []);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui, /StationMapProjectionPolicy\.js" as MapProjection/);
assert.match(ui, /property real mapZoom: 1/);
assert.match(ui, /property real mapCenterLon: 0/);
assert.match(ui, /property real mapCenterLat: 0/);
assert.match(ui, /MapProjection\.plottable\(source \? source\.rows : \[\]\)/);
assert.match(ui, /title: "SPATIAL PLOT \/\/ EONET \+ FIRMS POINTS"/);
assert.match(ui, /id: mapPlot/);
assert.match(ui, /height: 270/);
assert.match(ui, /id: mapPanArea/);
assert.match(ui, /preventStealing: true/);
assert.match(ui, /MapProjection\.pan\(/);
assert.match(ui, /MapProjection\.zoomAt\(/);
assert.match(ui, /wheel\.accepted = true/);
assert.match(ui, /onDoubleClicked:\s*stationDiscovery\.resetMapView\(\)/);
assert.match(ui, /model: stationDiscovery\.mapPointRows/);
assert.match(ui, /MapProjection\.project\(\s*modelData\.longitude,\s*modelData\.latitude/);
assert.match(ui, /stationDiscovery\.selectedMapEvent = modelData/);
assert.match(ui, /LAT\/LON GRID \/\/ RADAR \+ SMOKE ARE DATA LAYERS, NOT BASEMAP/);
assert.match(ui, /EONET \+ FIRMS POINTS \/\/ POLYGONS LISTED BELOW/);
assert.match(ui, /EONET POINT CANVAS \/\/ PAN \+ ZOOM/);
assert.match(ui, /BASEMAP \/ OTHER POLYGON LAYERS", state:"NOT WIRED"/);

const policySource = read("widgets/weather/StationMapProjectionPolicy.js");
assert.doesNotMatch(policySource, /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/);

console.log("Weather MAP spatial projection, zoom, pan and point canvas: PASS");
