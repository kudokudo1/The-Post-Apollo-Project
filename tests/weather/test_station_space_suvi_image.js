#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {Date, Number, String, Math, isFinite};
vm.runInNewContext(
    read("widgets/weather/StationSolarImagePolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "cleanMode", "modeInfo", "refreshToken",
    "imageUrl", "safeImageUrl", "localAgeMinutes"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.equal(ctx.cleanMode("195"), "195");
assert.equal(ctx.cleanMode("map"), "map");
assert.equal(ctx.cleanMode("anything"), "195");

let info = ctx.modeInfo("195");
assert.equal(info.id, "195");
assert.equal(info.label, "195 Å");
assert.equal(info.path, "195/latest.png");
assert.match(info.detail, /WARM CORONAL PLASMA/);
assert.match(info.detail, /ACTIVE REGIONS/);
assert.match(info.detail, /CORONAL HOLES/);

info = ctx.modeInfo("map");
assert.equal(info.id, "map");
assert.equal(info.label, "THERMAL MAP");
assert.equal(info.path, "map/latest.png");
assert.match(info.detail, /TEMPERATURE-MAP PRODUCT/);

const t0 = 1793095200000;
assert.equal(ctx.refreshToken(t0), Math.floor(t0 / 300000));
assert.equal(ctx.refreshToken(t0 + 299999), Math.floor((t0 + 299999) / 300000));

const url195 = ctx.imageUrl("195", t0);
const urlMap = ctx.imageUrl("map", t0);
assert.match(
    url195,
    /^https:\/\/services\.swpc\.noaa\.gov\/images\/animations\/suvi\/primary\/195\/latest\.png\?v=\d+$/
);
assert.match(
    urlMap,
    /^https:\/\/services\.swpc\.noaa\.gov\/images\/animations\/suvi\/primary\/map\/latest\.png\?v=\d+$/
);
assert.equal(ctx.safeImageUrl(url195), true);
assert.equal(ctx.safeImageUrl(urlMap), true);
assert.equal(ctx.safeImageUrl("https://example.com/latest.png?v=1"), false);
assert.equal(
    ctx.safeImageUrl(
        "https://services.swpc.noaa.gov/images/animations/suvi/primary/304/latest.png?v=1"
    ),
    false
);
assert.equal(ctx.localAgeMinutes(1000000, 1120000), 2);
assert.equal(ctx.localAgeMinutes(0, 1120000), -1);
assert.equal(ctx.localAgeMinutes(1200000, 1120000), -1);

const policy = read("widgets/weather/StationSolarImagePolicy.js");
assert.doesNotMatch(
    policy,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);
assert.doesNotMatch(policy, /products\/animations|\.json|secondary\//);

const space = read("widgets/weather/StationSpace.qml");
assert.match(space, /StationSolarImagePolicy\.js" as SolarImagePolicy/);
assert.match(space, /property string solarImageMode: "195"/);
assert.match(space, /property string solarImageUrl: ""/);
assert.match(space, /function refreshSolarImage\(\)/);
assert.match(space, /SolarImagePolicy\.imageUrl\(/);
assert.match(space, /function selectSolarImageMode\(mode\)/);
assert.match(space, /id: solarImageRefreshClock/);
assert.match(space, /interval: 300000/);
assert.match(space, /running: space\.visible/);
assert.match(space, /Component\.onCompleted: refreshSolarImage\(\)/);

assert.match(space, /title: "SOLAR IMAGER \/\/ NOAA SWPC SUVI"/);
assert.match(space, /id: solarImage/);
assert.match(space, /source: space\.solarImageUrl/);
assert.match(space, /fillMode: Image\.PreserveAspectFit/);
assert.match(space, /asynchronous: true/);
assert.match(space, /cache: false/);
assert.equal((space.match(/id: solarImage\b/g) || []).length, 1,
             "only one SUVI image slot should exist");

assert.match(space, /labelText: "195 Å"/);
assert.match(space, /labelText: "THERMAL MAP"/);
assert.match(space, /bordered: false/);
assert.match(space, /label: "REFRESH"/);
assert.match(space, /NOAA SWPC \/\/ SUVI PRIMARY/);
assert.match(space, /LATEST ENDPOINT \/\/ ONE SELECTED IMAGE/);
assert.match(space, /LOCAL RECEIVE \/\/ /);
assert.match(space, /LOCAL RECEIVE TIME IS NOT SPACECRAFT OBSERVATION TIME/);
assert.match(space, /NO FRAME ARCHIVE/);
assert.match(space, /DISPLAY IMAGE, NOT A LOCAL TEMPERATURE READING/);
assert.match(space, /WARM CORONAL PLASMA FOR GLOBAL STRUCTURE, ACTIVE REGIONS \+ CORONAL HOLES/);

const solarStart = space.indexOf(
    'title: "SOLAR IMAGER // NOAA SWPC SUVI"'
);
const auroraStart = space.indexOf(
    'title: "AURORA // 30-90 MIN FORECAST"',
    solarStart
);
assert.ok(solarStart >= 0 && auroraStart > solarStart);
const solarArea = space.slice(solarStart, auroraStart);
assert.doesNotMatch(
    solarArea,
    /Process\s*\{|curl|Qt\.openUrlExternally|WebEngine/
);
assert.equal((solarArea.match(/\bImage\s*\{/g) || []).length, 1);

console.log("Weather SPACE NOAA SUVI single-image source and refresh contracts: PASS");
