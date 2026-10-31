#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {
    Date, Number, String, Array, Object, Math, JSON, isFinite,
    encodeURIComponent
};
vm.runInNewContext(
    read("services/weather/CoopsCoastalPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "finite", "boolValue", "distanceKm", "normalizeStation",
    "parseStationCatalog", "nearestStation", "cacheGet", "cachePut",
    "clearCacheForTest", "observationDatum", "coopsUtcMillis",
    "utcLabel", "parseWaterLevel", "predictionKind", "parsePredictions",
    "requestKey", "predictionWindow", "feetLabel"
])
    assert.equal(typeof ctx[fn], "function", fn);

const catalog = {
    stations: [
        {
            id:"8575512", name:"Annapolis", lat:38.9833, lng:-76.4816,
            state:"MD", tidal:true, greatlakes:false, timezone:"EST"
        },
        {
            id:"8577330", name:"Solomons Island", lat:"38.3172",
            lng:"-76.4500", state:"MD", tidal:"true", greatlakes:"false"
        },
        {
            id:"9063020", name:"Buffalo", lat:42.8774, lng:-78.8905,
            state:"NY", tidal:false, greatlakes:true
        }
    ]
};

const rows = Array.from(ctx.parseStationCatalog(catalog));
assert.equal(rows.length, 3);
assert.equal(rows[0].tidal, true);
assert.equal(rows[1].tidal, true);
assert.equal(rows[2].greatLakes, true);
assert.equal(ctx.observationDatum(rows[0]), "MLLW");
assert.equal(ctx.observationDatum(rows[2]), "LWD");
assert.equal(ctx.observationDatum({tidal:false, greatLakes:false}), "STND");

const nearest = ctx.nearestStation(rows, 38.98, -76.50);
assert.equal(nearest.id, "8575512");
assert.ok(nearest.distanceKm >= 0 && nearest.distanceKm < 5);
assert.equal(ctx.requestKey(38.98, -76.50), "38.980|-76.500");
assert.equal(ctx.requestKey("", -76.50), "");
assert.throws(() => ctx.parseStationCatalog({stations:[]}));
assert.throws(() => ctx.parseStationCatalog({error:{message:"bad"}}));

ctx.clearCacheForTest();
assert.equal(Array.from(ctx.cacheGet("waterlevels", 1000, 500)).length, 0);
assert.equal(ctx.cachePut("waterlevels", rows, 1000), true);
assert.equal(Array.from(ctx.cacheGet("waterlevels", 1200, 500)).length, 3);
assert.equal(Array.from(ctx.cacheGet("waterlevels", 2000, 500)).length, 0);
assert.equal(ctx.cachePut("bogus", rows, 1000), false);

const water = ctx.parseWaterLevel({
    data: [
        {t:"2026-10-31 12:00", v:"1.21", s:"0.03", f:"0,0,0,0", q:"p"},
        {t:"2026-10-31 12:06", v:"1.27", s:"0.02", f:"0,0,0,0", q:"v"}
    ]
});
assert.equal(water.value, 1.27);
assert.equal(water.sigma, 0.02);
assert.equal(water.sampleUtc, "2026-10-31 12:06Z");
assert.equal(water.qualityLabel, "VERIFIED");
assert.equal(ctx.coopsUtcMillis("2026-02-30 12:00"), -1);
assert.throws(() => ctx.parseWaterLevel({data:[]}));
assert.throws(() => ctx.parseWaterLevel({error:{message:"bad"}}));

const now = Date.UTC(2026, 9, 31, 12, 0);
const predictions = Array.from(ctx.parsePredictions({
    predictions: [
        {t:"2026-10-31 11:00", v:"0.20", type:"L"},
        {t:"2026-10-31 13:00", v:"1.70", type:"H"},
        {t:"2026-10-31 19:30", v:"0.15", type:"L"},
        {t:"2026-11-01 01:15", v:"1.90", type:"HH"},
        {t:"2026-11-01 07:10", v:"0.05", ty:"LL"}
    ]
}, now, 3));

assert.equal(predictions.length, 3);
assert.equal(predictions[0].type, "H");
assert.equal(predictions[0].label, "HIGH");
assert.equal(predictions[1].type, "L");
assert.equal(predictions[2].type, "HH");
assert.equal(predictions[2].high, true);
assert.equal(ctx.predictionKind("LL").high, false);

const window = ctx.predictionWindow(now);
assert.equal(window.beginDate, "20261031");
assert.equal(window.endDate, "20261102");
assert.equal(ctx.feetLabel(1.234), "1.23 ft");
assert.equal(ctx.feetLabel(null), "--");

const policy = read("services/weather/CoopsCoastalPolicy.js");
assert.doesNotMatch(
    policy,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

const service = read("services/weather/CoopsCoastalService.qml");
assert.match(
    service,
    /^import QtQuick\s*\nimport Quickshell\s*\nimport Quickshell\.Io/m
);
assert.match(
    service,
    /api\.tidesandcurrents\.noaa\.gov\/mdapi\/prod\//
);
assert.match(service, /webapi\/stations\.json\?type=/);
assert.match(
    service,
    /api\.tidesandcurrents\.noaa\.gov\/api\/prod\/datagetter/
);
assert.match(service, /type=" \+ kind/);
assert.match(service, /product=water_level/);
assert.match(service, /product=predictions/);
assert.match(service, /interval=hilo/);
assert.match(service, /datum=MLLW/);
assert.match(service, /CoastalPolicy\.observationDatum/);
assert.match(service, /CoastalPolicy\.predictionWindow\(Date\.now\(\)\)/);
assert.match(service, /Post-Apollo-WeatherStation\/0\.7/);
assert.match(service, /property string inflightWaterKey: ""/);
assert.match(service, /property string inflightTideKey: ""/);
assert.match(
    service,
    /inflightWaterKey !== currentKey \+ "\|" \+ waterStation\.id/
);
assert.match(
    service,
    /inflightTideKey !== currentKey \+ "\|" \+ tideStation\.id/
);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 3);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 2);
assert.match(service, /interval: 900000/);
assert.match(service, /interval: 250/);
assert.match(service, /readonly property int catalogTtlMs: 86400000/);
assert.match(service, /--proto", "=https"/);

const ground = read("widgets/weather/StationGround.qml");
assert.match(ground, /CoopsCoastalPolicy\.js" as CoastalPolicy/);
assert.match(ground, /WeatherServices\.CoopsCoastalService\s*\{/);
assert.match(ground, /title: "COAST \/\/ NOAA CO-OPS"/);
assert.match(ground, /OBSERVED WATER LEVEL/);
assert.match(ground, /TIDE PREDICTIONS \/\/ NEXT HIGH \+ LOW/);
assert.match(ground, /OBSERVATION STATION AND TIDE STATION MAY DIFFER/);
assert.match(ground, /MLLW DATUM IS USED FOR COASTAL TIDE PREDICTIONS/);
assert.match(ground, /NEAREST CO-OPS STATION ≠ LOCAL COAST/);
assert.match(ground, /NOT A STORM-SURGE OR FLOOD-IMPACT CLAIM/);

const coastStart = ground.indexOf('title: "COAST // NOAA CO-OPS"');
const heatStart = ground.indexOf(
    'title: "HEAT + FIRE WEATHER // NWS CONTEXT"', coastStart
);
assert.ok(coastStart >= 0 && heatStart > coastStart);
const coastArea = ground.slice(coastStart, heatStart);
assert.doesNotMatch(
    coastArea,
    /Process\s*\{|Timer\s*\{|curl|Qt\.openUrlExternally/
);

const workflow = read(".github/workflows/weather-teardown-contracts.yml");
assert.match(
    workflow,
    /node tests\/weather\/test_station_ground_coops_coastal\.js/
);

console.log("Weather GROUND NOAA CO-OPS coastal water levels + tides: PASS");
