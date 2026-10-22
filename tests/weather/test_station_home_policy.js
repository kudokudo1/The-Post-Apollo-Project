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

function choose(overrides = {}) {
    return context.chooseRelevant({
        weatherReady: true,
        aqiReady: true,
        spaceReady: true,
        aqi: 25,
        aqiLabel: "GOOD",
        uvIndex: 1,
        hourlyForecast: [{
            timeLabel: "12 PM",
            tempF: 70,
            chanceRain: 10,
            condition: "Partly cloudy",
        }],
        kp: 2,
        kpLabel: "QUIET",
        solarWindSpeed: 420,
        bz: 1,
        spaceError: "",
        ...overrides,
    });
}

let result = choose();
assert.equal(result.title, "NEXT HOURS");
assert.equal(result.source, "sky");
assert.equal(result.rank, 0);

result = choose({
    aqi: 175,
    aqiLabel: "UNHEALTHY",
    uvIndex: 6,
    kp: 5,
});
assert.equal(result.title, "AIR QUALITY");
assert.equal(result.value, "AQI 175");
assert.equal(result.source, "ground");
assert.ok(result.rank > 90);

result = choose({
    aqi: 40,
    uvIndex: 9,
    kp: 4,
});
assert.equal(result.title, "UV INDEX");
assert.equal(result.value, "9");
assert.equal(result.source, "sky");

result = choose({
    aqi: 40,
    uvIndex: 2,
    kp: 6,
    kpLabel: "G2 STORM",
});
assert.equal(result.title, "GEOMAGNETIC");
assert.equal(result.value, "KP 6.0");
assert.equal(result.source, "space");

result = choose({
    weatherReady: false,
    aqiReady: false,
});
assert.equal(result.title, "WEATHER LINK");
assert.equal(result.value, "OFFLINE");
assert.equal(result.rank, 100);

result = choose({
    aqi: 40,
    uvIndex: 2,
    kp: 2,
    hourlyForecast: [{
        timeLabel: "3 PM",
        tempF: 68,
        chanceRain: 80,
        condition: "Rain",
    }],
});
assert.equal(result.title, "RAIN CHANCE");
assert.equal(result.value, "80%");
assert.equal(result.source, "sky");
assert.equal(result.meterValue, 0.8);

console.log("Weather Station Home policy contracts: PASS");
