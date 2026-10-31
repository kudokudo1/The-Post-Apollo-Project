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

const projection = load("widgets/weather/StationMapProjectionPolicy.js");
const radar = load("widgets/weather/StationRadarPolicy.js");

let bounds = projection.visibleBounds(900, 450, 4, -77, 38);
assert.equal(bounds.valid, true);
assert.ok(Math.abs(bounds.longitudeSpan - 90) < 1e-9);
assert.ok(Math.abs(bounds.latitudeSpan - 45) < 1e-9);

let area = radar.boundedArea(bounds, 90, 50);
assert.equal(area.valid, true);
assert.equal(area.longitudeSpan, 90);
assert.equal(area.latitudeSpan, 45);
assert.match(area.bbox, /^-?\d+\.\d{5},-?\d+\.\d{5},-?\d+\.\d{5},-?\d+\.\d{5}$/);

const world = radar.boundedArea(
    projection.visibleBounds(900, 450, 1, 0, 0), 90, 50
);
assert.equal(world.valid, false);
assert.equal(world.reason, "ZOOM IN // VIEW TOO WIDE");

const url = radar.exportImageUrl(area, 900, 450);
assert.ok(url.startsWith(
    "https://mapservices.weather.noaa.gov/eventdriven/rest/services/"
    + "radar/radar_base_reflectivity_time/ImageServer/exportImage?"
));
for (const token of [
    "bbox=" + area.bbox,
    "bboxSR=4326",
    "size=900,450",
    "imageSR=4326",
    "format=png32",
    "transparent=true",
    "adjustAspectRatio=false",
    "f=image"
])
    assert.ok(url.includes(token), token);
assert.equal(url.includes("&time="), false);

assert.equal(radar.normalizeHistoryMinutes(-5), 0);
assert.equal(radar.normalizeHistoryMinutes(30), 30);
assert.equal(radar.normalizeHistoryMinutes(999), 240);

const fixedNow = Date.UTC(2026, 9, 31, 21, 57, 23);
const roundedNow = Date.UTC(2026, 9, 31, 21, 50, 0);
assert.equal(radar.historyTimeMillis(fixedNow, 0), 0);
assert.equal(
    radar.historyTimeMillis(fixedNow, 30),
    roundedNow - 30 * 60 * 1000
);
assert.equal(
    radar.historyTimeMillis(fixedNow, 240),
    roundedNow - 240 * 60 * 1000
);

const options = Array.from(radar.historyOptions());
assert.deepEqual(
    options.map(row => [row.minutes, row.label]),
    [[0, "NOW"], [30, "-30M"], [60, "-1H"], [120, "-2H"], [240, "-4H"]]
);

const historicalTime = radar.historyTimeMillis(fixedNow, 120);
const historyUrl = radar.exportImageUrl(
    area, 900, 450, historicalTime
);
assert.ok(historyUrl.includes("&time=" + historicalTime));
assert.ok(historyUrl.endsWith("&f=image"));

assert.equal(radar.exportImageUrl(area, 10, 450), "");
assert.equal(radar.exportImageUrl(area, 900, 5000), "");
assert.equal(radar.exportImageUrl({valid:false}, 900, 450), "");

const snap = radar.snapshot(area);
assert.deepEqual(
    [snap.west, snap.south, snap.east, snap.north],
    [area.west, area.south, area.east, area.north]
);
assert.equal(radar.snapshot(null), null);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui, /StationRadarPolicy\.js" as RadarPolicy/);
assert.match(ui, /readonly property var mapVisibleBounds:/);
assert.match(ui, /FirmsAreaPolicy\.boundedArea\(mapVisibleBounds, 60, 40\)/);
assert.match(ui, /RadarPolicy\.boundedArea\(mapVisibleBounds, 90, 50\)/);
assert.match(ui, /function selectRadarHistory\(minutes\)/);
assert.match(ui, /function radarHistoryLabel\(minutes\)/);
assert.match(ui, /function radarUtcLabel\(timeMs\)/);
assert.match(ui, /function loadRadarSnapshot\(\)/);
assert.match(ui, /RadarPolicy\.historyTimeMillis\(/);
assert.match(ui, /RadarPolicy\.snapshot\(radarArea\)/);
assert.match(ui, /RadarPolicy\.exportImageUrl\(/);
assert.match(ui, /radarHistoryOptions:\s*RadarPolicy\.historyOptions\(\)/);
assert.match(ui, /model: stationDiscovery\.radarHistoryOptions/);
assert.match(ui, /SELECT FRAME \/\/ THEN LOAD \/\/ NOAA TIME WINDOW \/\/ NO AUTO-FETCH/);
assert.match(ui, /radarImageUrl = "";/);
assert.match(ui, /Qt\.callLater\(function\(\)[\s\S]*stationDiscovery\.radarImageUrl = nextUrl/);
assert.match(ui, /title: "RADAR \/\/ NOAA\/NWS MRMS BASE REFLECTIVITY \+ 4H HISTORY"/);
assert.match(ui, /"REFRESH RADAR" : "LOAD RADAR"/);
assert.match(ui, /MAX 90° × 50° VIEW \/\/ MANUAL LOAD \/\/ NO PAN AUTO-FETCH/);
assert.match(ui, /NOAA \/ NWS \/ MRMS \/\/ OFFICIAL BASE REFLECTIVITY \/\/ 4H MOVING HISTORY/);
assert.match(ui, /id: radarImage/);
assert.match(ui, /cache: false/);
assert.match(ui, /asynchronous: true/);
assert.match(ui, /fillMode: Image\.Stretch/);
assert.match(ui, /opacity: 0\.68/);
assert.match(ui, /stationDiscovery\.radarSnapshotBounds\.west/);
assert.match(ui, /stationDiscovery\.radarSnapshotBounds\.north/);
assert.match(ui, /stationDiscovery\.radarSnapshotBounds\.east/);
assert.match(ui, /stationDiscovery\.radarSnapshotBounds\.south/);
assert.match(ui, /z: 0\.1/);
assert.match(ui, /z: 0\.3/);
assert.match(ui, /NATURAL EARTH LAND \+ CONTEXT \/\/ LAT\/LON GRID \/\/ RADAR \+ SMOKE OVERLAYS/);
assert.match(ui, /NOAA\/NWS MRMS \/\/ BASE REFLECTIVITY \+ 4H HISTORY/);
assert.match(ui, /RAINVIEWER \/\/ PAST RADAR FALLBACK \/\/ 2H/);

// Loading is explicit only. Panning/zooming and selecting a historical
// frame must not trigger another provider request.
for (const forbidden of [
    "onMapZoomChanged", "onMapCenterLonChanged", "onMapCenterLatChanged",
    "onRadarHistoryMinutesChanged"
]) {
    const at = ui.indexOf(forbidden);
    if (at >= 0) {
        const tail = ui.slice(at, at + 400);
        assert.doesNotMatch(tail, /loadRadarSnapshot|radarImageUrl/);
    }
}

const policySource = read("widgets/weather/StationRadarPolicy.js");
assert.doesNotMatch(
    policySource,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

console.log("Weather MAP NOAA MRMS current + four-hour history overlay: PASS");
