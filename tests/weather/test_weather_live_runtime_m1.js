#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/WeatherRuntimePolicy.js");
const ctx = {
    Date, Math, Number, String, Array, Object, JSON,
    isFinite
};
vm.runInNewContext(source.replace(/^\.pragma library\s*/m, ""), ctx);

for (const fn of [
    "sourceCatalog", "sourceSpec", "timestampMs", "ageMs", "ageMinutes",
    "effectiveFreshMs", "effectiveStaleMs", "effectiveExpireMs", "freshness",
    "runtimeState", "compactAgeMinutes"
])
    assert.equal(typeof ctx[fn], "function", fn);

const catalog = Array.from(ctx.sourceCatalog());
assert.ok(catalog.length >= 28, "runtime inventory should cover current Weather owners");
assert.equal(new Set(catalog.map(row => row.id)).size, catalog.length);

const validModes = new Set([
    "STREAM", "FAST_POLL", "NORMAL_POLL", "SLOW_POLL",
    "KEYED_FETCH", "LOCAL_CALC", "MANUAL"
]);
const validLifetimes = new Set([
    "SESSION_BACKGROUND", "VIEW_SCOPED", "KEYED_VIEW",
    "OPERATOR_REQUEST", "LOCAL"
]);
for (const row of catalog) {
    assert.ok(validModes.has(row.mode), row.id + " mode");
    assert.ok(validLifetimes.has(row.lifetime), row.id + " lifetime");
    assert.equal(typeof row.owner, "string", row.id + " owner");
    assert.ok(row.owner.length > 0, row.id + " owner");
    assert.ok(Number(row.cadenceMs) >= 0, row.id + " cadence");
}

const weather = ctx.sourceSpec("weather");
assert.equal(weather.mode, "NORMAL_POLL");
assert.equal(weather.cadenceMs, 900000);
assert.equal(weather.lifetime, "SESSION_BACKGROUND");
assert.equal(weather.freshMs, 1200000);
assert.equal(weather.staleMs, 21600000);

const space = ctx.sourceSpec("space-core");
assert.equal(space.mode, "FAST_POLL");
assert.equal(space.cadenceMs, 300000);
assert.equal(space.lifetime, "SESSION_BACKGROUND");

const moon = ctx.sourceSpec("moon");
assert.equal(moon.mode, "KEYED_FETCH");
assert.equal(moon.cadenceMs, 0);
assert.equal(moon.lifetime, "KEYED_VIEW");

const firms = ctx.sourceSpec("firms");
assert.equal(firms.mode, "MANUAL");
assert.equal(firms.lifetime, "OPERATOR_REQUEST");

assert.equal(ctx.sourceSpec("missing"), null);

// Receive time and source observation time remain separate.
const now = Date.parse("2026-11-02T07:00:00Z");
const received = now - 10 * 60000;
const observed = now - 25 * 60000;
let state = ctx.runtimeState(
    weather,
    {
        active:true, ready:true, loading:false, errorText:"",
        receivedAt:received, observedAt:observed
    },
    now
);
assert.equal(state.transport, "READY");
assert.equal(state.freshness, "FRESH");
assert.equal(state.receivedAgeMs, 10 * 60000);
assert.equal(state.observationAgeMs, 25 * 60000);

state = ctx.runtimeState(
    weather,
    {active:true, ready:true, receivedAt:now - 30 * 60000},
    now
);
assert.equal(state.freshness, "AGING");

state = ctx.runtimeState(
    weather,
    {active:true, ready:true, receivedAt:now - 2 * 3600000},
    now
);
assert.equal(state.freshness, "STALE");

state = ctx.runtimeState(
    weather,
    {active:true, ready:true, receivedAt:now - 7 * 3600000},
    now
);
assert.equal(state.freshness, "EXPIRED");

state = ctx.runtimeState(
    space,
    {active:true, ready:true, receivedAt:now - 6 * 60000},
    now
);
assert.equal(state.freshness, "FRESH");

state = ctx.runtimeState(
    space,
    {active:true, ready:true, receivedAt:now - 15 * 60000},
    now
);
assert.equal(state.freshness, "AGING");

state = ctx.runtimeState(
    space,
    {active:true, ready:true, receivedAt:now - 31 * 60000},
    now
);
assert.equal(state.freshness, "STALE");

assert.equal(
    ctx.runtimeState(
        firms,
        {active:true, ready:true, receivedAt:received},
        now
    ).freshness,
    "SNAPSHOT"
);
assert.equal(
    ctx.runtimeState(
        moon,
        {active:true, ready:true, receivedAt:received},
        now
    ).freshness,
    "KEYED"
);
assert.equal(
    ctx.runtimeState(
        weather,
        {active:false, ready:true, receivedAt:received},
        now
    ).transport,
    "INACTIVE"
);
assert.equal(
    ctx.runtimeState(
        weather,
        {active:true, ready:false, loading:true},
        now
    ).transport,
    "LOADING"
);
assert.equal(
    ctx.runtimeState(
        weather,
        {active:true, ready:false, errorText:"network failed"},
        now
    ).transport,
    "ERROR"
);

assert.equal(ctx.compactAgeMinutes(-1), "--");
assert.equal(ctx.compactAgeMinutes(0), "<1m");
assert.equal(ctx.compactAgeMinutes(17), "17m");
assert.equal(ctx.compactAgeMinutes(90), "1.5h");
assert.equal(ctx.compactAgeMinutes(3000), "2d");

// The manifest is an inventory of CURRENT implementation behavior. Guard the
// declared poll cadences against the provider source files so future changes
// must update both the service and runtime contract.
for (const row of catalog) {
    const ownerPath = row.owner.includes("/")
        ? row.owner
        : "services/weather/" + row.owner;
    const owner = read(ownerPath);

    if (row.cadenceMs > 0) {
        const cadencePattern = new RegExp(
            "\\b" + String(row.cadenceMs) + "\\b"
        );
        assert.ok(owner.includes("Timer {"), row.id + " poll timer");
        assert.match(owner, cadencePattern, row.id + " declared cadence");
    }

    if (row.lifetime === "VIEW_SCOPED") {
        assert.match(owner, /property bool active:/, row.id + " active gate");
    }

    if (row.mode === "MANUAL") {
        assert.doesNotMatch(owner, /\bTimer\s*\{/, row.id + " manual timer");
    }
}

const weatherService = read("services/weather/WeatherService.qml");
assert.match(weatherService, /interval:\s*900000/);
assert.match(weatherService, /running:\s*true/);

const spaceService = read("services/weather/SpaceService.qml");
assert.match(spaceService, /interval:\s*300000/);
assert.match(spaceService, /running:\s*true/);

const nws = read("services/notifications/NwsOfficialAlertNotificationProducer.qml");
assert.match(nws, /interval:\s*900000/);
assert.match(nws, /running:\s*producer\.alertPoint !== ""/);

const ui = read("widgets/weather/WeatherStationW.qml");
assert.match(
    ui,
    /import "\.\.\/\.\.\/services\/weather\/WeatherRuntimePolicy\.js" as RuntimePolicy/
);
assert.match(ui, /RuntimePolicy\.sourceSpec\("weather-current"\)/);
assert.match(ui, /RuntimePolicy\.sourceSpec\("space-core"\)/);
assert.match(ui, /RuntimePolicy\.runtimeState\(/);
assert.match(ui, /weatherObservationAgeMinutes/);
assert.match(ui, /weatherRuntimeState\.freshness === "AGING"/);
assert.match(ui, /weatherRuntimeState\.freshness === "STALE"/);
assert.match(ui, /weatherRuntimeState\.freshness === "EXPIRED"/);
assert.doesNotMatch(ui, /weatherAgeMinutes >= 20/);

console.log("Weather live runtime M1 inventory and freshness contract: PASS");
