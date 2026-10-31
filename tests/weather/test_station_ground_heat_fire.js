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
    read("widgets/weather/StationGroundEnvironmentPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of ["heatBand", "heatIndex", "fireWeatherAlerts"])
    assert.equal(typeof ctx[fn], "function", fn);

let heat = ctx.heatIndex(96, 65);
assert.equal(heat.available, true);
assert.equal(heat.method, "ROTHFUSZ");
assert.ok(
    Math.abs(heat.valueF - 121) < 1.5,
    "96F/65% should be about 121F"
);
assert.equal(heat.band.id, "danger");
assert.equal(heat.band.label, "DANGER");

heat = ctx.heatIndex(90, 60);
assert.ok(Math.abs(heat.valueF - 100) < 1.5);
assert.equal(heat.band.id, "extreme-caution");

heat = ctx.heatIndex(75, 50);
assert.equal(heat.available, true);
assert.equal(heat.method, "STEADMAN SIMPLE");
assert.equal(heat.band.id, "below");

heat = ctx.heatIndex(110, 10);
assert.equal(heat.method, "ROTHFUSZ");
assert.ok(isFinite(heat.valueF));

heat = ctx.heatIndex(85, 90);
assert.equal(heat.method, "ROTHFUSZ");
assert.ok(isFinite(heat.valueF));

assert.equal(ctx.heatIndex("", 50).available, false);
assert.equal(ctx.heatIndex(90, -1).available, false);
assert.equal(ctx.heatIndex(90, 101).available, false);

assert.equal(ctx.heatBand(79.9).id, "below");
assert.equal(ctx.heatBand(80).id, "caution");
assert.equal(ctx.heatBand(89.9).id, "caution");
assert.equal(ctx.heatBand(90).id, "extreme-caution");
assert.equal(ctx.heatBand(103).id, "danger");
assert.equal(ctx.heatBand(125).id, "extreme-danger");

const alerts = [
    {
        id:"a",
        event:"Red Flag Warning",
        effective:"2026-10-31T12:00:00Z"
    },
    {
        id:"b",
        event:"Fire Weather Watch",
        effective:"2026-10-31T13:00:00Z"
    },
    {
        id:"c",
        event:"Severe Thunderstorm Warning"
    },
    {
        id:"d",
        event:"Fire Danger Statement"
    },
    {
        id:"e",
        headline:"Fire Weather Special Weather Statement"
    },
    {
        id:"a",
        event:"Red Flag Warning",
        effective:"2026-10-31T12:00:00Z"
    }
];
const fire = Array.from(ctx.fireWeatherAlerts(alerts));
assert.equal(fire.length, 4);
assert.deepEqual(
    fire.map(x => x.id),
    ["a", "b", "d", "e"]
);
assert.equal(ctx.fireWeatherAlerts(null).length, 0);

const policy = read("widgets/weather/StationGroundEnvironmentPolicy.js");
assert.doesNotMatch(
    policy,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);
assert.match(policy, /-42\.379/);
assert.match(policy, /2\.04901523/);
assert.match(policy, /10\.14333127/);
assert.match(
    policy,
    /red flag warning\|fire weather watch\|fire danger statement/
);
assert.doesNotMatch(
    policy,
    /fuel moisture\s*[<>]=?|KBDI\s*[<>]=?|redFlagScore|fireRiskScore/i,
    "do not invent local Red Flag criteria"
);

const ground = read("widgets/weather/StationGround.qml");
assert.match(
    ground,
    /StationGroundEnvironmentPolicy\.js" as EnvironmentPolicy/
);
assert.match(
    ground,
    /EnvironmentPolicy\.heatIndex\([\s\S]*?weatherService\.tempF[\s\S]*?weatherService\.humidity/
);
assert.match(
    ground,
    /EnvironmentPolicy\.fireWeatherAlerts\(officialAlerts\)/
);
assert.match(
    ground,
    /title: "HEAT \+ FIRE WEATHER \/\/ NWS CONTEXT"/
);
assert.match(ground, /NWS HEAT INDEX \/\/ SHADE/);
assert.match(ground, /DIRECT SUN CAN FEEL HOTTER/);
assert.match(ground, /FIRE WEATHER \/\/ OFFICIAL \+ LOCAL OBS/);
assert.match(ground, /NO MATCHING FIRE PRODUCT IN ALERT FEED/);
assert.match(
    ground,
    /LOCAL WEATHER VALUES ARE DESCRIPTIVE ONLY \/\/ RED FLAG CRITERIA VARY BY NWS OFFICE \+ FUEL STATE/
);
assert.match(ground, /fireWeatherAlertRows\.slice\(0, 3\)/);

const heatStart = ground.indexOf(
    'title: "HEAT + FIRE WEATHER // NWS CONTEXT"'
);
const airStart = ground.indexOf(
    'title: "AIR // PARTICULATES"',
    heatStart
);
assert.ok(heatStart >= 0 && airStart > heatStart);
const heatArea = ground.slice(heatStart, airStart);
assert.doesNotMatch(
    heatArea,
    /Process\s*\{|Timer\s*\{|curl|Qt\.openUrlExternally/
);

console.log("Weather GROUND NWS heat-index and fire-weather context: PASS");
