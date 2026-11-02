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

for (const fn of [
    "isFloodLike",
    "compactReading",
    "latestObservedStage",
    "floodGaugeContext",
    "timelineRow",
    "evidenceTimeline"
]) {
    assert.equal(typeof ctx[fn], "function", fn);
}

const base = Date.UTC(2026, 10, 2, 15, 0, 0);

const selectedFlood = ctx.normalizeSelected("gdacs", {
    id:"FL:100:1",
    name:"Example Flood",
    eventTypeLabel:"FLOOD",
    latitude:38.90,
    longitude:-77.02,
    timeMs:base,
    toUtc:"2026-11-02 15:00 UTC"
});
assert.equal(ctx.isFloodLike(selectedFlood), true);

const selectedQuake = ctx.normalizeSelected("usgs", {
    id:"eq-1",
    magnitude:3.2,
    place:"Nearby",
    latitude:38.91,
    longitude:-77.03,
    time:base - 5 * 60000
});
assert.equal(ctx.isFloodLike(selectedQuake), false);

const gauge = {
    lid:"TEST1",
    name:"Test River near Town",
    latitude:38.95,
    longitude:-77.05,
    distanceKm:8.4,
    observedPrimary:10.25,
    primaryUnits:"ft",
    observedCategory:{id:"minor", label:"MINOR", rank:2},
    forecastCategory:{id:"moderate", label:"MODERATE", rank:3}
};
const gaugeContext = {
    available:true,
    thresholds:[
        {id:"action", label:"ACTION", stage:8, flow:null},
        {id:"minor", label:"MINOR", stage:10, flow:null},
        {id:"moderate", label:"MODERATE", stage:12, flow:null},
        {id:"major", label:"MAJOR", stage:14, flow:null}
    ],
    impacts:[
        {stage:10, statement:"Low areas begin flooding."},
        {stage:12, statement:"Some roads flood."},
        {stage:14, statement:"Major impacts."}
    ]
};
const stageflow = {
    observed:{
        available:true,
        primaryUnits:"ft",
        data:[
            {
                validMillis:base - 80 * 60000,
                validLabel:"2026-11-02 13:40Z",
                primary:9.80
            },
            {
                validMillis:base - 20 * 60000,
                validLabel:"2026-11-02 14:40Z",
                primary:10.25
            }
        ]
    },
    forecast:{available:false, data:[]}
};

let flood = ctx.floodGaugeContext(
    selectedFlood, gauge, gaugeContext, stageflow, 100
);
assert.equal(flood.relevant, true);
assert.equal(flood.available, true);
assert.equal(flood.gaugeId, "TEST1");
assert.equal(flood.gaugeName, "Test River near Town");
assert.ok(flood.eventGaugeDistanceKm > 0);
assert.ok(flood.eventGaugeDistanceKm < 100);
assert.equal(flood.weatherFixGaugeDistanceKm, 8.4);
assert.equal(flood.observedCategory, "MINOR");
assert.equal(flood.forecastCategory, "MODERATE");
assert.equal(flood.observedReading, "10.25 ft");
assert.equal(flood.thresholds.length, 4);
assert.equal(flood.impacts.length, 2);
assert.equal(flood.latestObserved.value, 10.25);
assert.equal(flood.latestObserved.timeMs, base - 20 * 60000);
assert.match(flood.reason, /OFFICIAL FLOOD METADATA/);

const nonFlood = ctx.floodGaugeContext(
    selectedQuake, gauge, gaugeContext, stageflow, 100
);
assert.equal(nonFlood.relevant, false);
assert.equal(nonFlood.available, false);
assert.match(nonFlood.reason, /NOT AN EXPLICIT FLOOD/);

const farFlood = ctx.normalizeSelected("gdacs", {
    id:"FL:far:1",
    name:"Far Flood",
    eventTypeLabel:"FLOOD",
    latitude:40.5,
    longitude:-77.0,
    timeMs:base,
    toUtc:"2026-11-02 15:00 UTC"
});
const far = ctx.floodGaugeContext(
    farFlood, gauge, gaugeContext, stageflow, 100
);
assert.equal(far.relevant, true);
assert.equal(far.available, false);
assert.ok(far.eventGaugeDistanceKm > 100);
assert.match(far.reason, /OUTSIDE 100 KM EVENT GATE/);

const noPointFlood = {
    sourceId:"eonet",
    sourceLabel:"NASA EONET",
    title:"Polygon Flood",
    typeLabel:"Floods",
    hasPoint:false,
    latitude:null,
    longitude:null,
    timeMs:base
};
const noPoint = ctx.floodGaugeContext(
    noPointFlood, gauge, gaugeContext, stageflow, 100
);
assert.equal(noPoint.relevant, true);
assert.equal(noPoint.available, false);
assert.match(noPoint.reason, /NO POINT COORDINATE/);

const radar = ctx.radarCoverage(
    selectedFlood,
    {valid:true, west:-78, south:38, east:-76, north:40},
    0,
    base - 5 * 60000,
    false
);
const lightning = ctx.lightningCoverage(
    selectedFlood,
    {west:-80, south:36, east:-74, north:42},
    true,
    new Date(base - 15 * 60000).toISOString(),
    15,
    8,
    320,
    true
);
const companions = [{
    sourceId:"eonet",
    sourceLabel:"NASA EONET",
    id:"event-near",
    title:"Nearby Flood Record",
    typeLabel:"Floods",
    latitude:38.93,
    longitude:-77.00,
    coordinates:"38.930, -77.000",
    timeMs:base - 10 * 60000,
    timeLabel:"2026-11-02 14:50 UTC",
    distanceKm:4
}];

const timeline = Array.from(ctx.evidenceTimeline(
    selectedFlood,
    companions,
    radar,
    lightning,
    flood,
    8
));
assert.equal(timeline.length, 5);
assert.deepEqual(
    timeline.map(row => row.sourceLabel),
    ["GDACS", "NOAA MRMS", "NASA EONET", "NOAA NOWCOAST", "NOAA NWPS"]
);
assert.deepEqual(
    timeline.map(row => row.kind),
    ["SELECTED EVENT", "RADAR FRAME", "NEARBY RECORD", "LIGHTNING FRAME", "OBSERVED STAGE"]
);
assert.ok(
    timeline.every((row, index) =>
        index === 0 || timeline[index - 1].timeMs >= row.timeMs
    )
);
assert.equal(timeline[0].provenance, "SOURCE EVENT TIME");
assert.equal(
    timeline[timeline.length - 1].provenance,
    "GAUGE OBSERVATION TIME"
);

const station = read("widgets/weather/WeatherStationW.qml");
const ground = read("widgets/weather/StationGround.qml");
const map = read("widgets/weather/StationDiscovery.qml");
const card = read("widgets/weather/StationEventContextCard.qml");
const service = read("services/weather/NwpsRiverService.qml");

assert.equal(
    (station.match(/WeatherServices\.NwpsRiverService\s*\{/g) || []).length,
    1
);
assert.equal(
    (ground.match(/WeatherServices\.NwpsRiverService\s*\{/g) || []).length,
    0
);
assert.equal(
    (map.match(/WeatherServices\.NwpsRiverService\s*\{/g) || []).length,
    0
);

const ownerStart = station.indexOf("WeatherServices.NwpsRiverService {");
const ownerEnd = station.indexOf(
    "// Shared keyboard-ownership contract",
    ownerStart
);
assert.ok(ownerStart >= 0 && ownerEnd > ownerStart);
const owner = station.slice(ownerStart, ownerEnd);
assert.match(owner, /id: riverService/);
assert.match(owner, /weatherStation\.menuOpen/);
assert.match(owner, /weatherStation\.currentView === "ground"/);
assert.match(owner, /weatherStation\.currentView === "map"/);
assert.match(owner, /cacheStore: weatherStation\.persistentCacheStore/);
assert.match(owner, /weatherStation\.weatherService\.latitude/);
assert.match(owner, /weatherStation\.weatherService\.longitude/);

assert.match(
    station,
    /StationGround\s*\{[\s\S]*?riverSource: riverService/
);
assert.match(
    station,
    /StationDiscovery\s*\{[\s\S]*?domain: "map"[\s\S]*?riverSource: riverService/
);

assert.match(ground, /property var riverSource: null/);
assert.match(ground, /readonly property var riverService: riverSource/);
assert.match(ground, /title: "RIVER \/\/ NOAA NWPS"/);

assert.match(map, /property var riverSource: null/);
assert.match(map, /RuntimePolicy\.displayRow\(\s*"river"/);
assert.match(map, /"detail": "WEATHER-FIX NEAREST GAUGE"/);
assert.match(map, /readonly property var selectedFloodContext:/);
assert.match(map, /EventContextPolicy\.floodGaugeContext\(/);
assert.match(map, /selectedFloodContext,\s*8/);
assert.match(map, /riverSource && riverSource\.contextReady/);
assert.match(map, /riverSource && riverSource\.stageflowReady/);
assert.match(map, /\n\s*100\s*\n\s*\)/);
assert.match(map, /readonly property var selectedEvidenceTimeline:/);
assert.match(map, /EventContextPolicy\.evidenceTimeline\(/);
assert.match(
    map,
    /floodContext:\s*stationDiscovery\.selectedFloodContext/
);
assert.match(
    map,
    /timelineRows:\s*stationDiscovery\.selectedEvidenceTimeline/
);
assert.doesNotMatch(map, /api\.water\.noaa\.gov/);

for (const phrase of [
    "FLOOD DOSSIER // NOAA NWPS",
    "NEARBY GAUGE EVIDENCE ONLY",
    "EVENT POINT ≠ GAUGE CATCHMENT",
    "NOT A FLOOD WARNING",
    "EVIDENCE TIMELINE // SOURCE-NATIVE TIMES",
    "ROWS RETAIN SOURCE + GROUP PROVENANCE",
    "NOT ONE MERGED INCIDENT HISTORY"
]) {
    assert.ok(card.includes(phrase), phrase);
}
assert.match(card, /card\.floodContext\.reason/);
assert.match(card, /card\.timelineRows\.slice\(0, 6\)/);
assert.equal((card.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bFileView\s*\{/g) || []).length, 0);

assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 3);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 2);
assert.match(service, /interval: 900000/);
assert.match(service, /interval: 250/);
assert.match(service, /running: river\.active && river\.configured/);

console.log("Weather M15 flood dossier and evidence timeline: PASS");
