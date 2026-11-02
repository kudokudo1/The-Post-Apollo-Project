#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/WeatherRuntimePolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const runtime = {
    Date, Math, Number, String, Array, Object, JSON, RegExp, isFinite
};
vm.runInNewContext(source, runtime, {
    filename: "services/weather/WeatherRuntimePolicy.js"
});

const minute = 60000;
const hour = 60 * minute;

function expectSpec(id, expected) {
    const spec = runtime.sourceSpec(id);
    assert.ok(spec, id + " runtime spec");
    for (const [key, value] of Object.entries(expected))
        assert.equal(spec[key], value, id + " " + key);
}

expectSpec("nws-alerts", {
    mode: "FAST_POLL",
    cadenceMs: 5 * minute,
    freshMs: 10 * minute,
    staleMs: 30 * minute,
    expireMs: 6 * hour
});

expectSpec("seismic", {
    mode: "FAST_POLL",
    cadenceMs: 5 * minute,
    freshMs: 10 * minute,
    staleMs: 30 * minute,
    expireMs: 24 * hour
});

expectSpec("marine", {
    mode: "SLOW_POLL",
    cadenceMs: 30 * minute,
    freshMs: 45 * minute,
    staleMs: 2 * hour,
    expireMs: 6 * hour
});

expectSpec("gdacs", {
    mode: "NORMAL_POLL",
    cadenceMs: 6 * minute,
    freshMs: 15 * minute,
    staleMs: 1 * hour,
    expireMs: 24 * hour
});

// M9 is deliberately selective. These sources are explicit guardrails against
// a blanket faster-refresh pass.
for (const [id, cadence] of [
    ["weather-current", 15 * minute],
    ["weather-forecast", 15 * minute],
    ["air-quality", 15 * minute],
    ["space-core", 5 * minute],
    ["river", 15 * minute],
    ["coastal", 15 * minute],
    ["lightning", 15 * minute],
    ["swpc-alerts", 10 * minute],
    ["aurora", 15 * minute],
    ["kp-forecast", 15 * minute],
    ["discovery", 15 * minute],
]) {
    assert.equal(runtime.sourceSpec(id).cadenceMs, cadence, id + " unchanged");
}

const nws = read("services/notifications/NwsOfficialAlertNotificationProducer.qml");
assert.match(nws, /interval:\s*300000/);
assert.match(nws, /conservative five-minute cadence/);
assert.equal((nws.match(/\bTimer\s*\{/g) || []).length, 1);

const seismic = read("services/weather/SeismicService.qml");
assert.match(seismic, /interval:\s*300000/);
assert.match(seismic, /GeoJSON summary feeds update every minute/);
assert.equal((seismic.match(/\bTimer\s*\{/g) || []).length, 1);

const marine = read("services/weather/NdbcMarineService.qml");
assert.match(marine, /interval:\s*1800000/);
assert.match(marine, /most stations report hourly/);
assert.equal((marine.match(/\bTimer\s*\{/g) || []).length, 2);

const gdacs = read("services/weather/GdacsService.qml");
assert.match(gdacs, /readonly property int cacheMs:\s*360000/);
assert.match(gdacs, /updated every six minutes/);
assert.equal((gdacs.match(/\bTimer\s*\{/g) || []).length, 1);

// Location/view activation still performs immediate refreshes. M9 changes
// steady-state cadence only.
assert.match(marine, /onCurrentKeyChanged: reconcileLocationKey\(\)/);
assert.match(marine, /locationDebounce\.restart\(\)/);
assert.match(seismic, /onActiveChanged:[\s\S]*?refresh\(\)/);
assert.match(gdacs, /onActiveChanged:[\s\S]*?refresh\(false\)/);
assert.match(nws, /Component\.onCompleted:[\s\S]*?producer\.refresh\(\)/);

// Runtime labels must expose the new numbers rather than a generic class.
assert.equal(
    runtime.cadenceLabel(runtime.displayRow(
        "nws-alerts", {active:true, ready:true, receivedAt:Date.now()}, Date.now()
    )),
    "5m"
);
assert.equal(
    runtime.cadenceLabel(runtime.displayRow(
        "marine", {active:true, ready:true, receivedAt:Date.now()}, Date.now()
    )),
    "30m"
);
assert.equal(
    runtime.cadenceLabel(runtime.displayRow(
        "gdacs", {active:true, ready:true, receivedAt:Date.now()}, Date.now()
    )),
    "6m"
);

console.log("Weather M9 source-specific cadence tuning: PASS");
