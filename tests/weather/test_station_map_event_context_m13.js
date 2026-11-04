#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("widgets/weather/StationEventContextPolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const ctx = {
    Date, Math, Number, String, Array, Object, JSON, RegExp,
    isFinite, isNaN
};
vm.runInNewContext(source, ctx, {
    filename: "widgets/weather/StationEventContextPolicy.js"
});

for (const fn of [
    "validPoint", "distanceKm", "sourceLabel", "normalizeSelected",
    "pointInBounds", "radarCoverage", "weatherFixDistance",
    "nearbyEvidence"
]) {
    assert.equal(typeof ctx[fn], "function", fn);
}

const gdacs = ctx.normalizeSelected("gdacs", {
    id: "FL:1:2",
    name: "Example Flood",
    eventTypeLabel: "FLOOD",
    latitude: 38.90,
    longitude: -77.02,
    timeMs: Date.UTC(2026, 10, 2, 14, 0, 0),
    toUtc: "2026-11-02 14:00 UTC"
});
assert.equal(gdacs.sourceLabel, "GDACS");
assert.equal(gdacs.title, "Example Flood");
assert.equal(gdacs.typeLabel, "FLOOD");
assert.equal(gdacs.hasPoint, true);
assert.equal(gdacs.coordinates, "38.900, -77.020");

const quake = ctx.normalizeSelected("usgs", {
    id: "usgs-1",
    magnitude: 4.6,
    place: "20 km SW of Example",
    latitude: 39.0,
    longitude: -77.1,
    time: Date.UTC(2026, 10, 2, 13, 30, 0)
});
assert.match(quake.title, /^M4\.6 \/\/ 20 km SW/);
assert.equal(quake.typeLabel, "EARTHQUAKE");
assert.equal(quake.hasPoint, true);

const eonet = ctx.normalizeSelected("eonet", {
    id: "EONET-1",
    title: "Example Wildfire",
    category: "Wildfires",
    latitude: 38.95,
    longitude: -77.10,
    rawTime: "2026-11-02T13:00:00Z",
    time: "2026-11-02 13:00 UTC"
});
assert.equal(eonet.sourceLabel, "NASA EONET");
assert.equal(eonet.typeLabel, "Wildfires");
assert.equal(eonet.hasPoint, true);

const polygon = ctx.normalizeSelected("eonet", {
    id: "EONET-POLYGON",
    title: "Polygon Event",
    category: "Severe Storms",
    latitude: null,
    longitude: null,
    rawTime: "2026-11-02T12:00:00Z",
    time: "2026-11-02 12:00 UTC"
});
assert.equal(polygon.hasPoint, false);
assert.equal(polygon.coordinates, "POINT LOCATION UNAVAILABLE");

const firms = ctx.normalizeSelected("firms", {
    id: "hotspot-1",
    title: "VIIRS HOTSPOT",
    latitude: 38.94,
    longitude: -77.08,
    acquiredUtc: "2026-11-02 13:55Z"
});
assert.equal(firms.sourceLabel, "NASA FIRMS");
assert.equal(firms.typeLabel, "THERMAL HOTSPOT");
assert.equal(firms.hasPoint, true);

assert.equal(ctx.normalizeSelected("unknown", {}), null);
assert.ok(ctx.distanceKm(38.9, -77.02, 38.9, -77.02) < 1e-9);
assert.ok(ctx.distanceKm(38.9, -77.02, 39.0, -77.1) > 0);
assert.equal(ctx.distanceKm(null, -77, 39, -77), -1);

const bounds = {
    valid: true,
    west: -78,
    south: 38,
    east: -76,
    north: 40
};
assert.equal(ctx.pointInBounds(38.9, -77.02, bounds), true);
assert.equal(ctx.pointInBounds(45, -77.02, bounds), false);

let radar = ctx.radarCoverage(
    gdacs,
    bounds,
    60,
    Date.UTC(2026, 10, 2, 13, 0, 0),
    true
);
assert.equal(radar.available, true);
assert.equal(radar.covered, true);
assert.equal(radar.frameLabel, "-60M");
assert.equal(radar.usingCache, true);
assert.equal(radar.status, "FRAME COVERS EVENT COORDINATE");

radar = ctx.radarCoverage(
    ctx.normalizeSelected("gdacs", {
        id:"far", name:"Far Event", eventTypeLabel:"FLOOD",
        latitude:50, longitude:-77, timeMs:1
    }),
    bounds, 0, 0, false
);
assert.equal(radar.covered, false);
assert.equal(radar.status, "EVENT OUTSIDE LOADED FRAME");

radar = ctx.radarCoverage(gdacs, null, 0, 0, false);
assert.equal(radar.available, false);
assert.equal(radar.status, "NO LOADED MRMS FRAME");

assert.ok(
    ctx.weatherFixDistance(gdacs, 38.91, -77.01) >= 0
);
assert.equal(
    ctx.weatherFixDistance(polygon, 38.91, -77.01),
    -1
);

const companions = Array.from(ctx.nearbyEvidence(
    gdacs,
    [
        {sourceId:"gdacs", rows:[{
            id:"same-source", name:"Other Flood",
            eventTypeLabel:"FLOOD", latitude:38.91, longitude:-77.01,
            timeMs:Date.UTC(2026,10,2,14,5,0)
        }]},
        {sourceId:"usgs", rows:[{
            id:"quake-near", magnitude:3.5, place:"Nearby",
            latitude:38.91, longitude:-77.00,
            time:Date.UTC(2026,10,2,14,2,0)
        }]},
        {sourceId:"eonet", rows:[{
            id:"fire-near", title:"Nearby Fire", category:"Wildfires",
            latitude:39.00, longitude:-77.10,
            rawTime:"2026-11-02T13:50:00Z"
        }]},
        {sourceId:"firms", rows:[{
            id:"hotspot-far", title:"VIIRS HOTSPOT",
            latitude:45, longitude:-77,
            acquiredUtc:"2026-11-02 13:55Z"
        }]}
    ],
    250,
    6
));
assert.equal(companions.length, 2);
assert.equal(companions[0].sourceId, "usgs");
assert.equal(companions[1].sourceId, "eonet");
assert.ok(companions[0].distanceKm <= companions[1].distanceKm);
assert.ok(companions.every(row => row.sourceId !== "gdacs"));

const map = read("widgets/weather/StationDiscovery.qml");
assert.match(map, /StationEventContextPolicy\.js" as EventContextPolicy/);
assert.match(map, /property var weatherService: null/);
assert.match(map, /readonly property string selectedContextSourceId:/);
assert.match(map, /selectedMapGdacsEvent !== null \? "gdacs"/);
assert.match(map, /selectedMapEarthquake !== null \? "usgs"/);
assert.match(map, /selectedMapEvent !== null \? "eonet"/);
assert.match(map, /selectedMapHotspot !== null \? "firms"/);
assert.match(map, /EventContextPolicy\.normalizeSelected/);
assert.match(map, /EventContextPolicy\.weatherFixDistance/);
assert.match(map, /EventContextPolicy\.radarCoverage/);
assert.match(map, /EventContextPolicy\.nearbyEvidence/);
assert.match(map, /"sourceId": "gdacs"/);
assert.match(map, /"sourceId": "usgs"/);
assert.match(map, /"sourceId": "eonet"/);
assert.match(map, /"sourceId": "firms"/);
assert.match(map, /250,\s*6/);
assert.match(map, /title: "EVENT CONTEXT \/\/ CROSS-DOMAIN"/);
assert.match(map, /StationEventContextCard\s*\{/);

// M13 must consume existing source owners only.
assert.doesNotMatch(map, /WeatherServices\.NowcoastLightningService\s*\{/);
assert.equal(
    (map.match(/WeatherServices\.MrmsRadarService\s*\{/g) || []).length,
    1
);

const card = read("widgets/weather/StationEventContextCard.qml");
for (const phrase of [
    "WEATHER FIX",
    "DISTANCE ONLY",
    "RADAR CONTEXT = GEOMETRIC FRAME COVERAGE ONLY",
    "IMAGE PIXELS ARE NOT INTERPRETED",
    "NEARBY INDEPENDENT MAP RECORDS",
    "NEARBY ≠ SAME EVENT",
    "SOURCE RECORDS REMAIN INDEPENDENT EVIDENCE"
]) {
    assert.ok(card.includes(phrase), phrase);
}
assert.match(card, /card\.radarContext\.status/);
assert.equal((card.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bFileView\s*\{/g) || []).length, 0);
assert.doesNotMatch(card, /curl|https:\/\//);

const station = read("widgets/weather/WeatherStationW.qml");
const earthPane = read("widgets/weather/StationEarthSubjectPane.qml");
assert.match(station,/weatherService: weatherStation\.weatherService/);
assert.match(earthPane,/StationDiscovery\s*\{/);
assert.match(earthPane,/weatherService: earthPane\.weatherService/);

// M14 promotes nowCOAST to one WeatherStation-level owner. M13 continues
// to reject a MAP-local duplicate and consumes the shared source only.
const ground = read("widgets/weather/StationGround.qml");
assert.equal(
    (ground.match(/WeatherServices\.NowcoastLightningService\s*\{/g) || []).length,
    0
);
assert.equal(
    (station.match(/WeatherServices\.NowcoastLightningService\s*\{/g) || []).length,
    1
);
assert.match(station,/lightningSource: lightningService/);
assert.match(earthPane,/lightningSource: earthPane\.lightningSource/);

console.log("Weather M13 cross-domain selected-event context: PASS");
