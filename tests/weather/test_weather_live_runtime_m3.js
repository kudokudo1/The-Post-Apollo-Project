#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/WeatherRuntimePolicy.js");
const ctx = {Date, Math, Number, String, Array, Object, JSON, isFinite};
vm.runInNewContext(source.replace(/^\.pragma library\s*/m, ""), ctx);

for (const fn of [
    "effectiveExpireMs", "temporalBand", "availabilityState",
    "availabilityLabel", "retentionLabel", "compactDurationMs"
])
    assert.equal(typeof ctx[fn], "function", fn);

const minute = 60000;
const hour = 60 * minute;
const day = 24 * hour;
const now = Date.parse("2026-11-02T09:00:00Z");

// One fetch owner can expose different semantic cache windows.
const current = ctx.sourceSpec("weather-current");
const forecast = ctx.sourceSpec("weather-forecast");
const aqi = ctx.sourceSpec("air-quality");
assert.equal(current.owner, "WeatherService.qml");
assert.equal(forecast.owner, "WeatherService.qml");
assert.equal(aqi.owner, "WeatherService.qml");
assert.equal(current.cadenceMs, 15 * minute);
assert.equal(forecast.cadenceMs, 15 * minute);
assert.equal(aqi.cadenceMs, 15 * minute);

assert.equal(current.freshMs, 20 * minute);
assert.equal(current.staleMs, 90 * minute);
assert.equal(current.expireMs, 6 * hour);
assert.equal(forecast.freshMs, 3 * hour);
assert.equal(forecast.staleMs, 24 * hour);
assert.equal(forecast.expireMs, 8 * day);
assert.equal(aqi.freshMs, 30 * minute);
assert.equal(aqi.staleMs, 3 * hour);
assert.equal(aqi.expireMs, 12 * hour);

for (const spec of [current, forecast, aqi])
    assert.equal(spec.retention, "MEMORY_LAST_GOOD");

// Current weather transitions FRESH -> AGING -> STALE -> EXPIRED.
assert.equal(ctx.temporalBand(current, now - 10 * minute, now), "FRESH");
assert.equal(ctx.temporalBand(current, now - 45 * minute, now), "AGING");
assert.equal(ctx.temporalBand(current, now - 2 * hour, now), "STALE");
assert.equal(ctx.temporalBand(current, now - 7 * hour, now), "EXPIRED");

// A failed refresh with a retained last-good payload becomes CACHE, not LIVE.
let row = ctx.displayRow(
    "weather-current",
    {
        active:true, ready:true, errorText:"request failed",
        receivedAt:now - 10 * minute
    },
    now
);
assert.equal(row.transport, "DEGRADED");
assert.equal(row.availability, "CACHE_FRESH");
assert.equal(ctx.rowStateLabel(row), "CACHE // FRESH");
assert.equal(ctx.statusToken(row), "blue");
assert.equal(ctx.retentionLabel(row), "MEMORY≤6h");

row = ctx.displayRow(
    "weather-current",
    {
        active:true, ready:true, errorText:"request failed",
        receivedAt:now - 45 * minute
    },
    now
);
assert.equal(row.availability, "CACHE_AGING");
assert.equal(ctx.rowStateLabel(row), "CACHE // AGING");
assert.equal(ctx.statusToken(row), "yellow");

row = ctx.displayRow(
    "weather-current",
    {
        active:true, ready:true, errorText:"request failed",
        receivedAt:now - 2 * hour
    },
    now
);
assert.equal(row.availability, "CACHE_STALE");
assert.equal(ctx.rowStateLabel(row), "CACHE // STALE");

row = ctx.displayRow(
    "weather-current",
    {
        active:true, ready:true, errorText:"request failed",
        receivedAt:now - 7 * hour
    },
    now
);
assert.equal(row.availability, "CACHE_EXPIRED");
assert.equal(ctx.rowStateLabel(row), "CACHE // EXPIRED");
assert.equal(ctx.statusToken(row), "red");

// No successful payload means there is no cache to pretend exists.
row = ctx.displayRow(
    "weather-current",
    {active:true, ready:false, errorText:"request failed"},
    now
);
assert.equal(row.availability, "OFFLINE");
assert.equal(ctx.statusToken(row), "red");

// StationDiscovery has a real session cache signal independent of failure.
row = ctx.displayRow(
    "discovery",
    {
        active:true, ready:true, usingCache:true,
        receivedAt:now - 20 * minute
    },
    now
);
assert.equal(row.availability, "CACHE_FRESH");
assert.equal(row.retention, "SESSION_CACHE");
assert.equal(ctx.retentionLabel(row), "SESSION≤1d");

// Manual radar snapshots age independently of polling.
const radar = ctx.sourceSpec("mrms-radar");
assert.equal(radar.retention, "OPERATOR_SNAPSHOT");
assert.equal(radar.freshMs, 10 * minute);
assert.equal(radar.staleMs, 30 * minute);
assert.equal(radar.expireMs, 2 * hour);

row = ctx.displayRow(
    "mrms-radar",
    {active:true, ready:true, receivedAt:now - 5 * minute},
    now
);
assert.equal(row.freshness, "SNAPSHOT");
assert.equal(row.ageBand, "FRESH");
assert.equal(row.availability, "SNAPSHOT");
assert.equal(ctx.rowStateLabel(row), "SNAPSHOT // FRESH");
assert.equal(ctx.retentionLabel(row), "SNAPSHOT≤2h");

row = ctx.displayRow(
    "mrms-radar",
    {active:true, ready:true, receivedAt:now - 20 * minute},
    now
);
assert.equal(row.availability, "SNAPSHOT_AGING");

row = ctx.displayRow(
    "mrms-radar",
    {active:true, ready:true, receivedAt:now - hour},
    now
);
assert.equal(row.availability, "SNAPSHOT_STALE");

row = ctx.displayRow(
    "mrms-radar",
    {active:true, ready:true, receivedAt:now - 3 * hour},
    now
);
assert.equal(row.availability, "SNAPSHOT_EXPIRED");
assert.equal(ctx.statusToken(row), "red");

// Keyed services are valid for the active key; their services clear readiness
// when the key changes or a replacement fetch cannot be established.
row = ctx.displayRow("moon", {active:true, ready:true}, now);
assert.equal(row.availability, "KEY_VALID");
assert.equal(ctx.rowStateLabel(row), "KEYED // VALID");
assert.equal(ctx.retentionLabel(row), "KEY-BOUND");

row = ctx.displayRow(
    "moon",
    {active:true, ready:false, failed:true, errorText:"USNO failed"},
    now
);
assert.equal(row.availability, "OFFLINE");

// Local calculation has no network cache claim.
row = ctx.displayRow("sky-local", {active:true, ready:true}, now);
assert.equal(row.availability, "LOCAL");
assert.equal(ctx.retentionLabel(row), "LOCAL");

// Provider-specific cache profiles cover high-volatility and slower products.
assert.equal(ctx.sourceSpec("lightning").expireMs, 2 * hour);
assert.equal(ctx.sourceSpec("river").expireMs, 12 * hour);
assert.equal(ctx.sourceSpec("coastal").expireMs, 24 * hour);
assert.equal(ctx.sourceSpec("aurora").expireMs, 2 * hour);
assert.equal(ctx.sourceSpec("xray-flux").expireMs, 2 * hour);
assert.equal(ctx.sourceSpec("hms-smoke").expireMs, 36 * hour);
assert.equal(ctx.sourceSpec("firms").expireMs, 24 * hour);

// SPACE uses one process owner but exposes independent product cache health.
for (const id of ["space-kp","space-wind","space-imf","space-flux"]) {
    const spec = ctx.sourceSpec(id);
    assert.equal(spec.owner, "SpaceService.qml");
    assert.equal(spec.retention, "MEMORY_LAST_GOOD");
}
assert.equal(ctx.sourceSpec("space-kp").expireMs, 2 * hour);
assert.equal(ctx.sourceSpec("space-flux").expireMs, 12 * hour);

const summary = ctx.summarizeRows([
    ctx.displayRow("weather-current", {
        active:true, ready:true, errorText:"failed",
        receivedAt:now - 10 * minute
    }, now),
    ctx.displayRow("mrms-radar", {
        active:true, ready:true, receivedAt:now - 3 * hour
    }, now),
    ctx.displayRow("moon", {
        active:true, ready:false, failed:true
    }, now),
    ctx.displayRow("sky-local", {
        active:true, ready:true
    }, now)
]);
assert.equal(summary.cached, 1);
assert.equal(summary.expired, 1);
assert.equal(summary.offline, 1);
assert.equal(summary.local, 1);

// UI contract: current/forecast/AQ are separately aged without multiplying
// fetch owners, and fake observation age from localObservationAnchorMs is gone.
const home = read("widgets/weather/StationHome.qml");
const ground = read("widgets/weather/StationGround.qml");
const sky = read("widgets/weather/StationSky.qml");
for (const ui of [home, sky]) {
    assert.match(ui, /"weather-current"/);
    assert.match(ui, /"weather-forecast"/);
    assert.match(ui, /"air-quality"/);
    assert.match(ui, /PROVIDER ISSUE TIME NOT EXPOSED/);
}
assert.match(ground, /"weather-current"/);
assert.match(ground, /"air-quality"/);
assert.doesNotMatch(home, /"observedAt": weatherService[\s\S]{0,100}localObservationAnchorMs/);
assert.doesNotMatch(ground, /"observedAt": weatherService[\s\S]{0,100}localObservationAnchorMs/);
assert.doesNotMatch(sky, /"observedAt": weatherService[\s\S]{0,100}localObservationAnchorMs/);

const space = read("widgets/weather/StationSpace.qml");
for (const id of ["space-kp","space-wind","space-imf","space-flux"])
    assert.ok(space.includes('"' + id + '"'));
assert.match(space, /"observedAt": spaceService \? spaceService\.kpTime/);
assert.match(space, /spaceService\.solarWindTime/);
assert.match(space, /spaceService\.magneticFieldTime/);
assert.match(space, /spaceService\.solarFluxTime/);

const discovery = read("widgets/weather/StationDiscovery.qml");
assert.match(discovery, /"usingCache": source\.usingCache/);

const rack = read("widgets/weather/StationRuntimeRack.qml");
assert.match(rack, /rack\.summary\.cached/);
assert.match(rack, /rack\.summary\.expired/);
assert.match(rack, /rack\.summary\.offline/);
assert.match(rack, /RuntimePolicy\.retentionLabel\(modelData\)/);
assert.doesNotMatch(rack, /\bTimer\s*\{|\bProcess\s*\{|FileView|XMLHttpRequest|curl/);

const station = read("widgets/weather/WeatherStationW.qml");
assert.match(station, /RuntimePolicy\.sourceSpec\("weather-current"\)/);
assert.match(station, /return "CACHE FRESH";/);
assert.match(station, /return "CACHE AGING";/);
assert.match(station, /return "CACHE STALE";/);
assert.match(station, /return "CACHE EXPIRED";/);
assert.match(station, /return "MAP CACHE";/);
assert.doesNotMatch(
    station,
    /"observedAt": weatherService[\s\S]{0,100}localObservationAnchorMs/
);

// M3 remains policy/UI-only. It adds no new persistence or network owner.
assert.doesNotMatch(source, /\bProcess\s*\{|FileView|XMLHttpRequest|curl/);

console.log("Weather live runtime M3 cache and offline validity: PASS");
