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
    "normalizeStageflowProduct", "parseStageflow",
    "seriesTail", "seriesHead", "seriesWindow", "seriesStats",
    "normalizedSeriesBars", "pointReading", "utcLabel"
])
    assert.equal(typeof ctx[fn], "function", fn);

const payload = {
    observed: {
        pedts: "HGIRG",
        issuedTime: "2026-10-27T10:30:00Z",
        wfo: "LWX",
        timeZone: "EST5EDT",
        primaryName: "Stage",
        primaryUnits: "ft",
        secondaryName: "Flow",
        secondaryUnits: "kcfs",
        data: [
            {
                validTime:"2026-10-27T10:00:00Z",
                generatedTime:"2026-10-27T10:05:00Z",
                primary:4.10, secondary:0.82
            },
            {
                validTime:"2026-10-27T09:00:00Z",
                generatedTime:"2026-10-27T09:05:00Z",
                primary:3.95, secondary:0.79
            },
            {
                validTime:"2026-10-27T08:00:00Z",
                generatedTime:"2026-10-27T08:05:00Z",
                primary:3.80, secondary:0.75
            },
            {
                validTime:"2026-10-27T07:00:00Z",
                generatedTime:"2026-10-27T07:05:00Z",
                primary:null, secondary:null
            }
        ]
    },
    forecast: {
        peds: "HGIFZ",
        issued_time: "2026-10-27T10:45:00Z",
        primary_name: "Stage",
        primaryUnit: "ft",
        secondary_name: "Flow",
        secondaryUnit: "kcfs",
        data: [
            {valid_time:"2026-10-27T13:00:00Z", primary:5.40, secondary:1.05},
            {valid_time:"2026-10-27T11:00:00Z", primary:4.50, secondary:0.90},
            {valid_time:"2026-10-27T12:00:00Z", primary:4.90, secondary:0.96}
        ]
    }
};

const parsed = ctx.parseStageflow(payload);
assert.equal(parsed.observed.available, true);
assert.equal(parsed.observed.pedts, "HGIRG");
assert.equal(parsed.observed.issuedLabel, "2026-10-27 10:30Z");
assert.equal(parsed.observed.primaryName, "STAGE");
assert.equal(parsed.observed.primaryUnits, "ft");
assert.equal(parsed.observed.secondaryName, "FLOW");
assert.equal(parsed.observed.secondaryUnits, "kcfs");
assert.equal(parsed.observed.data.length, 3);
assert.deepEqual(
    Array.from(parsed.observed.data, x => x.validLabel),
    [
        "2026-10-27 08:00Z",
        "2026-10-27 09:00Z",
        "2026-10-27 10:00Z"
    ]
);

assert.equal(parsed.forecast.available, true);
assert.equal(parsed.forecast.pedts, "HGIFZ");
assert.equal(parsed.forecast.issuedLabel, "2026-10-27 10:45Z");
assert.deepEqual(
    Array.from(parsed.forecast.data, x => x.validLabel),
    [
        "2026-10-27 11:00Z",
        "2026-10-27 12:00Z",
        "2026-10-27 13:00Z"
    ]
);

assert.deepEqual(
    Array.from(ctx.seriesTail(parsed.observed, 2), x => x.primary),
    [3.95, 4.10]
);
assert.deepEqual(
    Array.from(ctx.seriesHead(parsed.forecast, 2), x => x.primary),
    [4.50, 4.90]
);
assert.equal(
    ctx.pointReading(parsed.observed, parsed.observed.data[2]),
    "4.10 ft // FLOW 0.82 kcfs"
);

const windowRows = ctx.seriesWindow(parsed.observed, 12);
assert.equal(windowRows.length, 3);
const stats = ctx.seriesStats(parsed.observed, 12);
assert.equal(stats.available, true);
assert.equal(stats.points, 3);
assert.equal(stats.minimum, 3.8);
assert.equal(stats.maximum, 4.1);
assert.ok(Math.abs(stats.delta - 0.3) < 0.000001);
assert.equal(stats.direction, "RISING");
assert.equal(stats.spanHours, 2);

const bars = ctx.normalizedSeriesBars(parsed.observed, 12);
assert.equal(bars.length, 3);
assert.equal(bars[0].fraction, 0);
assert.equal(bars[2].fraction, 1);
assert.equal(ctx.seriesStats(null, 12).available, false);
assert.equal(ctx.normalizedSeriesBars(null, 12).length, 0);

assert.equal(
    ctx.pointReading(
        {primaryUnits:"ft", secondaryName:"", secondaryUnits:""},
        {primary:4.1, secondary:null}
    ),
    "4.10 ft"
);

// One product may legitimately be absent. Do not turn a missing forecast into
// an invalid observed-series response.
const observedOnly = ctx.parseStageflow({
    observed: payload.observed,
    forecast: null
});
assert.equal(observedOnly.observed.available, true);
assert.equal(observedOnly.forecast.available, false);
assert.throws(() => ctx.parseStageflow({}));

const service = read("services/weather/NwpsRiverService.qml");
assert.match(service, /property bool stageflowReady: false/);
assert.match(service, /property bool stageflowFailed: false/);
assert.match(service, /property string stageflowGaugeId: ""/);
assert.match(service, /property string inflightStageflowGaugeId: ""/);
assert.match(service, /function refreshStageflow\(\)/);
assert.match(service, /inflightStageflowGaugeId = String\(gauge\.lid\)/);
assert.match(
    service,
    /https:\/\/api\.water\.noaa\.gov\/nwps\/v1\/gauges\/[\s\S]*?encodeURIComponent\(inflightStageflowGaugeId\)[\s\S]*?\/stageflow/
);
assert.match(service, /RiverPolicy\.parseStageflow/);
assert.match(
    service,
    /String\(gauge\.lid \|\| ""\)[\s\S]*?!== inflightStageflowGaugeId[\s\S]*?return;/
);
assert.match(
    service,
    /currentId !== river\.inflightStageflowGaugeId[\s\S]*?river\.refreshStageflow\(\)/
);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 2);
assert.equal((service.match(/interval: 900000/g) || []).length, 1);
assert.doesNotMatch(service, /National Water Model|\/reaches\/|streamflow\?series=/i);

const ground = read("widgets/weather/StationGround.qml");
assert.match(ground, /title: "STAGEFLOW \/\/ OBSERVED \+ OFFICIAL FORECAST"/);
assert.match(ground, /OBSERVED \/\/ LAST /);
assert.match(ground, /OFFICIAL FORECAST \/\/ NEXT /);
assert.match(ground, /RiverPolicy\.seriesTail/);
assert.match(ground, /RiverPolicy\.seriesHead/);
assert.match(ground, /OBS ISSUED \/\/ /);
assert.match(ground, /FORECAST ISSUED \/\/ /);
assert.match(ground, /NO OFFICIAL FORECAST SERIES RETURNED/);
assert.match(ground, /OBSERVED HYDROGRAPH \/\/ /);
assert.match(ground, /RiverPolicy\.seriesWindow/);
assert.match(ground, /RiverPolicy\.seriesStats/);
assert.match(ground, /RiverPolicy\.normalizedSeriesBars/);
assert.match(ground, /MIN \/\/ /);
assert.match(ground, /MAX \/\/ /);
assert.match(ground, /DELTA \/\/ /);
assert.match(
    ground,
    /OBSERVED AND FORECAST SERIES ARE SEPARATE NWPS PRODUCTS \/\/ FORECAST VALUES ARE PREDICTIONS, NOT MEASUREMENTS/
);

const start = ground.indexOf(
    'title: "STAGEFLOW // OBSERVED + OFFICIAL FORECAST"'
);
const end = ground.indexOf(
    "BOUNDED WEATHER-LOCATION PROXIMITY LOOKUP",
    start
);
assert.ok(start >= 0 && end > start);
const stageflowUi = ground.slice(start, end);
assert.doesNotMatch(
    stageflowUi,
    /Process\s*\{|curl|National Water Model|Qt\.openUrlExternally/
);

console.log("Weather GROUND NWPS observed/forecast stageflow separation: PASS");
