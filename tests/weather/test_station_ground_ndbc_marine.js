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
    read("services/weather/NdbcMarinePolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "finite", "distanceKm", "parseHeader", "rowObject",
    "observationMillis", "parseLatest", "nearest", "requestKey",
    "celsiusToF", "metersToFeet", "metersPerSecondToMph",
    "numericLabel"
])
    assert.equal(typeof ctx[fn], "function", fn);

const fixture = [
    "#STN LAT LON YYYY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES PTDY ATMP WTMP DEWP VIS TIDE",
    "#text deg deg yr mo dy hr mn degT m/s m/s m sec sec degT hPa hPa degC degC degC nmi ft",
    "44086 36.001 -75.421 2026 10 31 05 00 MM MM MM 0.9 8 5.8 111 MM MM 19.2 18.9 MM MM MM",
    "TEST1 38.900 -77.200 2026 10 31 05 10 270 8.0 11.0 MM MM MM MM 1008.5 -1.2 14.5 MM 8.0 7.5 1.23",
    "TEST2 39.500 -76.500 2026 10 31 05 20 180 4.5 6.0 1.2 7 5.5 160 1012.1 0.4 16.0 15.0 10.2 8.0 MM"
].join("\n");

const rows = Array.from(ctx.parseLatest(fixture));
assert.equal(rows.length, 3);
assert.equal(rows[0].stationId, "44086");
assert.equal(rows[0].waveHeightM, 0.9);
assert.equal(rows[0].dominantPeriodS, 8);
assert.equal(rows[0].meanWaveDirection, 111);
assert.equal(rows[0].windSpeedMs, null);
assert.equal(rows[1].stationId, "TEST1");
assert.equal(rows[1].windDirection, 270);
assert.equal(rows[1].windSpeedMs, 8);
assert.equal(rows[1].gustMs, 11);
assert.equal(rows[1].pressureHpa, 1008.5);
assert.equal(rows[1].tideFt, 1.23);
assert.equal(rows[1].sampleUtc, "2026-10-31 05:10Z");

const nearest = ctx.nearest(rows, 38.9, -77.0);
assert.equal(nearest.stationId, "TEST1");
assert.ok(nearest.distanceKm > 0 && nearest.distanceKm < 25);

assert.equal(ctx.requestKey(38.9, -77), "38.900|-77.000");
assert.equal(ctx.requestKey("", -77), "");
assert.equal(ctx.nearest(rows, "", -77), null);
assert.throws(() => ctx.parseLatest("no header"));
assert.throws(() => ctx.parseLatest("#STN LAT LON YYYY MM DD hh mm\n"));

assert.ok(Math.abs(ctx.celsiusToF(0) - 32) < 0.000001);
assert.ok(Math.abs(ctx.celsiusToF(20) - 68) < 0.000001);
assert.ok(Math.abs(ctx.metersToFeet(1) - 3.28084) < 0.000001);
assert.ok(Math.abs(ctx.metersPerSecondToMph(1) - 2.236936) < 0.000001);
assert.equal(ctx.numericLabel(null, 1, " m"), "--");
assert.equal(ctx.numericLabel(1.234, 1, " m"), "1.2 m");

// Header-driven parsing must tolerate an inserted provider column.
const extended = [
    "#STN LAT LON YYYY MM DD hh mm EXTRA WDIR WSPD WVHT ATMP",
    "#x x x x x x x x x x x x x",
    "X001 40 -70 2026 10 31 06 00 ABC 90 5.5 2.2 12.3"
].join("\n");
const extendedRows = Array.from(ctx.parseLatest(extended));
assert.equal(extendedRows.length, 1);
assert.equal(extendedRows[0].windDirection, 90);
assert.equal(extendedRows[0].windSpeedMs, 5.5);
assert.equal(extendedRows[0].waveHeightM, 2.2);
assert.equal(extendedRows[0].airTempC, 12.3);

const policy = read("services/weather/NdbcMarinePolicy.js");
assert.doesNotMatch(
    policy,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

const service = read("services/weather/NdbcMarineService.qml");
assert.match(
    service,
    /^import QtQuick\s*\nimport Quickshell\s*\nimport Quickshell\.Io/m
);
assert.match(
    service,
    /https:\/\/www\.ndbc\.noaa\.gov\/data\/latest_obs\/latest_obs\.txt/
);
assert.match(service, /MarinePolicy\.parseLatest/);
assert.match(service, /MarinePolicy\.nearest/);
assert.match(service, /property string inflightKey: ""/);
assert.match(service, /currentKey !== inflightKey/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 2);
assert.match(service, /interval: 600000/);
assert.match(service, /interval: 250/);
assert.match(service, /running: marine\.active && marine\.configured/);
assert.match(service, /--proto", "=https"/);

const ground = read("widgets/weather/StationGround.qml");
assert.match(ground, /NdbcMarinePolicy\.js" as MarinePolicy/);
assert.match(ground, /WeatherServices\.NdbcMarineService\s*\{/);
assert.match(ground, /title: "MARINE \/\/ NOAA NDBC"/);
assert.match(ground, /NDBC LATEST OBSERVATIONS \/\/ ALL REPORTING STATIONS/);
assert.match(ground, /WAVES \/\/ SIGNIFICANT/);
assert.match(ground, /MEAN WAVE DIR/);
assert.match(ground, /REPORTING STATIONS \/\/ /);
assert.match(ground, /SOURCE METRIC \/\/ CONVERSIONS SHOWN FOR DISPLAY/);
assert.match(ground, /DISTANCE IS GEOGRAPHIC, NOT COASTAL RELEVANCE/);
assert.match(ground, /MISSING SENSOR FIELDS STAY UNAVAILABLE/);

const marineStart = ground.indexOf('title: "MARINE // NOAA NDBC"');
const airStart = ground.indexOf('title: "AIR // PARTICULATES"', marineStart);
assert.ok(marineStart >= 0 && airStart > marineStart);
const marineArea = ground.slice(marineStart, airStart);
assert.doesNotMatch(
    marineArea,
    /Process\s*\{|Timer\s*\{|curl|Qt\.openUrlExternally/
);

console.log("Weather GROUND nearest NOAA NDBC marine observations: PASS");
