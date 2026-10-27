#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
function load(file) {
    const source = fs.readFileSync(path.join(root, file), "utf8")
        .replace(/^\.pragma library\s*/m, "");
    const context = {};
    vm.runInNewContext(source, context);
    return context;
}

const health = load("widgets/weather/StationSourceHealthPolicy.js");
assert.equal(typeof health.sourceRow, "function");
assert.equal(typeof health.buildCoreSources, "function");
assert.equal(typeof health.ageMinutes, "function");

const now = 1_000_000;
function row(overrides = {}) {
    return health.sourceRow({
        id: "weather",
        title: "WEATHER",
        provider: "WTTR.IN",
        ready: true,
        loading: false,
        error: "",
        lastSuccessMs: now - 2 * 60_000,
        sampleAgeMinutes: -1,
        staleAfterMinutes: 20,
        ...overrides,
    }, now);
}

let current = row();
assert.equal(current.state, "LIVE");
assert.equal(current.accent, "magenta");
assert.equal(current.footer, "LAST SUCCESS 2m");

current = row({loading:true});
assert.equal(current.state, "UPDATING");
assert.equal(current.accent, "cyan");

current = row({ready:false, loading:true, lastSuccessMs:-1});
assert.equal(current.state, "READING");
assert.equal(current.footer, "LAST SUCCESS --");

current = row({ready:false, error:"request failed", lastSuccessMs:-1});
assert.equal(current.state, "OFFLINE");
assert.equal(current.accent, "red");
assert.match(current.detail, /REQUEST FAILED/);

current = row({error:"request failed"});
assert.equal(current.state, "DEGRADED");
assert.equal(current.accent, "yellow");
assert.equal(current.footer, "LAST SUCCESS 2m");

current = row({loading:true, error:"request failed"});
assert.equal(current.state, "RETRYING");
assert.equal(current.accent, "orange");

current = row({
    lastSuccessMs: now - 60_000,
    sampleAgeMinutes: 46,
    staleAfterMinutes: 45,
});
assert.equal(current.state, "STALE");
assert.equal(current.detail, "SOURCE SAMPLE 46m OLD");
assert.equal(current.footer, "LAST SUCCESS 1m // SAMPLE 46m");

current = row({
    lastSuccessMs: now - 21 * 60_000,
    sampleAgeMinutes: -1,
    staleAfterMinutes: 20,
});
assert.equal(current.state, "STALE");

assert.equal(health.ageMinutes(now, now), 0);
assert.equal(health.compactAge(0), "<1m");
assert.equal(health.compactAge(-1), "--");

const core = health.buildCoreSources({
    nowMs: now,
    weather: {id:"weather", title:"WEATHER", ready:true, lastSuccessMs:now},
    aqi: {id:"aqi", title:"AIR QUALITY", ready:true, lastSuccessMs:now},
    kp: {id:"kp", title:"KP INDEX", ready:true, lastSuccessMs:now},
    solarWind: {id:"solar-wind", title:"SOLAR WIND", ready:true, lastSuccessMs:now},
    magneticField: {id:"imf", title:"IMF", ready:true, lastSuccessMs:now},
    solarFlux: {id:"solar-flux", title:"F10.7 FLUX", ready:true, lastSuccessMs:now},
});
assert.equal(core.length, 6);
assert.deepEqual(Array.from(core, item => item.id), [
    "weather", "aqi", "kp", "solar-wind", "imf", "solar-flux"
]);

const policySource = fs.readFileSync(
    path.join(root, "widgets/weather/StationSourceHealthPolicy.js"),
    "utf8"
);
assert.doesNotMatch(policySource, /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest/);

const space = fs.readFileSync(
    path.join(root, "services/weather/SpaceService.qml"),
    "utf8"
);
for (const token of [
    "kpLoading", "solarWindLoading", "magneticFieldLoading", "solarFluxLoading",
    "kpLastUpdated", "solarWindLastUpdated",
    "magneticFieldLastUpdated", "solarFluxLastUpdated",
    "kpErrorText", "solarWindErrorText",
    "magneticFieldErrorText", "solarFluxErrorText"
])
    assert.match(space, new RegExp("\\b" + token + "\\b"), token);
assert.match(space, /readonly property string errorText:/);
assert.match(space, /kpErrorText = ""/);
assert.match(space, /solarWindErrorText = ""/);
assert.match(space, /magneticFieldErrorText = ""/);
assert.match(space, /solarFluxErrorText = ""/);

const home = fs.readFileSync(
    path.join(root, "widgets/weather/StationHome.qml"),
    "utf8"
);
assert.match(home, /import "StationSourceHealthPolicy\.js" as SourceHealth/);
assert.match(home, /SourceHealth\.buildCoreSources/);
assert.match(home, /title: "CORE SOURCE HEALTH \/\/ LAST SUCCESS \+ FRESHNESS"/);
assert.match(home, /model: home\.sourceHealthRows/);
assert.match(home, /id: homeScroll/);
assert.match(home, /NeonScrollBar\s*\{/);
assert.match(home, /handleStyle: "star"/);
assert.doesNotMatch(
    home.slice(
        home.indexOf("readonly property var sourceHealthRows"),
        home.indexOf("// HOME tracks only session-local deltas")
    ),
    /Process\s*\{|Timer\s*\{/
);

console.log("Weather core source-health policy, per-feed state and HOME rack: PASS");
