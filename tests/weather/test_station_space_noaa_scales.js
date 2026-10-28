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
    read("services/weather/NoaaScalesPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "scaleNumber", "fallbackDescriptor", "normalizeScale",
    "parseCurrent", "emptyCurrent"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.equal(ctx.scaleNumber("0"), 0);
assert.equal(ctx.scaleNumber("5"), 5);
assert.equal(ctx.scaleNumber(3), 3);
assert.equal(ctx.scaleNumber(2.5), -1);
assert.equal(ctx.scaleNumber(6), -1);
assert.equal(ctx.scaleNumber(null), -1);

for (const [level, label] of [
    [0, "NONE"], [1, "MINOR"], [2, "MODERATE"],
    [3, "STRONG"], [4, "SEVERE"], [5, "EXTREME"]
])
    assert.equal(ctx.fallbackDescriptor(level), label);

let normalized = ctx.normalizeScale(
    {Scale:"3", Text:"strong"},
    "G",
    "GEOMAGNETIC STORM"
);
assert.equal(normalized.available, true);
assert.equal(normalized.level, 3);
assert.equal(normalized.code, "G3");
assert.equal(normalized.providerText, "STRONG");
assert.equal(normalized.category, "GEOMAGNETIC STORM");

normalized = ctx.normalizeScale(
    {Scale:"2", Text:null},
    "R",
    "RADIO BLACKOUT"
);
assert.equal(normalized.providerText, "MODERATE");

const fixture = {
    "0": {
        DateStamp:"2026-10-28",
        TimeStamp:"08:28:00",
        R:{Scale:"1", Text:"minor", MinorProb:null, MajorProb:null},
        S:{Scale:"0", Text:"none", Prob:null},
        G:{Scale:"3", Text:"strong"}
    },
    "1": {
        DateStamp:"2026-10-28",
        TimeStamp:"08:28:00",
        R:{Scale:null, Text:null, MinorProb:"5", MajorProb:"1"},
        S:{Scale:null, Text:null, Prob:"1"},
        G:{Scale:"5", Text:"extreme"}
    },
    "-1": {
        DateStamp:"2026-10-27",
        TimeStamp:"08:28:00",
        R:{Scale:"5", Text:"extreme"},
        S:{Scale:"5", Text:"extreme"},
        G:{Scale:"5", Text:"extreme"}
    }
};

const current = ctx.parseCurrent(fixture);
assert.equal(current.available, true);
assert.equal(current.productStamp, "2026-10-28 08:28:00");
assert.equal(current.G.code, "G3");
assert.equal(current.G.providerText, "STRONG");
assert.equal(current.R.code, "R1");
assert.equal(current.R.providerText, "MINOR");
assert.equal(current.S.code, "S0");
assert.equal(current.S.providerText, "NONE");

// Parser owns only documented current slot 0. It must not substitute future
// or previous slots when current is missing.
assert.throws(() => ctx.parseCurrent({"1":fixture["1"]}));
assert.throws(() => ctx.parseCurrent([]));
assert.throws(() => ctx.parseCurrent(null));
assert.throws(() => ctx.parseCurrent({
    "0": {
        DateStamp:"2026-10-28",
        TimeStamp:"08:28:00",
        G:{Scale:null}, R:{Scale:null}, S:{Scale:null}
    }
}));

const empty = ctx.emptyCurrent();
assert.equal(empty.available, false);
assert.equal(empty.G.code, "G--");
assert.equal(empty.R.code, "R--");
assert.equal(empty.S.code, "S--");

const policy = read("services/weather/NoaaScalesPolicy.js");
assert.doesNotMatch(
    policy,
    /Kp|xray|X-ray|flare|proton|solarWind|magneticField/,
    "NOAA scales policy must parse provider scales, not derive them"
);
assert.doesNotMatch(
    policy,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

const service = read("services/weather/NoaaScalesService.qml");
assert.match(
    service,
    /^import QtQuick\s*\nimport Quickshell\s*\nimport Quickshell\.Io/m
);
assert.match(service, /Scope\s*\{/);
assert.match(
    service,
    /services\.swpc\.noaa\.gov\/products\/noaa-scales\.json/
);
assert.match(service, /ScalesPolicy\.parseCurrent/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 1);
assert.match(service, /interval: 300000/);
assert.match(service, /repeat: true/);
assert.match(service, /running: scales\.active/);
assert.match(service, /--proto", "=https"/);
assert.match(service, /Post-Apollo-WeatherStation\/0\.7/);
assert.doesNotMatch(
    service,
    /noaa-planetary-k-index|xray|flares|proton|solar-wind/i
);

const space = read("widgets/weather/StationSpace.qml");
assert.match(space, /WeatherServices\.NoaaScalesService\s*\{/);
assert.match(space, /id: scalesService/);
assert.match(space, /active: space\.visible/);
assert.match(
    space,
    /title: "NOAA SCALES \/\/ CURRENT SNAPSHOT"/
);
assert.match(space, /scalesService\.current\.G/);
assert.match(space, /scalesService\.current\.R/);
assert.match(space, /scalesService\.current\.S/);
assert.match(space, /MODEL SSN \/\/ /);
assert.match(space, /PRODUCT STAMP \/\/ /);
assert.match(space, /LOCAL RECEIVE /);
assert.match(
    space,
    /G \/\/ GEOMAGNETIC STORM  •  R \/\/ RADIO BLACKOUT  •  S \/\/ SOLAR RADIATION STORM/
);
assert.match(space, /NOAA-PUBLISHED SCALE, NOT DERIVED FROM LOCAL KP\/X-RAY VALUES/);
assert.match(space, /NO TIME ZONE INFERRED/);
assert.match(space, /onClicked: scalesService\.refresh\(\)/);

const scaleStart = space.indexOf(
    'title: "NOAA SCALES // CURRENT SNAPSHOT"'
);
const cycleStart = space.indexOf(
    'title: "SOLAR CYCLE // NOAA MONTHLY PREDICTION"',
    scaleStart
);
assert.ok(scaleStart >= 0 && cycleStart > scaleStart);
const scaleArea = space.slice(scaleStart, cycleStart);
assert.doesNotMatch(
    scaleArea,
    /Process\s*\{|Timer\s*\{|curl|Qt\.openUrlExternally|WebEngine/
);

console.log("Weather SPACE official NOAA G/R/S current scales: PASS");
