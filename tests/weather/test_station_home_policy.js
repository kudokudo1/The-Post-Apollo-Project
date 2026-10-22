#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(
    path.join(root, "widgets/weather/StationHomePolicy.js"),
    "utf8"
).replace(/^\.pragma library\s*/m, "");

const context = {};
vm.runInNewContext(source, context);

assert.equal(typeof context.chooseRelevant, "function");
assert.equal(typeof context.rankRelevant, "function");
assert.equal(typeof context.minutesUntilClock, "function");

function base(overrides = {}) {
    return {
        weatherReady: true,
        weatherStale: false,
        weatherAgeMinutes: 2,
        weatherError: "",
        aqiReady: true,
        aqiError: "",
        spaceReady: true,
        spacePartial: false,
        spaceStale: false,
        spaceStaleDetail: "",
        spaceError: "",

        temperatureF: 70,
        humidity: 45,
        windMph: 8,
        windDirection: "NW",
        condition: "Partly cloudy",
        pressureHpa: 1014,
        visibilityMiles: 10,
        cloudCover: 30,
        uvIndex: 1,

        aqi: 25,
        aqiLabel: "GOOD",
        pm25: 6,

        hourlyForecast: [{
            timeLabel: "12 PM",
            tempF: 70,
            chanceRain: 10,
            condition: "Partly cloudy",
        }],
        dailyForecast: [{
            date: "2026-10-22",
            maxTempF: 74,
            minTempF: 52,
            condition: "Partly cloudy",
            sunrise: "07:20 AM",
            sunset: "06:15 PM",
        }],

        kp: 2,
        kpLabel: "QUIET",
        solarWindSpeed: 420,
        bz: 1,
        bt: 6,
        solarFlux: 130,

        temperatureDelta: 0,
        pressureDelta: 0,
        rainChanceDelta: 0,
        aqiDelta: 0,
        kpDelta: 0,
        solarWindDelta: 0,
        bzDelta: 0,

        nowMinutes: 12 * 60,

        ...overrides,
    };
}

function ranked(overrides = {}, previous = [], limit = 3) {
    return context.rankRelevant(base(overrides), previous, limit);
}

function first(overrides = {}, previous = []) {
    return ranked(overrides, previous, 3)[0];
}

// Normal state keeps useful low-priority baselines instead of inventing an alert.
let result = first();
assert.equal(result.id, "next-hours");
assert.equal(result.rank, 0);
assert.equal(result.source, "sky");
assert.equal(ranked().length, 3);

// Multiple simultaneous conditions are preserved and ranked.
let results = ranked({
    aqi: 175,
    aqiLabel: "UNHEALTHY",
    uvIndex: 9,
    kp: 5,
}, [], 3);
assert.deepEqual(
    Array.from(results, item => item.id),
    ["air-quality", "uv-index", "geomagnetic"]
);

// Weather source failure outranks ordinary conditions.
result = first({
    weatherReady: false,
    aqiReady: false,
});
assert.equal(result.id, "weather-link");
assert.equal(result.rank, 100);

// Stale weather is distinct from offline.
result = first({
    weatherStale: true,
    weatherAgeMinutes: 26,
});
assert.equal(result.id, "weather-stale");
assert.match(result.detail, /26 MIN AGO/);

// Space can report a partial source without taking the entire HOME offline.
result = first({
    spaceReady: false,
    spacePartial: true,
    spaceError: "",
});
assert.equal(result.id, "space-feed");
assert.equal(result.value, "PARTIAL");

// Space freshness is a separate source-health state from partial/offline.
result = first({
    spaceStale: true,
    spaceStaleDetail: "STALE // WIND 48m",
});
assert.equal(result.id, "space-feed");
assert.equal(result.value, "STALE");
assert.match(result.detail, /WIND 48M/);

// Combined weather conditions outrank their component cards.
result = first({
    temperatureF: 91,
    humidity: 72,
    windMph: 28,
    hourlyForecast: [{
        timeLabel: "3 PM",
        tempF: 89,
        chanceRain: 82,
        condition: "Rain",
    }],
});
assert.equal(result.id, "wind-rain");
assert.ok(
    ranked({
        temperatureF: 91,
        humidity: 72,
        windMph: 28,
        hourlyForecast: [{
            timeLabel: "3 PM",
            tempF: 89,
            chanceRain: 82,
            condition: "Rain",
        }],
    }).some(item => item.id === "hot-humid")
);

// Space stack combines Kp, solar wind and southward Bz instead of crowding
// all three watch slots with near-duplicate space cards.
result = first({
    kp: 5,
    kpLabel: "G1 STORM",
    solarWindSpeed: 710,
    bz: -8,
    bt: 12,
});
assert.equal(result.id, "space-stack");
assert.match(result.detail, /710 KM\/S/);
assert.match(result.detail, /BZ -8\.0 nT/);
assert.match(result.detail, /BT 12\.0 nT/);

// Low visibility and strong wind can promote independently.
results = ranked({
    visibilityMiles: 0.8,
    windMph: 32,
}, [], 4);
assert.ok(results.some(item => item.id === "low-visibility"));
assert.ok(results.some(item => item.id === "strong-wind"));

// Trend-only cards appear when the absolute reading is otherwise ordinary.
result = first({
    temperatureF: 68,
    temperatureDelta: -7,
});
assert.equal(result.id, "temperature-trend");
assert.equal(result.value, "-7°F");

result = first({
    pressureHpa: 1004,
    pressureDelta: -4.5,
});
assert.equal(result.id, "pressure-trend");
assert.equal(result.value, "-4.5 hPa");

result = first({
    aqi: 45,
    aqiDelta: 24,
});
assert.equal(result.id, "air-quality-trend");

result = first({
    kp: 3.5,
    kpDelta: 1.5,
});
assert.equal(result.id, "kp-trend");

result = first({
    solarWindSpeed: 470,
    solarWindDelta: 130,
});
assert.equal(result.id, "solar-wind-trend");

result = first({
    bz: 2,
    bzDelta: -6,
});
assert.equal(result.id, "bz-trend");

// Hysteresis keeps a promoted condition while it is near the release edge,
// then drops it after the reading clearly settles.
results = ranked({
    uvIndex: 6,
}, [], 3);
assert.ok(results.some(item => item.id === "uv-index"));

results = ranked({
    uvIndex: 2.7,
}, ["uv-index"], 3);
assert.ok(results.some(item => item.id === "uv-index"));

results = ranked({
    uvIndex: 2.2,
}, ["uv-index"], 3);
assert.ok(!results.some(item => item.id === "uv-index"));

// Sunrise/sunset become relevant near their local clock times.
result = first({
    nowMinutes: 6 * 60 + 50,
    dailyForecast: [{
        maxTempF: 74,
        minTempF: 52,
        condition: "Clear",
        sunrise: "07:20 AM",
        sunset: "06:15 PM",
    }],
});
assert.equal(result.id, "sunrise-window");
assert.equal(result.detail, "IN 30 MIN");

result = first({
    nowMinutes: 17 * 60 + 45,
    dailyForecast: [{
        maxTempF: 74,
        minTempF: 52,
        condition: "Clear",
        sunrise: "07:20 AM",
        sunset: "06:15 PM",
    }],
});
assert.equal(result.id, "sunset-window");
assert.equal(result.detail, "IN 30 MIN");

// Clock parsing stays deterministic for 12-hour provider strings.
assert.equal(context.minutesUntilClock("12:15 PM", 12 * 60), 15);
assert.equal(context.minutesUntilClock("12:15 AM", 0), 15);
assert.equal(context.minutesUntilClock("bad", 0), -1);

// Baseline catalog includes lower-priority atmospheric, space and particulate
// cards so AUTO can stay informative when nothing urgent is happening.
results = ranked({}, [], 10);
for (const id of [
    "next-hours",
    "today-range",
    "pressure-baseline",
    "space-baseline",
    "particulate-baseline",
]) {
    assert.ok(results.some(item => item.id === id), id);
}

console.log("Weather Station Home relevance contracts: PASS");
