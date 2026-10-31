#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {Date, Number, String, Array, Object, Math, JSON, isFinite};
vm.runInNewContext(
    read("services/weather/NwpsRiverPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "normalizeFloodImpact", "normalizeFloodCrest",
    "normalizeFloodCategoryThresholds", "parseGaugeContext",
    "crestReading"
])
    assert.equal(typeof ctx[fn], "function", fn);

const fixture = {
    lid:"TEST1",
    usgsId:"01234567",
    description:"Test River near Town",
    county:"Test County",
    timeZone:"America/New_York",
    flood:{
        stageUnits:"ft",
        flowUnits:"kcfs",
        categories:{
            action:{stage:8, flow:null},
            minor:{stage:10, flow:null},
            moderate:{stage:12, flow:null},
            major:{stage:14, flow:null}
        },
        impacts:[
            {stage:14, statement:"Major roads and low structures flood."},
            {stage:9, statement:"Low agricultural areas begin flooding."},
            {stage:null, statement:"Broken row"}
        ],
        crests:{
            recent:[
                {
                    occurredTime:"2026-09-01T12:00:00Z",
                    stage:13.2, flow:6.4, preliminary:"P",
                    olddatum:false
                },
                {
                    occurredTime:"2025-05-10T12:00:00Z",
                    stage:11.1, flow:null, preliminary:"",
                    olddatum:false
                }
            ],
            historic:[
                {
                    occurredTime:"1972-06-23T12:00:00Z",
                    stage:19.5, flow:10.2, preliminary:"",
                    olddatum:true
                }
            ]
        }
    },
    hydronotes:[
        {
            statement:"Ice may affect stage readings.",
            effective:"2026-01-01T00:00:00Z",
            expiration:"2026-02-01T00:00:00Z"
        }
    ],
    inundation:{enabled:true}
};

const parsed = ctx.parseGaugeContext(fixture);
assert.equal(parsed.available, true);
assert.equal(parsed.lid, "TEST1");
assert.equal(parsed.usgsId, "01234567");
assert.equal(parsed.county, "Test County");
assert.equal(parsed.stageUnits, "ft");
assert.equal(parsed.flowUnits, "kcfs");
assert.deepEqual(
    Array.from(parsed.thresholds, x => x.id),
    ["action", "minor", "moderate", "major"]
);
assert.equal(parsed.thresholds[2].stage, 12);
assert.equal(parsed.impacts.length, 2);
assert.equal(parsed.impacts[0].stage, 9);
assert.equal(parsed.impacts[1].stage, 14);
assert.equal(parsed.recentCrests.length, 2);
assert.equal(parsed.recentCrests[0].stage, 13.2);
assert.equal(parsed.recentCrests[0].preliminary, "P");
assert.equal(parsed.historicCrests.length, 1);
assert.equal(parsed.historicCrests[0].oldDatum, true);
assert.equal(parsed.inundationAvailable, true);
assert.equal(parsed.notes.length, 1);
assert.equal(
    ctx.crestReading(parsed.recentCrests[0], "ft", "kcfs"),
    "13.20 ft // 6.40 kcfs"
);
assert.throws(() => ctx.parseGaugeContext(null));
assert.throws(() => ctx.parseGaugeContext([]));

const sparse = ctx.parseGaugeContext({
    lid:"EMPTY1",
    flood:{stageUnits:"ft", flowUnits:"cfs"}
});
assert.equal(sparse.available, false);
assert.equal(sparse.impacts.length, 0);
assert.equal(sparse.recentCrests.length, 0);

const service = read("services/weather/NwpsRiverService.qml");
assert.match(service, /property bool contextReady: false/);
assert.match(service, /property string inflightContextGaugeId: ""/);
assert.match(service, /RiverPolicy\.parseGaugeContext/);
assert.match(service, /function refreshContext\(\)/);
assert.match(service, /function acceptContext\(raw\)/);
assert.match(
    service,
    /String\(gauge\.lid \|\| ""\) !== inflightContextGaugeId/
);
assert.match(service, /river\.refreshContext\(\)/);
assert.match(
    service,
    /https:\/\/api\.water\.noaa\.gov\/nwps\/v1\/gauges\//
);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 3);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 2);
assert.match(service, /interval: 900000/);
assert.match(service, /interval: 250/);

// Metadata piggybacks on the existing gauge refresh lifecycle. There is no
// dedicated context timer.
const contextStart = service.indexOf("function refreshContext()");
const contextEnd = service.indexOf("function clearStageflow()", contextStart);
assert.ok(contextStart >= 0 && contextEnd > contextStart);
const contextFunctions = service.slice(contextStart, contextEnd);
assert.doesNotMatch(contextFunctions, /Timer\s*\{/);

const ground = read("widgets/weather/StationGround.qml");
assert.match(ground, /title: "FLOOD CONTEXT \/\/ IMPACTS \+ CRESTS"/);
assert.match(ground, /OFFICIAL FLOOD IMPACT STATEMENTS/);
assert.match(ground, /RECENT CRESTS/);
assert.match(ground, /HISTORIC CRESTS/);
assert.match(ground, /RiverPolicy\.crestReading/);
assert.match(ground, /riverService\.gaugeContext\.thresholds/);
assert.match(ground, /riverService\.gaugeContext\.impacts\.slice\(0, 4\)/);
assert.match(ground, /recentCrests\.slice\(0, 4\)/);
assert.match(ground, /historicCrests\.slice\(0, 4\)/);
assert.match(ground, /INUNDATION PRODUCT AVAILABLE/);
assert.match(ground, /IMPACT STATEMENTS \+ CREST RECORDS ARE LOCATION-SPECIFIC/);

console.log("Weather GROUND NWPS flood impacts and crest context: PASS");
