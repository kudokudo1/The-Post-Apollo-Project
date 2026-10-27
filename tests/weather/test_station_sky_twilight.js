#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("widgets/weather/StationSkyTwilightPolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const ctx = {Date, Number, String, Array, Object, Math, isFinite};
vm.runInNewContext(source, ctx, {filename:"StationSkyTwilightPolicy.js"});

for (const fn of [
    "parseDate", "eventUtcMinutes", "solarNoonUtcMinutes",
    "clockMinute", "calibratedClockOffset", "summary"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.deepEqual(
    JSON.parse(JSON.stringify(ctx.parseDate("2026-10-27"))),
    {year:2026, month:10, day:27}
);
assert.equal(ctx.parseDate("2026-02-30"), null);
assert.equal(ctx.parseDate(""), null);
assert.equal(ctx.clockMinute("07:29 AM"), 449);
assert.equal(ctx.clockMinute("12:00 AM"), 0);
assert.equal(ctx.clockMinute("12:00 PM"), 720);
assert.equal(ctx.clockMinute("23:45"), 1425);
assert.equal(ctx.clockMinute("25:00"), -1);

// Longitude is used only to choose the plausible civil-clock offset when the
// provider sunrise and calculated UTC sunrise straddle different dates.
assert.ok(Math.abs(ctx.calibratedClockOffset(449, 689.868, -77) + 240.868) < 0.01);
assert.equal(ctx.calibratedClockOffset(360, 1020, 174), 780);
assert.equal(ctx.calibratedClockOffset(360, 1260, 139), 540);

// Washington-area regression fixture. The provider sunrise anchors the local
// clock; twilight spacing comes from calculated solar zenith crossings.
const dc = ctx.summary("2026-10-27", 38.9, -77.0, "07:29 AM");
assert.equal(dc.available, true);
assert.equal(dc.sunriseAnchor, "7:29 AM");
assert.equal(dc.astronomicalDawn, "5:59 AM");
assert.equal(dc.nauticalDawn, "6:30 AM");
assert.equal(dc.civilDawn, "7:02 AM");
assert.equal(dc.solarNoon, "12:51 PM");
assert.equal(dc.civilDusk, "6:40 PM");
assert.equal(dc.nauticalDusk, "7:11 PM");
assert.equal(dc.astronomicalDusk, "7:42 PM");

const ordered = [
    dc.astronomicalDawn, dc.nauticalDawn, dc.civilDawn,
    dc.sunriseAnchor, dc.solarNoon,
    dc.civilDusk, dc.nauticalDusk, dc.astronomicalDusk
].map(ctx.clockMinute);
for (let i = 1; i < ordered.length; i++)
    assert.ok(ordered[i] > ordered[i - 1], "solar windows must be chronological");

// No valid provider sunrise means there is no honest way to convert the
// UTC solar calculation into the provider location's civil clock.
assert.equal(ctx.summary("2026-10-27", 38.9, -77, "--").available, false);
assert.equal(ctx.summary("2026-10-27", "", -77, "07:29 AM").available, false);
assert.equal(ctx.summary("2026-10-27", 38.9, "", "07:29 AM").available, false);
assert.equal(ctx.summary("bad-date", 38.9, -77, "07:29 AM").available, false);

// Polar day/night can lack a sunrise crossing. Do not invent twilight clocks.
assert.equal(ctx.summary("2026-06-21", 89, 0, "12:00 AM").available, false);

const policySource = read("widgets/weather/StationSkyTwilightPolicy.js");
for (const zenith of ["90.833", "96", "102", "108"])
    assert.ok(policySource.includes(zenith), "missing solar zenith " + zenith);
assert.doesNotMatch(
    policySource,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

const sky = read("widgets/weather/StationSky.qml");
assert.match(sky, /StationSkyTwilightPolicy\.js" as TwilightPolicy/);
assert.match(sky, /readonly property var twilightSummary:/);
assert.match(
    sky,
    /TwilightPolicy\.summary\([\s\S]*?astronomySummary\.date[\s\S]*?weatherService\.latitude[\s\S]*?weatherService\.longitude[\s\S]*?astronomySummary\.sunrise/
);
assert.match(sky, /title: "TWILIGHT \/\/ SOLAR WINDOWS"/);
for (const token of [
    "astronomicalDawn", "nauticalDawn", "civilDawn", "solarNoon",
    "civilDusk", "nauticalDusk", "astronomicalDusk"
])
    assert.ok(sky.includes("sky.twilightSummary." + token), token);
assert.match(sky, /CLOCK CALIBRATED TO PROVIDER SUNRISE/);
assert.match(sky, /NOT OBSERVED/);
assert.match(sky, /TWILIGHT WINDOWS UNAVAILABLE/);
assert.doesNotMatch(sky, /GOLDEN HOUR|BLUE HOUR/);

const twilightStart = sky.indexOf('title: "TWILIGHT // SOLAR WINDOWS"');
const forecastStart = sky.indexOf('title: "FORECAST // NEXT HOURS"', twilightStart);
assert.ok(twilightStart > 0 && forecastStart > twilightStart);
const twilightArea = sky.slice(twilightStart, forecastStart);
assert.doesNotMatch(
    twilightArea,
    /Process\s*\{|Timer\s*\{|Qt\.openUrlExternally/
);

console.log("SKY calibrated civil/nautical/astronomical twilight contracts: PASS");
