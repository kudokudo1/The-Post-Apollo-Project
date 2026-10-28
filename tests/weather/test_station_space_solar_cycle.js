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
    read("services/weather/SolarCyclePolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "monthKeyFromMs", "validMonth", "normalizeRow", "parseRows",
    "selectModelRow", "peakRow", "emptySummary", "summarize",
    "numberText", "rangeText"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.equal(
    ctx.monthKeyFromMs(Date.UTC(2026, 9, 28, 12, 0, 0)),
    "2026-10"
);
assert.equal(ctx.monthKeyFromMs(0), "");
assert.equal(ctx.validMonth("2026-10"), "2026-10");
assert.equal(ctx.validMonth("2026-13"), "");

const rows = [
    {
        "time-tag":"2026-11",
        "predicted_ssn":148.2,
        "low_ssn":120.0,
        "high_ssn":176.0,
        "predicted_f10.7":166.0,
        "low_f10.7":150.0,
        "high_f10.7":182.0
    },
    {
        "time-tag":"2026-09",
        "predicted_ssn":145.0,
        "low_ssn":118.0,
        "high_ssn":173.0,
        "predicted_f10.7":162.0,
        "low_f10.7":147.0,
        "high_f10.7":178.0
    },
    {
        "time-tag":"2026-10",
        "predicted_ssn":151.5,
        "low_ssn":123.0,
        "high_ssn":180.0,
        "predicted_f10.7":169.4,
        "low_f10.7":153.0,
        "high_f10.7":185.0
    },
    {
        "time-tag":"2027-02",
        "predicted_ssn":162.0,
        "low_ssn":130.0,
        "high_ssn":190.0,
        "predicted_f10.7":175.0,
        "low_f10.7":158.0,
        "high_f10.7":192.0
    },
    {
        "time-tag":"2027-03",
        "predicted_ssn":158.0,
        "low_ssn":128.0,
        "high_ssn":187.0,
        "predicted_f10.7":172.0,
        "low_f10.7":156.0,
        "high_f10.7":189.0
    }
];

let parsed = Array.from(ctx.parseRows(rows));
assert.deepEqual(
    parsed.map(x => x.month),
    ["2026-09", "2026-10", "2026-11", "2027-02", "2027-03"]
);

let summary = ctx.summarize(
    rows,
    Date.UTC(2026, 9, 28, 12, 0, 0)
);
assert.equal(summary.available, true);
assert.equal(summary.targetMonth, "2026-10");
assert.equal(summary.modelMonth, "2026-10");
assert.equal(summary.exactMonth, true);
assert.equal(summary.predictedSsn, 151.5);
assert.equal(summary.lowSsn, 123.0);
assert.equal(summary.highSsn, 180.0);
assert.equal(summary.ssnRangeValid, true);
assert.equal(summary.predictedFlux, 169.4);
assert.equal(summary.lowFlux, 153.0);
assert.equal(summary.highFlux, 185.0);
assert.equal(summary.fluxRangeValid, true);
assert.equal(summary.nextMonth, "2026-11");
assert.equal(summary.nextPredictedSsn, 148.2);
assert.equal(summary.peakMonth, "2027-02");
assert.equal(summary.peakPredictedSsn, 162.0);
assert.equal(summary.rowCount, 5);

// If the file does not contain the current month, retain the nearest earlier
// model month and label it non-current rather than relabeling it as today.
summary = ctx.summarize(
    rows,
    Date.UTC(2026, 11, 1, 0, 0, 0)
);
assert.equal(summary.targetMonth, "2026-12");
assert.equal(summary.modelMonth, "2026-11");
assert.equal(summary.exactMonth, false);

// Before the first available model row, use the first row but keep exact=false.
summary = ctx.summarize(
    rows,
    Date.UTC(2025, 0, 1, 0, 0, 0)
);
assert.equal(summary.modelMonth, "2026-09");
assert.equal(summary.exactMonth, false);

const invalidRange = ctx.normalizeRow({
    "time-tag":"2026-10",
    "predicted_ssn":151.5,
    "low_ssn":180,
    "high_ssn":123,
    "predicted_f10.7":169.4,
    "low_f10.7":190,
    "high_f10.7":150
});
assert.equal(invalidRange.ssnRangeValid, false);
assert.equal(invalidRange.fluxRangeValid, false);
assert.equal(ctx.rangeText(180, 123, 1), "RANGE INVALID");
assert.equal(ctx.rangeText(123, 180, 1), "123.0–180.0");
assert.equal(ctx.numberText(151.54, 1), "151.5");
assert.equal(ctx.numberText(null, 1), "--");

assert.equal(ctx.normalizeRow({"time-tag":"2026-10"}), null);
assert.throws(() => ctx.parseRows({}));
assert.throws(() => ctx.parseRows([]));

const service = read("services/weather/SolarCycleService.qml");
assert.match(
    service,
    /^import QtQuick\s*\nimport Quickshell\s*\nimport Quickshell\.Io/m
);
assert.match(service, /Scope\s*\{/);
assert.match(
    service,
    /services\.swpc\.noaa\.gov\/json\/solar-cycle\/predicted-solar-cycle\.json/
);
assert.match(service, /SolarCyclePolicy\.summarize\(/);
assert.match(service, /property string loadedMonth: ""/);
assert.match(service, /if \(!force && ready && loadedMonth === month\)/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 0);
assert.doesNotMatch(
    service,
    /sunspots\.json|observed-solar-cycle-indices|swpc_observed_ssn/
);
assert.match(service, /--proto", "=https"/);
assert.match(service, /Post-Apollo-WeatherStation\/0\.6/);

const space = read("widgets/weather/StationSpace.qml");
assert.match(
    space,
    /SolarCyclePolicy\.js" as SolarCyclePolicy/
);
assert.match(space, /WeatherServices\.SolarCycleService\s*\{/);
assert.match(space, /active: space\.visible/);
assert.match(
    space,
    /title: "SOLAR CYCLE \/\/ NOAA MONTHLY PREDICTION"/
);
assert.match(space, /MODEL SSN \/\/ /);
assert.match(space, /SSN RANGE/);
assert.match(space, /MODEL F10\.7/);
assert.match(space, /CURVE PEAK/);
assert.match(space, /LIVE F10\.7 \/\/ /);
assert.match(space, /NEXT MODEL \/\/ /);
assert.match(space, /NO EXACT MODEL ROW FOR CURRENT UTC MONTH/);
assert.match(space, /RANGE NOT REPAIRED/);
assert.match(
    space,
    /MONTHLY PREDICTION CURVE \/\/ LIVE F10\.7 ABOVE IS A SEPARATE OBSERVATION WITH A DIFFERENT CADENCE \/\/ NOT A MODEL-ERROR CALCULATION/
);
assert.match(space, /onClicked: solarCycleService\.refresh\(true\)/);

const cycleStart = space.indexOf(
    'title: "SOLAR CYCLE // NOAA MONTHLY PREDICTION"'
);
const kpStart = space.indexOf(
    'title: "GEOMAGNETIC // KP 72-HOUR HISTORY"',
    cycleStart
);
assert.ok(cycleStart >= 0 && kpStart > cycleStart);
const cycleArea = space.slice(cycleStart, kpStart);
assert.doesNotMatch(
    cycleArea,
    /Process\s*\{|Timer\s*\{|curl|Qt\.openUrlExternally|WebEngine/
);

console.log("Weather SPACE NOAA monthly solar-cycle prediction context: PASS");
