#!/usr/bin/env node
"use strict";

// Execute the same pure JavaScript policy used by QML with deterministic inputs.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const src = fs.readFileSync(path.join(root, "services/weather/WeatherDockPolicy.js"), "utf8")
              .replace(/^\.pragma library\s*/m, "");
const context = {};
vm.runInNewContext(src, context);
assert.equal(typeof context.classify, "function");
assert.equal(typeof context.formatTemperature, "function");

// The exact same observed Fahrenheit reading supports both presentation units.
assert.equal(context.formatTemperature("72", true, false), "72°F");
assert.equal(context.formatTemperature("72", true, true), "22°C");
assert.equal(context.formatTemperature("32", true, true), "0°C");
assert.equal(context.formatTemperature("-40", true, false), "-40°F");
assert.equal(context.formatTemperature("-40", true, true), "-40°C");
assert.equal(context.formatTemperature("98.6", true, false), "99°F");
assert.equal(context.formatTemperature("98.6", true, true), "37°C");
assert.equal(context.formatTemperature("-0.1", true, false), "0°F");
assert.equal(context.formatTemperature("--", true, false), "--°F");
assert.equal(context.formatTemperature("", true, true), "--°C");
assert.equal(context.formatTemperature("75", false, false), "--°F");
assert.equal(context.formatTemperature("75", false, true), "--°C");
assert.equal(context.formatTemperature(null, true, true), "--°C");
assert.equal(context.formatTemperature("Infinity", true, false), "--°F");

const nowMs = 1780000000000;
function reading(patch = {}) {
    return {
        nowMs, ready: true, errorText: "", weatherTimeMs: nowMs - 10000,
        weatherCode: "113", condition: "Sunny", windMph: "5",
        uvIndex: 2, aqiReady: true, aqiErrorText: "",
        aqiTimeMs: nowMs - 10000, aqi: 42, ...patch
    };
}
function expectColor(patch, expected) {
    const actual = context.classify(reading(patch));
    assert.equal(actual.color, expected, JSON.stringify(patch));
    return actual;
}

expectColor({ weatherCode: "113", condition: "Sunny" }, "orange");
expectColor({ weatherCode: "116", condition: "Partly cloudy" }, "orange");
expectColor({ weatherCode: "119", condition: "Cloudy" }, "yellow");
expectColor({ weatherCode: "248", condition: "Fog" }, "yellow");
expectColor({ weatherCode: "338", condition: "Heavy snow" }, "cyan");
expectColor({ weatherCode: "317", condition: "Sleet" }, "cyan");
expectColor({ weatherCode: "308", condition: "Heavy rain" }, "blue");
expectColor({ weatherCode: "389", condition: "Thunder and rain" }, "magenta");
expectColor({ weatherCode: "350", condition: "Ice pellets" }, "white");
expectColor({ weatherCode: "113", windMph: "25" }, "omnitrix");
expectColor({ weatherCode: "308", windMph: "28" }, "omnitrix");
expectColor({ weatherCode: "389", windMph: "48" }, "magenta");
expectColor({ weatherCode: "113", uvIndex: 8 }, "red");
expectColor({ weatherCode: "119", aqi: 151 }, "red");
expectColor({ weatherCode: "389", uvIndex: 10, aqi: 175 }, "red");
expectColor({ aqi: 151, aqiErrorText: "fetch failed" }, "orange");
expectColor({ aqi: 151, aqiTimeMs: nowMs - 3700000 }, "orange");
expectColor({ uvIndex: -1, weatherCode: "113" }, "orange");
expectColor({ weatherTimeMs: nowMs - 3700000 }, "white");
expectColor({ ready: false }, "white");
expectColor({ errorText: "request failed" }, "white");
expectColor({ weatherCode: "999", condition: "Unknown" }, "white");
expectColor({ weatherCode: "", condition: "Thunderstorm" }, "magenta");
assert.equal(context.classify(reading({ weatherTimeMs: 0 })).label,
             "WEATHER UNAVAILABLE");

// The dock has no independent fetch; the session-wide service owns updates.
const dock = fs.readFileSync(path.join(root, "modules/Weather.qml"), "utf8");
const shell = fs.readFileSync(path.join(root, "shell.qml"), "utf8");
assert.match(dock, /weatherStationWindow\.toggle\(\)/);
assert.match(dock, /implicitHeight:\s*50/);
assert.match(dock, /implicitWidth:\s*Math\.ceil\(weatherContent\.implicitWidth\)\s*\+\s*6/);
// Keep the original identity glyph while rendering condition and temperature separately.
assert.match(dock, /id:\s*weatherThermometer[\s\S]*?text:\s*"🌡"[\s\S]*?font\.pixelSize:\s*24/);
assert.match(dock, /property bool useCelsius:\s*false/);
assert.match(dock, /onRightClicked:\s*\{\s*useCelsius\s*=\s*!useCelsius;/);
assert.match(dock, /WeatherDockPolicy\.formatTemperature\([\s\S]*?weatherFresh,[\s\S]*?useCelsius/);
assert.match(dock, /id:\s*weatherCondition[\s\S]*?text:\s*weatherDock\.weatherState\.icon[\s\S]*?font\.pixelSize:\s*32/);
assert.match(dock, /id:\s*weatherTemperatureValue[\s\S]*?text:\s*weatherDock\.temperatureLabel\.slice\(0, -2\)[\s\S]*?font\.pixelSize:\s*20/);
assert.match(dock, /id:\s*weatherTemperatureUnit[\s\S]*?text:\s*weatherDock\.temperatureLabel\.slice\(-1\)[\s\S]*?font\.pixelSize:\s*20/);
assert.match(dock, /id:\s*weatherDegree[\s\S]*?text:\s*"°"[\s\S]*?font\.pixelSize:\s*20[\s\S]*?color:\s*weatherDock\.open\s*\|\|\s*weatherDock\.pressed[\s\S]*?Colors\.magenta[\s\S]*?weatherDock\.hovered\s*\?\s*Colors\.orange\s*:\s*Colors\.white/);
assert.match(dock, /SafeDropShadow\s*\{[^}]*safeSource:\s*weatherDegree[^}]*color:\s*weatherDock\.open\s*\|\|\s*weatherDock\.pressed\s*\?\s*Colors\.magenta\s*:\s*Colors\.orange/s);
assert.match(dock, /id:\s*weatherContent[\s\S]*?spacing:\s*6/);
assert.match(dock, /id:\s*weatherReadout[\s\S]*?spacing:\s*0/);
assert.match(dock, /id:\s*weatherTemperature[\s\S]*?spacing:\s*0/);
assert.match(dock, /contentGlowSource:\s*weatherContent/);
// Idle uses observed weather colors; interaction takes the standard orange -> magenta path.
for (const [property, color] of [
    ["normalForegroundColor", "weatherColor"],
    ["normalContentGlowColor", "weatherColor"],
    ["normalDockGlowColor", "weatherColor"],
    ["hoverForegroundColor", "Colors.orange"],
    ["hoverContentGlowColor", "Colors.orange"],
    ["hoverDockGlowColor", "Colors.orange"],
    ["pressedForegroundColor", "Colors.magenta"],
    ["pressedContentGlowColor", "Colors.magenta"],
    ["pressedDockGlowColor", "Colors.magenta"],
    ["openForegroundColor", "Colors.magenta"],
    ["openGlowColor", "Colors.magenta"],
    ["openFillColor", "Colors.yellow"]
]) {
    assert.ok(dock.includes(property + ": " + color), property + " should use " + color);
}
assert.match(dock, /id:\\s*weatherThermometer[\\s\\S]*?color:\\s*weatherDock\\.open\\s*\\|\\|\\s*weatherDock\\.pressed[\\s\\S]*?Colors\\.magenta\\s*:\\s*Colors\\.orange/);
assert.match(dock, /id:\\s*weatherContent[\\s\\S]*?spacing:\\s*6/);
assert.ok(dock.indexOf("id: weatherCondition") < dock.indexOf("id: weatherTemperature"));
assert.ok(dock.indexOf("id: weatherTemperature") < dock.indexOf("id: weatherThermometer"));
assert.ok(dock.indexOf("id: weatherTemperatureUnit") < dock.indexOf("id: weatherThermometer"));
assert.match(dock, /WeatherDockPolicy\.classify/);
assert.doesNotMatch(dock, /\bProcess\s*\{/);
assert.match(shell, /Weather\s*\{[^}]*weatherService:\s*weatherService/s);

console.log("Weather dock live state contracts: PASS");
