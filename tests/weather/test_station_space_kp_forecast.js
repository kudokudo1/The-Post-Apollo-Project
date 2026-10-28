#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {Number, String, Array, Object, Math, isFinite};
vm.runInNewContext(
    read("services/weather/KpForecastPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "validTimeTag", "state", "noaaScale", "scaleLevel",
    "timeLabel", "normalizeRow", "parseRows", "predictedRows",
    "summarize", "emptySummary"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.equal(ctx.state("observed"), "observed");
assert.equal(ctx.state("ESTIMATED"), "estimated");
assert.equal(ctx.state("Predicted"), "predicted");
assert.equal(ctx.state("future"), "");

assert.equal(ctx.noaaScale("G1"), "G1");
assert.equal(ctx.noaaScale("g5"), "G5");
assert.equal(ctx.noaaScale("G0"), "");
assert.equal(ctx.noaaScale("G6"), "");
assert.equal(ctx.noaaScale(null), "");

assert.equal(
    ctx.timeLabel("2026-10-29T03:00:00"),
    "10-29 03:00"
);
assert.equal(ctx.timeLabel("bad"), "--");

const fixture = [
    {time_tag:"2026-10-28T12:00:00", kp:0.67, observed:"estimated", noaa_scale:null},
    {time_tag:"2026-10-27T21:00:00", kp:1.00, observed:"observed", noaa_scale:null},
    {time_tag:"2026-10-29T06:00:00", kp:5.00, observed:"predicted", noaa_scale:null},
    {time_tag:"2026-10-29T00:00:00", kp:1.67, observed:"predicted", noaa_scale:null},
    {time_tag:"2026-10-29T03:00:00", kp:3.00, observed:"predicted", noaa_scale:"G1"},
    {time_tag:"2026-10-29T09:00:00", kp:2.33, observed:"predicted", noaa_scale:null},
    {time_tag:"2026-10-29T12:00:00", kp:2.67, observed:"predicted", noaa_scale:"G2"},
    {time_tag:"2026-10-29T15:00:00", kp:1.33, observed:"predicted", noaa_scale:null},
    {time_tag:"2026-10-29T18:00:00", kp:1.67, observed:"predicted", noaa_scale:null},
    {time_tag:"2026-10-29T21:00:00", kp:1.67, observed:"predicted", noaa_scale:null},
    {time_tag:"2026-10-30T00:00:00", kp:4.00, observed:"predicted", noaa_scale:"G1"}
];

const parsed = Array.from(ctx.parseRows(fixture));
assert.equal(parsed.length, 11);
assert.equal(parsed[0].state, "observed");
assert.equal(parsed[1].state, "estimated");
assert.equal(parsed[2].timeTag, "2026-10-29T00:00:00");

const predicted = Array.from(ctx.predictedRows(fixture));
assert.equal(predicted.length, 9);
assert.ok(predicted.every(row => row.state === "predicted"));
assert.equal(predicted[0].timeTag, "2026-10-29T00:00:00");

let summary = ctx.summarize(fixture, 8);
assert.equal(summary.available, true);
assert.equal(summary.displayedBins, 8);
assert.equal(summary.totalPredicted, 9);
assert.equal(summary.rows.length, 8);
assert.equal(summary.firstTimeTag, "2026-10-29T00:00:00");
assert.equal(summary.lastTimeTag, "2026-10-29T21:00:00");
assert.equal(summary.firstTimeLabel, "10-29 00:00");
assert.equal(summary.lastTimeLabel, "10-29 21:00");
assert.equal(summary.maxKp, 5.00);
assert.equal(
    summary.maxNoaaScale,
    "G2",
    "highest NOAA-published scale wins even when a higher Kp row has no scale"
);
assert.equal(
    summary.rows[2].noaaScale,
    "",
    "Kp 5 row without provider scale remains unscaled"
);

summary = ctx.summarize(fixture, 3);
assert.equal(summary.displayedBins, 3);
assert.equal(summary.maxKp, 5.00);
assert.equal(summary.maxNoaaScale, "G1");

assert.equal(ctx.normalizeRow({
    time_tag:"bad", kp:2, observed:"predicted"
}), null);
assert.equal(ctx.normalizeRow({
    time_tag:"2026-10-29T00:00:00", kp:10, observed:"predicted"
}), null);
assert.equal(ctx.normalizeRow({
    time_tag:"2026-10-29T00:00:00", kp:2, observed:"future"
}), null);
assert.throws(() => ctx.parseRows({}));
assert.throws(() => ctx.summarize([
    {time_tag:"2026-10-28T00:00:00", kp:2, observed:"observed"}
], 8));

const service = read("services/weather/KpForecastService.qml");
assert.match(
    service,
    /^import QtQuick\s*\nimport Quickshell\s*\nimport Quickshell\.Io/m
);
assert.match(service, /Scope\s*\{/);
assert.match(
    service,
    /services\.swpc\.noaa\.gov\/products\/noaa-planetary-k-index-forecast\.json/
);
assert.match(service, /KpForecastPolicy\.summarize\([\s\S]*?8/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 1);
assert.match(service, /interval: 900000/);
assert.match(service, /repeat: true/);
assert.match(service, /running: forecast\.active/);
assert.match(service, /--proto", "=https"/);
assert.match(service, /Post-Apollo-WeatherStation\/0\.8/);

const policy = read("services/weather/KpForecastPolicy.js");
assert.match(policy, /row\.observed/);
assert.match(policy, /row\.noaa_scale/);
assert.match(policy, /row\.state === "predicted"/);
assert.doesNotMatch(
    policy,
    /kp\s*>=\s*5[\s\S]*?G1|kp\s*>=\s*6[\s\S]*?G2|kp\s*>=\s*7[\s\S]*?G3/,
    "policy must not convert Kp thresholds into NOAA G-scale values"
);

const space = read("widgets/weather/StationSpace.qml");
assert.match(space, /WeatherServices\.KpForecastService\s*\{/);
assert.match(space, /id: kpForecastService/);
assert.match(space, /active: space\.visible/);
assert.match(
    space,
    /title: "GEOMAGNETIC \/\/ NOAA KP FORECAST"/
);
assert.match(space, /MAX KP \/\/ NEXT BINS/);
assert.match(space, /NOAA SCALE \/\/ NEXT BINS/);
assert.match(space, /PREDICTED BINS/);
assert.match(space, /kpForecastService\.summary\.rows/);
assert.match(space, /modelData\.kp\.toFixed\(2\)/);
assert.match(space, /modelData\.noaaScale !== ""/);
assert.match(
    space,
    /ONLY NOAA ROWS TAGGED PREDICTED \/\/ OBSERVED \+ ESTIMATED EXCLUDED \/\/ NOAA SCALE SHOWN ONLY WHEN PUBLISHED/
);
assert.match(space, /NO LOCAL G-SCALE DERIVATION/);
assert.match(space, /onClicked: kpForecastService\.refresh\(\)/);

const forecastStart = space.indexOf(
    'title: "GEOMAGNETIC // NOAA KP FORECAST"'
);
const fieldStart = space.indexOf(
    'title: "FIELD // SOURCE TIMES"',
    forecastStart
);
assert.ok(forecastStart >= 0 && fieldStart > forecastStart);
const forecastArea = space.slice(forecastStart, fieldStart);
assert.doesNotMatch(
    forecastArea,
    /Process\s*\{|Timer\s*\{|curl|Qt\.openUrlExternally|WebEngine/
);

console.log("Weather SPACE NOAA predicted planetary K bins: PASS");
