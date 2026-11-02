#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const policySource = read("widgets/weather/StationEventContextPolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const ctx = {
    Date, Math, Number, String, Array, Object, JSON, RegExp,
    isFinite, isNaN
};
vm.runInNewContext(policySource, ctx, {
    filename: "widgets/weather/StationEventContextPolicy.js"
});

assert.equal(typeof ctx.lightningCoverage, "function");
assert.equal(typeof ctx.plainBoundsAvailable, "function");

const selected = ctx.normalizeSelected("gdacs", {
    id: "FL:14:1",
    name: "Shared Lightning Test",
    eventTypeLabel: "FLOOD",
    latitude: 38.90,
    longitude: -77.02,
    timeMs: Date.UTC(2026, 10, 2, 15, 0, 0),
    toUtc: "2026-11-02 15:00 UTC"
});

const bbox = {
    west: -80,
    south: 36,
    east: -74,
    north: 42
};
assert.equal(ctx.plainBoundsAvailable(bbox), true);
assert.equal(ctx.pointInBounds(38.90, -77.02, bbox), true);
assert.equal(
    ctx.pointInBounds(
        38.90, -77.02,
        {valid:false, west:-80, south:36, east:-74, north:42}
    ),
    false
);

let lightning = ctx.lightningCoverage(
    selected,
    bbox,
    true,
    "2026-11-02T14:45:00.000Z",
    15,
    8,
    320,
    false
);
assert.equal(lightning.available, true);
assert.equal(lightning.covered, true);
assert.equal(lightning.status, "FRAME COVERS EVENT COORDINATE");
assert.equal(lightning.windowMinutes, 15);
assert.equal(lightning.resolutionKm, 8);
assert.equal(lightning.radiusKm, 320);
assert.equal(lightning.usingCache, false);
assert.equal(lightning.timeLabel, "2026-11-02T14:45:00.000Z");

lightning = ctx.lightningCoverage(
    ctx.normalizeSelected("gdacs", {
        id:"far",
        name:"Far Event",
        eventTypeLabel:"FLOOD",
        latitude:50,
        longitude:-77,
        timeMs:1
    }),
    bbox,
    true,
    "LATEST",
    15,
    8,
    320,
    true
);
assert.equal(lightning.available, true);
assert.equal(lightning.covered, false);
assert.equal(lightning.status, "EVENT OUTSIDE LIGHTNING FRAME");
assert.equal(lightning.usingCache, true);

lightning = ctx.lightningCoverage(
    selected, bbox, false, "", 15, 8, 320, false
);
assert.equal(lightning.available, false);
assert.equal(lightning.status, "NO LOADED LIGHTNING FRAME");

const nonPoint = ctx.normalizeSelected("eonet", {
    id:"polygon",
    title:"Polygon Event",
    category:"Severe Storms",
    latitude:null,
    longitude:null,
    rawTime:"2026-11-02T14:00:00Z"
});
lightning = ctx.lightningCoverage(
    nonPoint, bbox, true, "LATEST", 15, 8, 320, false
);
assert.equal(lightning.covered, false);
assert.equal(lightning.status, "EVENT HAS NO POINT COORDINATE");

const station = read("widgets/weather/WeatherStationW.qml");
const ground = read("widgets/weather/StationGround.qml");
const map = read("widgets/weather/StationDiscovery.qml");
const card = read("widgets/weather/StationEventContextCard.qml");
const service = read("services/weather/NowcoastLightningService.qml");

assert.equal(
    (station.match(/WeatherServices\.NowcoastLightningService\s*\{/g) || []).length,
    1
);
assert.equal(
    (ground.match(/WeatherServices\.NowcoastLightningService\s*\{/g) || []).length,
    0
);
assert.equal(
    (map.match(/WeatherServices\.NowcoastLightningService\s*\{/g) || []).length,
    0
);

const ownerStart = station.indexOf(
    "WeatherServices.NowcoastLightningService {"
);
const ownerEnd = station.indexOf(
    "// Shared keyboard-ownership contract",
    ownerStart
);
assert.ok(ownerStart >= 0 && ownerEnd > ownerStart);
const owner = station.slice(ownerStart, ownerEnd);
assert.match(owner, /id: lightningService/);
assert.match(owner, /weatherStation\.menuOpen/);
assert.match(owner, /weatherStation\.currentView === "ground"/);
assert.match(owner, /weatherStation\.currentView === "map"/);
assert.match(owner, /weatherStation\.weatherService\.latitude/);
assert.match(owner, /weatherStation\.weatherService\.longitude/);

assert.match(
    station,
    /StationGround\s*\{[\s\S]*?lightningSource: lightningService/
);
assert.match(
    station,
    /StationDiscovery\s*\{[\s\S]*?domain: "map"[\s\S]*?lightningSource: lightningService/
);

assert.match(ground, /property var lightningSource: null/);
assert.match(
    ground,
    /readonly property var lightningService: lightningSource/
);
assert.match(ground, /title: "LIGHTNING \/\/ NOAA NOWCOAST"/);
assert.match(ground, /lightningService\.imageUrl/);

assert.match(map, /property var lightningSource: null/);
assert.match(
    map,
    /RuntimePolicy\.displayRow\(\s*"lightning"/
);
assert.match(map, /"detail": "WEATHER-FIX 15M DENSITY"/);
assert.match(
    map,
    /EventContextPolicy\.lightningCoverage\(/
);
assert.match(map, /readonly property var selectedLightningContext:/);
assert.match(
    map,
    /lightningContext:\s*stationDiscovery\.selectedLightningContext/
);

assert.match(card, /property var lightningContext: null/);
assert.match(card, /card\.lightningContext\.status/);
for (const phrase of [
    "LIGHTNING CONTEXT = GEOMETRIC FRAME COVERAGE ONLY",
    "DENSITY PIXELS ARE NOT INTERPRETED"
]) {
    assert.ok(card.includes(phrase), phrase);
}
assert.equal((card.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bFileView\s*\{/g) || []).length, 0);

// Provider machinery remains unchanged: one fetch process, one 15-minute
// provider timer, one short debounce timer, and the existing frame cache.
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 2);
assert.match(service, /interval: 900000/);
assert.match(
    service,
    /running: lightning\.active && lightning\.configured/
);
assert.match(service, /weather_frame_cache\.py/);
assert.match(service, /"lightning"/);

// Shared ownership must not turn MAP into an independent fetcher.
assert.doesNotMatch(map, /nowcoast_lightning_snapshot\.py/);
assert.doesNotMatch(map, /nowcoast\.noaa\.gov/);

console.log("Weather M14 shared lightning ownership and MAP context: PASS");
