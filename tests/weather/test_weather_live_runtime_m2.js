#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const policySource = read("services/weather/WeatherRuntimePolicy.js");
const ctx = {Date, Math, Number, String, Array, Object, JSON, isFinite};
vm.runInNewContext(
    policySource.replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "displayRow", "statusToken", "cadenceLabel",
    "rowStateLabel", "rowAgeLabel", "summarizeRows"
])
    assert.equal(typeof ctx[fn], "function", fn);

const now = Date.parse("2026-11-02T08:30:00Z");
let row = ctx.displayRow(
    "weather",
    {
        active:true, ready:true, loading:false, errorText:"",
        receivedAt:now - 5 * 60000,
        observedAt:now - 12 * 60000
    },
    now
);
assert.equal(row.transport, "READY");
assert.equal(row.freshness, "FRESH");
assert.equal(row.receivedAgeMinutes, 5);
assert.equal(row.observationAgeMinutes, 12);
assert.equal(ctx.statusToken(row), "cyan");
assert.equal(ctx.cadenceLabel(row), "15m");
assert.equal(ctx.rowStateLabel(row), "READY // FRESH");
assert.equal(ctx.rowAgeLabel(row), "RX 5m // OBS 12m");

row = ctx.displayRow(
    "firms",
    {active:true, ready:true, detail:"VIEWPORT REQUEST"},
    now
);
assert.equal(row.freshness, "SNAPSHOT");
assert.equal(ctx.statusToken(row), "magenta");
assert.equal(ctx.cadenceLabel(row), "ON REQUEST");
assert.equal(ctx.rowAgeLabel(row), "RX --");

row = ctx.displayRow(
    "moon",
    {active:true, ready:true},
    now
);
assert.equal(row.freshness, "KEYED");
assert.equal(ctx.statusToken(row), "blue");
assert.equal(ctx.cadenceLabel(row), "ON KEY CHANGE");

row = ctx.displayRow(
    "sky-local",
    {active:true, ready:true, observedAt:now},
    now
);
assert.equal(row.freshness, "LOCAL");
assert.equal(ctx.statusToken(row), "green");
assert.equal(ctx.cadenceLabel(row), "LOCAL");
assert.equal(ctx.rowAgeLabel(row), "LOCAL NOW // OBS <1m");

const summary = ctx.summarizeRows([
    ctx.displayRow("weather", {
        active:true, ready:true, receivedAt:now - 5 * 60000
    }, now),
    ctx.displayRow("river", {
        active:true, ready:false, loading:true
    }, now),
    ctx.displayRow("firms", {
        active:true, ready:true
    }, now),
    ctx.displayRow("moon", {
        active:true, ready:true
    }, now),
    ctx.displayRow("sky-local", {
        active:true, ready:true
    }, now)
]);
assert.equal(summary.total, 5);
assert.equal(summary.ready, 4);
assert.equal(summary.loading, 1);
assert.equal(summary.manual, 1);
assert.equal(summary.keyed, 1);
assert.equal(summary.local, 1);

const catalog = Array.from(ctx.sourceCatalog());
assert.ok(catalog.some(row => row.id === "mrms-radar"
                           && row.mode === "MANUAL"
                           && row.owner === "widgets/weather/StationDiscovery.qml"));
assert.ok(catalog.some(row => row.id === "sky-local"
                           && row.mode === "LOCAL_CALC"
                           && row.owner === "widgets/weather/StationSky.qml"));

const rack = read("widgets/weather/StationRuntimeRack.qml");
assert.match(rack, /LIVE RUNTIME \/\/ CURRENT PAGE/);
assert.match(rack, /RuntimePolicy\.summarizeRows\(rows\)/);
assert.match(rack, /RuntimePolicy\.rowStateLabel\(modelData\)/);
assert.match(rack, /RuntimePolicy\.rowAgeLabel\(modelData\)/);
assert.match(rack, /RuntimePolicy\.cadenceLabel\(modelData\)/);
assert.match(rack, /RuntimePolicy\.statusToken\(row\)/);
assert.doesNotMatch(rack, /\bTimer\s*\{/);
assert.doesNotMatch(rack, /\bProcess\s*\{|curl|XMLHttpRequest|FileView/);

const pageContracts = [
    ["widgets/weather/StationHome.qml",
     ["weather","space-core","nws-alerts","home-history"]],
    ["widgets/weather/StationGround.qml",
     ["weather","nws-alerts","seismic","river","marine","coastal","lightning"]],
    ["widgets/weather/StationSky.qml",
     ["weather","moon","eclipses","celnav","iss-passes",
      "planet-rise-set","meteor-showers","sky-local"]],
    ["widgets/weather/StationSpace.qml",
     ["space-core","aurora","solar-flares","xray-flux","swpc-alerts",
      "solar-cycle","noaa-scales","kp-forecast"]],
    ["widgets/weather/StationDiscovery.qml",
     ["discovery","gdacs","seismic","firms","mrms-radar",
      "rainviewer","hms-smoke","gdelt-article-location"]]
];

for (const [file, ids] of pageContracts) {
    const src = read(file);
    assert.match(
        src,
        /WeatherRuntimePolicy\.js" as RuntimePolicy/,
        file + " runtime import"
    );
    assert.match(src, /property real runtimeNowMs:/, file + " runtime clock");
    assert.match(src, /readonly property var runtimeRows:/,
                 file + " runtime rows");
    assert.match(src, /StationRuntimeRack\s*\{/,
                 file + " runtime rack");
    for (const id of ids)
        assert.ok(src.includes('"' + id + '"'), file + " " + id);
}

const ground = read("widgets/weather/StationGround.qml");
assert.match(ground, /marineService\.station\.sampleMillis/);
assert.match(ground, /coastalService\.waterLevel\.sampleMillis/);
assert.match(ground, /lightningService\.latestTime/);

const sky = read("widgets/weather/StationSky.qml");
assert.match(sky, /"detail": "SOLAR POSITION \+ TWILIGHT"/);

const space = read("widgets/weather/StationSpace.qml");
assert.match(space, /auroraService\.observationTimeMs/);
assert.match(space, /xrayService\.sampleTimeMs/);

const discovery = read("widgets/weather/StationDiscovery.qml");
assert.match(discovery, /radarImage\.status === Image\.Ready/);
assert.match(discovery, /"observedAt": radarRequestedTimeMs/);
assert.match(discovery, /domain === "news"/);

const news = read("widgets/weather/StationNewsHub.qml");
assert.match(news, /property real runtimeNowMs:/);
assert.match(news, /readonly property var runtimeRows:/);
assert.match(news, /runtimeNowMs: stationNewsHub\.runtimeNowMs/);

const station = read("widgets/weather/WeatherStationW.qml");
assert.match(station, /readonly property real runtimeNowMs:/);
assert.match(station, /RuntimePolicy\.summarizeRows\(currentPageRuntimeRows\)/);
assert.match(station, /readonly property bool usesMapRuntime:/);
assert.match(station, /return "MAP LIVE";/);
assert.match(station, /currentPageRuntimeSummary\.ready \+ " READY"/);
assert.match(station, /runtimeNowMs: weatherStation\.runtimeNowMs/);

// One Station clock updates page ages. M2 adds no per-provider timer.
assert.match(
    station,
    /Timer\s*\{[\s\S]*interval:\s*30000[\s\S]*sourceStatusClock\+\+/
);

console.log("Weather live runtime M2 page status rack: PASS");
