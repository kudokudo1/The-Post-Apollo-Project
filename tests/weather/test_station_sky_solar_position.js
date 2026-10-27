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
    "observationEpoch", "providerObservationMinute",
    "compassLabel", "solarPosition"
])
    assert.equal(typeof ctx[fn], "function", fn);

const anchor = 1000000;
assert.equal(
    ctx.providerObservationMinute(
        anchor, "2026-10-27 12:30 PM", anchor
    ),
    12 * 60 + 30
);
assert.equal(
    ctx.providerObservationMinute(
        anchor + 21 * 60000,
        "2026-10-27 12:30 PM",
        anchor
    ),
    12 * 60 + 51
);
assert.equal(
    ctx.providerObservationMinute(
        anchor + 61 * 60000,
        "2026-10-27 12:30 PM",
        anchor
    ),
    -1,
    "provider observation clock older than one hour must not drive solar position"
);
assert.equal(
    ctx.providerObservationMinute(
        anchor, "2026-02-30 12:30 PM", anchor
    ),
    -1
);
assert.equal(
    ctx.providerObservationMinute(anchor, "", anchor),
    -1
);

const twilight = ctx.summary(
    "2026-10-27", 38.9, -77.0, "07:29 AM"
);
assert.equal(twilight.available, true);
assert.ok(Number.isFinite(twilight.calibrationOffsetMinutes));

// Near calculated solar noon for the Washington fixture the Sun is due south
// and about 38 degrees above the horizon.
let position = ctx.solarPosition(
    "2026-10-27",
    12 * 60 + 51,
    38.9,
    -77.0,
    twilight.calibrationOffsetMinutes
);
assert.equal(position.available, true);
assert.ok(Math.abs(position.altitudeDegrees - 38.15) < 0.25);
assert.ok(Math.abs(position.azimuthDegrees - 180.02) < 0.5);
assert.equal(position.azimuthLabel, "S");
assert.equal(position.aboveHorizon, true);

// At the provider sunrise anchor, geometric altitude should agree with the
// 0.833-degree apparent-horizon convention used to calibrate the clock.
position = ctx.solarPosition(
    "2026-10-27",
    7 * 60 + 29,
    38.9,
    -77.0,
    twilight.calibrationOffsetMinutes
);
assert.ok(Math.abs(position.altitudeDegrees + 0.833) < 0.08);
assert.ok(Math.abs(position.azimuthDegrees - 105.94) < 0.5);
assert.equal(position.azimuthLabel, "ESE");
assert.equal(position.aboveHorizon, false);

// Nighttime position remains a geometric result, not an invented daylight
// state. The Sun is well below the western horizon.
position = ctx.solarPosition(
    "2026-10-27",
    20 * 60,
    38.9,
    -77.0,
    twilight.calibrationOffsetMinutes
);
assert.ok(position.altitudeDegrees < -18);
assert.ok(Math.abs(position.azimuthDegrees - 270.37) < 0.8);
assert.equal(position.azimuthLabel, "W");
assert.equal(position.aboveHorizon, false);

assert.equal(ctx.compassLabel(0), "N");
assert.equal(ctx.compassLabel(90), "E");
assert.equal(ctx.compassLabel(180), "S");
assert.equal(ctx.compassLabel(270), "W");
assert.equal(ctx.compassLabel(359), "N");

for (const bad of [
    ctx.solarPosition("", 720, 38.9, -77, -240),
    ctx.solarPosition("2026-10-27", -1, 38.9, -77, -240),
    ctx.solarPosition("2026-10-27", 720, "", -77, -240),
    ctx.solarPosition("2026-10-27", 720, 38.9, "", -240),
    ctx.solarPosition("2026-10-27", 720, 38.9, -77, null)
])
    assert.equal(bad.available, false);

const policySource = read("widgets/weather/StationSkyTwilightPolicy.js");
assert.doesNotMatch(
    policySource,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

const sky = read("widgets/weather/StationSky.qml");
assert.match(sky, /readonly property int providerLocalMinute:/);
assert.match(sky, /TwilightPolicy\.providerObservationMinute\(/);
assert.match(sky, /readonly property var currentSolarPosition:/);
assert.match(sky, /TwilightPolicy\.solarPosition\(/);
assert.match(sky, /text: "SUN NOW"/);
assert.match(sky, /text: "ALTITUDE"/);
assert.match(sky, /text: "AZIMUTH"/);
assert.match(sky, /ABOVE HORIZON/);
assert.match(sky, /BELOW HORIZON/);
assert.match(sky, /GEOMETRIC SUN POSITION/);
assert.match(sky, /AZIMUTH CLOCKWISE FROM NORTH/);
assert.match(sky, /PROVIDER OBSERVATION CLOCK IS MISSING OR STALE/);

const positionStart = sky.indexOf('text: "SUN NOW"');
const forecastStart = sky.indexOf('title: "FORECAST // NEXT HOURS"', positionStart);
assert.ok(positionStart > 0 && forecastStart > positionStart);
const positionArea = sky.slice(positionStart, forecastStart);
assert.doesNotMatch(
    positionArea,
    /Process\s*\{|Timer\s*\{|Qt\.openUrlExternally/
);

console.log("SKY provider-clock solar altitude and azimuth contracts: PASS");
