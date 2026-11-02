#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/WeatherLiveHistoryPolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const ctx = {
    Date, Math, Number, String, Array, Object, JSON, RegExp, isFinite
};
vm.runInNewContext(source, ctx, {
    filename: "services/weather/WeatherLiveHistoryPolicy.js"
});

const hour = 3600000;
const minute = 60000;
const now = Date.UTC(2026, 10, 2, 12, 0, 0);
const scope = "38.900|-76.900";

assert.deepEqual(
    Array.from(ctx.knownSourceIds()),
    [
        "air-quality",
        "coastal-water",
        "marine",
        "space-imf",
        "space-wind",
        "weather-current"
    ]
);

let doc = ctx.initialDocument();

function append(id, scopeKey, observedAtMs, receivedAtMs, payload, savedAtMs=receivedAtMs) {
    const result = ctx.append(
        doc, id, scopeKey, observedAtMs, receivedAtMs, payload, savedAtMs
    );
    assert.equal(result.ok, true, id + " append");
    doc = result.document;
}

append(
    "weather-current", scope, now - 30 * minute, now - 30 * minute,
    {
        tempF: 60, feelsLikeF: 59, humidity: 55, windMph: 5,
        pressureHpa: 1016, visibilityMiles: 10, cloudCover: 20,
        precipMm: 0, uvIndex: 1, condition: "Clear"
    }
);
append(
    "weather-current", scope, now - 15 * minute, now - 15 * minute,
    {
        tempF: 63, feelsLikeF: 62, humidity: 52, windMph: 8,
        pressureHpa: 1015, visibilityMiles: 10, cloudCover: 30,
        precipMm: 0, uvIndex: 2, condition: "Partly cloudy"
    }
);

assert.equal(ctx.count(doc, "weather-current", scope, now), 2);
let trend = ctx.numericTrend(
    doc, "weather-current", scope, "tempF", now
);
assert.equal(trend.count, 2);
assert.equal(trend.first, 60);
assert.equal(trend.latest, 63);
assert.equal(trend.delta, 3);

// Same provider observation replaces instead of inventing a new time point.
append(
    "weather-current", scope, now - 15 * minute, now - 14 * minute,
    {
        tempF: 64, feelsLikeF: 63, humidity: 51, windMph: 8,
        pressureHpa: 1015, visibilityMiles: 10, cloudCover: 25,
        precipMm: 0, uvIndex: 2, condition: "Partly cloudy"
    }
);
assert.equal(ctx.count(doc, "weather-current", scope, now), 2);
assert.equal(
    ctx.latest(doc, "weather-current", scope, now).payload.tempF,
    64
);

// A new geographic scope replaces the prior location's series rather than
// mixing two places into one graph.
append(
    "weather-current", "39.000|-77.000",
    now - 5 * minute, now - 5 * minute,
    {
        tempF: 58, feelsLikeF: 57, humidity: 60, windMph: 4,
        pressureHpa: 1017, visibilityMiles: 9, cloudCover: 40,
        precipMm: 0, uvIndex: 1, condition: "Cloudy"
    }
);
assert.equal(ctx.count(doc, "weather-current", scope, now), 0);
assert.equal(
    ctx.count(doc, "weather-current", "39.000|-77.000", now),
    1
);

// Restore test scope for remaining location-bound feeds.
const testScope = "38.900|-76.900";
append(
    "air-quality", testScope, now - 10 * minute, now - 10 * minute,
    {
        aqi: 42, pm25: 8, pm10: 12, ozoneAqi: 30,
        nitrogenDioxideAqi: 15, carbonMonoxideAqi: 5,
        ozone: 60, nitrogenDioxide: 8, carbonMonoxide: 180, dust: 2
    }
);

append(
    "marine", testScope, now - 20 * minute, now - 19 * minute,
    {
        stationId: "44063", sampleMillis: now - 20 * minute,
        windDirection: 220, windSpeedMs: 5.5, gustMs: 7.2,
        waveHeightM: 1.1, pressureHpa: 1014,
        airTempC: 14, waterTempC: 16, visibilityNm: 10, tideFt: 1.5
    }
);

append(
    "coastal-water", testScope, now - 6 * minute, now - 5 * minute,
    {
        stationId: "8574728", sampleMillis: now - 6 * minute,
        waterLevel: 1.24, sigma: 0.02, quality: "p"
    }
);

append(
    "space-wind", "ignored-by-policy",
    now - 3 * minute, now - 2 * minute,
    {solarWindSpeed: 430, sourceTime: "2026-11-02T11:57:00Z"}
);
append(
    "space-imf", "anything",
    now - 3 * minute, now - 2 * minute,
    {bt: 6.2, bz: -3.1, sourceTime: "2026-11-02T11:57:00Z"}
);

assert.equal(ctx.count(doc, "air-quality", testScope, now), 1);
assert.equal(ctx.count(doc, "marine", testScope, now), 1);
assert.equal(ctx.count(doc, "coastal-water", testScope, now), 1);
assert.equal(ctx.count(doc, "space-wind", "global", now), 1);
assert.equal(ctx.count(doc, "space-imf", "global", now), 1);

// 48-hour age boundary: a sample older than the window is dropped when a
// newer sample is appended.
let aging = ctx.initialDocument();
let result = ctx.append(
    aging, "space-wind", "global",
    now - 49 * hour, now - 49 * hour,
    {solarWindSpeed: 350, sourceTime: "old"},
    now - 49 * hour
);
assert.equal(result.ok, true);
aging = result.document;
result = ctx.append(
    aging, "space-wind", "global",
    now, now,
    {solarWindSpeed: 450, sourceTime: "new"},
    now
);
assert.equal(result.ok, true);
aging = result.document;
assert.equal(ctx.count(aging, "space-wind", "global", now), 1);
assert.equal(
    ctx.latest(aging, "space-wind", "global", now).payload.solarWindSpeed,
    450
);

// 5-minute space products are capped at 576 points ~= 48h.
let capped = ctx.initialDocument();
for (let i = 0; i < 600; i++) {
    const stamp = now - (599 - i) * 5 * minute;
    const appended = ctx.append(
        capped, "space-imf", "global",
        stamp, stamp,
        {bt: 5 + i / 1000, bz: -2 + i / 1000, sourceTime: String(i)},
        now
    );
    assert.equal(appended.ok, true);
    capped = appended.document;
}
assert.equal(ctx.count(capped, "space-imf", "global", now), 576);

// Invalid/undeclared categories fail closed.
assert.equal(
    ctx.append(
        doc, "weather-forecast", testScope, now, now, {}, now
    ).ok,
    false
);
assert.equal(
    ctx.append(
        doc, "lightning", testScope, now, now, {}, now
    ).ok,
    false
);

// Round trip remains bounded and versioned.
const roundTrip = ctx.parse(JSON.stringify(doc), now);
assert.equal(roundTrip.ok, true);
assert.equal(roundTrip.document.schema, "post-apollo.weather-live-history.v1");
assert.equal(roundTrip.document.version, 1);

const store = read("services/weather/WeatherLiveHistoryStore.qml");
assert.match(store, /weather-live-history-v1\.json/);
assert.equal((store.match(/\bFileView\s*\{/g) || []).length, 1);
assert.equal((store.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((store.match(/\bTimer\s*\{/g) || []).length, 0);
assert.match(store, /atomicWrites:\s*true/);
assert.match(store, /deferredSamples/);
assert.match(store, /HistoryPolicy\.append/);

const weather = read("services/weather/WeatherService.qml");
assert.match(weather, /property var historyStore: null/);
assert.match(weather, /historyStore\.append\(\s*"weather-current"/);
assert.match(weather, /historyStore\.append\(\s*"air-quality"/);
assert.match(
    weather,
    /persistCurrentWeather\(receivedAt\.getTime\(\)\);[\s\S]*?captureCurrentHistory/
);
assert.match(
    weather,
    /persistAirQuality\(aqiLastUpdated\.getTime\(\)\);[\s\S]*?captureAirQualityHistory/
);
assert.doesNotMatch(
    weather.slice(
        weather.indexOf("function hydratePersistentCache"),
        weather.indexOf("function persistCurrentWeather")
    ),
    /historyStore\.append/
);

const space = read("services/weather/SpaceService.qml");
assert.match(space, /property var historyStore: null/);
assert.match(space, /historyStore\.append\(\s*"space-wind"/);
assert.match(space, /historyStore\.append\(\s*"space-imf"/);
assert.doesNotMatch(space, /historyStore\.append\(\s*"space-kp"/);
assert.doesNotMatch(space, /historyStore\.append\(\s*"space-flux"/);

const marine = read("services/weather/NdbcMarineService.qml");
assert.match(marine, /property var historyStore: null/);
assert.match(marine, /historyStore\.append\(\s*"marine"/);
assert.match(marine, /Number\(station\.sampleMillis\)/);

const coastal = read("services/weather/CoopsCoastalService.qml");
assert.match(coastal, /property var historyStore: null/);
assert.match(coastal, /historyStore\.append\(\s*"coastal-water"/);
assert.match(coastal, /Number\(waterLevel\.sampleMillis\)/);
assert.doesNotMatch(coastal, /historyStore\.append\(\s*"coastal-tides"/);

const shell = read("shell.qml");
assert.equal(
    (shell.match(/WeatherLiveHistoryStore\s*\{/g) || []).length,
    1
);
assert.match(
    shell,
    /WeatherService\s*\{[\s\S]*?historyStore: weatherLiveHistory/
);
assert.match(
    shell,
    /SpaceService\s*\{[\s\S]*?historyStore: weatherLiveHistory/
);
assert.match(
    shell,
    /WeatherStationW\s*\{[\s\S]*?liveHistoryStore: weatherLiveHistory/
);

const station = read("widgets/weather/WeatherStationW.qml");
assert.match(station, /property var liveHistoryStore: null/);
assert.match(
    station,
    /StationHome\s*\{[\s\S]*?liveHistoryStore: weatherStation\.liveHistoryStore/
);
assert.match(
    station,
    /StationGround\s*\{[\s\S]*?liveHistoryStore: weatherStation\.liveHistoryStore/
);
assert.match(
    station,
    /StationSpace\s*\{[\s\S]*?liveHistoryStore: weatherStation\.liveHistoryStore/
);
assert.doesNotMatch(
    station,
    /StationSky\s*\{[\s\S]*?liveHistoryStore:/
);

const home = read("widgets/weather/StationHome.qml");
const ground = read("widgets/weather/StationGround.qml");
const stationSpace = read("widgets/weather/StationSpace.qml");
for (const src of [home, ground, stationSpace])
    assert.match(src, /HISTORY/);

assert.match(ground, /historyStore: ground\.liveHistoryStore/);
assert.match(ground, /"coastal-water"/);
assert.match(stationSpace, /"space-wind"/);
assert.match(stationSpace, /"space-imf"/);

console.log("Weather M10 selective live-history capture: PASS");
