#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

function loadPolicy(relative) {
    const source = read(relative).replace(/^\.pragma library\s*/m, "");
    const context = {
        Date, Math, Number, String, Array, Object, JSON,
        isFinite, isNaN, RegExp
    };
    vm.runInNewContext(source, context, {filename: relative});
    return context;
}

const rv = loadPolicy("services/weather/RainViewerRadarPolicy.js");

const base = 1793462400;
const frames = [];
for (let i = 0; i < 13; i++) {
    const time = base + i * 600;
    frames.push({
        time,
        path: "/v2/radar/" + time
    });
}

const parsed = rv.parseMetadata({
    version: "2.0.1",
    generated: base + 13 * 600,
    host: "https://tilecache.rainviewer.com",
    radar: {past: frames}
});
assert.equal(parsed.host, "https://tilecache.rainviewer.com");
assert.equal(parsed.frames.length, 13);
assert.equal(parsed.frames[0].time, base);
assert.equal(parsed.frames[12].time, base + 12 * 600);

assert.throws(
    () => rv.parseMetadata({
        host: "https://evil.example",
        radar: {past: frames}
    }),
    /Unsafe RainViewer tile host/
);
assert.throws(
    () => rv.parseMetadata({
        host: "https://tilecache.rainviewer.com",
        radar: {past: []}
    }),
    /No RainViewer past radar frames/
);

assert.equal(rv.normalizeHistoryMinutes(0), 0);
assert.equal(rv.normalizeHistoryMinutes(120), 120);
assert.equal(rv.normalizeHistoryMinutes(121), -1);
assert.equal(rv.normalizeHistoryMinutes(240), -1);

const latest = rv.selectFrame(parsed.frames, 0);
assert.equal(latest.time, base + 12 * 600);
assert.equal(latest.actualMinutes, 0);

const thirty = rv.selectFrame(parsed.frames, 30);
assert.equal(thirty.time, base + 9 * 600);
assert.equal(thirty.actualMinutes, 30);

const twoHours = rv.selectFrame(parsed.frames, 120);
assert.equal(twoHours.time, base);
assert.equal(twoHours.actualMinutes, 120);
assert.equal(rv.selectFrame(parsed.frames, 240), null);

const world = {
    valid: true,
    west: -180,
    south: -90,
    east: 180,
    north: 90
};
const worldRange = rv.chooseTileRange(world, 9);
assert.equal(worldRange.valid, true);
assert.ok(worldRange.zoom >= 1 && worldRange.zoom <= 7);
assert.ok(worldRange.count > 0 && worldRange.count <= 9);

const plan = rv.buildPlan(
    world,
    parsed.host,
    latest.path,
    9,
    4
);
assert.equal(plan.valid, true);
assert.ok(plan.tileCount > 0 && plan.tileCount <= 9);
assert.equal(plan.stripCount, plan.tileCount * 4);
assert.equal(plan.strips.length, plan.stripCount);

const tileKeys = new Set();
for (const strip of plan.strips) {
    tileKeys.add(strip.tileKey);
    assert.ok(strip.url.startsWith(
        "https://tilecache.rainviewer.com/v2/radar/"
    ));
    assert.match(strip.url, /\/512\/[1-7]\/\d+\/\d+\/2\/1_1\.png$/);
    assert.equal(strip.sourceSize, 512);
    assert.equal(strip.sourceHeight, 128);
    assert.ok(strip.sourceY >= 0 && strip.sourceY < 512);
    assert.ok(strip.west < strip.east);
    assert.ok(strip.south < strip.north);
    assert.ok(Math.abs(strip.north) <= 85.051129);
    assert.ok(Math.abs(strip.south) <= 85.051129);
}
assert.equal(tileKeys.size, plan.tileCount);

const service = read("services/weather/RainViewerRadarService.qml");
assert.match(
    service,
    /https:\/\/api\.rainviewer\.com\/public\/weather-maps\.json/
);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 0);
assert.match(service, /nowMs - lastMetadataMs < 10 \* 60 \* 1000/);
assert.match(service, /now - lastRequestMs < 30000/);
assert.match(
    service,
    /RainViewerPolicy\.buildPlan\([\s\S]*?pendingBounds[\s\S]*?host[\s\S]*?frame\.path[\s\S]*?9[\s\S]*?4/
);
assert.match(service, /signal overlayReady\(\)/);
assert.match(service, /RAINVIEWER HISTORY LIMITED TO 2H/);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui, /property string radarDisplaySource: "noaa"/);
assert.match(ui, /function loadRainViewerFallback\(\)/);
assert.match(
    ui,
    /rainViewerRadarService\.request\([\s\S]*?radarHistoryMinutes[\s\S]*?mapVisibleBounds/
);
assert.match(ui, /function clearRainViewerFallback\(\)/);
assert.match(ui, /function showRadarSource\(sourceId\)/);
assert.match(ui, /WeatherServices\.RainViewerRadarService\s*\{/);
assert.match(
    ui,
    /onOverlayReady:[\s\S]*?radarDisplaySource = "rainviewer"/
);
assert.match(
    ui,
    /RAINVIEWER \/\/ PAST RADAR FALLBACK \/\/ 2H/
);
assert.match(ui, /title: "RADAR FALLBACK \/\/ RAINVIEWER PAST RADAR"/);
assert.match(ui, /"LOAD FALLBACK"/);
assert.match(ui, /"SHOW NOAA"/);
assert.match(ui, /"SHOW FALLBACK"/);
assert.match(
    ui,
    /WEATHER DATA BY RAINVIEWER WHEN FALLBACK IS SHOWN/
);
assert.match(
    ui,
    /RAINVIEWER API \/\/ SOURCE CREDIT REQUIRED \/\/ GLOBAL COVERAGE VARIES \/\/ PUBLIC FALLBACK HAS PAST RADAR ONLY/
);
assert.match(
    ui,
    /stationDiscovery\.radarHistoryMinutes <= 120/
);
assert.match(
    ui,
    /visible: stationDiscovery\.radarDisplaySource === "noaa"/
);
assert.match(
    ui,
    /model: stationDiscovery\.radarDisplaySource[\s\S]*?=== "rainviewer"[\s\S]*?rainViewerRadarService\.strips/
);
assert.match(ui, /sourceClipRect: Qt\.rect\(/);
assert.match(ui, /sourceSize\.width: modelData\.sourceSize/);
assert.match(ui, /sourceSize\.height: modelData\.sourceSize/);
assert.match(ui, /cache: true/);
assert.match(ui, /z: 0\.12/);
assert.match(ui, /MapProjection\.project\([\s\S]*?modelData\.west/);
assert.match(ui, /MapProjection\.project\([\s\S]*?modelData\.east/);

// The fallback remains explicit. No map motion or selector change may trigger
// a RainViewer network request.
for (const forbidden of [
    "onMapZoomChanged",
    "onMapCenterLonChanged",
    "onMapCenterLatChanged",
    "onRadarHistoryMinutesChanged"
]) {
    const at = ui.indexOf(forbidden);
    if (at >= 0) {
        const tail = ui.slice(at, at + 500);
        assert.doesNotMatch(
            tail,
            /loadRainViewerFallback|rainViewerRadarService\.request/
        );
    }
}

const workflow = read(".github/workflows/weather-teardown-contracts.yml");
assert.match(
    workflow,
    /node tests\/weather\/test_station_map_rainviewer_fallback\.js/
);

console.log("Weather MAP manual RainViewer radar fallback: PASS");
