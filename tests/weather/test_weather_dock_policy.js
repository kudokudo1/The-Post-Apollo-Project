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
assert.equal(typeof context.temperatureState, "function");

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

// Fixed comfort baseline A, with lower/upper boundary checks for each band.
for (const [temp, color] of [
    [-40, "white"], [15, "white"], [16, "cyan"], [32, "cyan"],
    [33, "blue"], [49, "blue"], [50, "magenta"], [59, "magenta"],
    [60, "yellow"], [75, "yellow"], [76, "orange"], [89, "orange"],
    [90, "red"], [113, "red"]
]) {
    const state = context.temperatureState(String(temp), true);
    assert.equal(state.valid, true, "valid " + temp);
    assert.equal(state.color, color, "color at " + temp);
    assert.ok(state.level >= 0 && state.level <= 1, "clamped at " + temp);
}
assert.equal(context.temperatureState("32", true).level,
             (32 + 20) / 130);
assert.equal(context.temperatureState("0", true).level,
             20 / 130);
assert.equal(context.temperatureState("-25", true).level, 0);
assert.equal(context.temperatureState("115", true).level, 1);
for (const [temp, ready] of [["--", true], ["", true],
                            [null, true], ["75", false], ["NaN", true]]) {
    const state = context.temperatureState(temp, ready);
    assert.equal(state.valid, false);
    assert.equal(state.level, 0);
}
// Changing Fahrenheit/Celsius display cannot alter the physical gauge.
assert.equal(context.formatTemperature("72", true, true), "22°C");
assert.equal(context.temperatureState("72", true).color, "yellow");

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
// Preserve an identifiable weather condition, live numeric readout, and a
// compact classic thermometer. Canvas was not rendering in the dock at runtime,
// so the instrument must use native Qt Quick Shapes instead.
assert.match(dock, /import QtQuick\.Shapes/);
assert.match(dock, /id:\s*weatherThermometer[\s\S]*?implicitWidth:\s*17[\s\S]*?implicitHeight:\s*35[\s\S]*?width:\s*implicitWidth[\s\S]*?height:\s*implicitHeight/);
assert.doesNotMatch(dock, /text:\s*"🌡"/);
assert.doesNotMatch(dock, /\bCanvas\s*\{/);
assert.match(dock, /\bShape\s*\{/);
assert.match(dock, /\bShapePath\s*\{/);
assert.match(dock, /\bPathQuad\s*\{/);
assert.match(dock, /\bPathCubic\s*\{/);
// At tiny dock sizes, mathematically circular curves can still rasterize
// unevenly. Check the deliberate elliptical proportions and matched inset.
assert.match(dock, /readonly property real bulbCenterX:\s*width \/ 2/);
assert.match(dock, /readonly property real bulbCenterY:\s*26\.0/);
assert.match(dock, /readonly property real joinDiagonal:\s*Math\.SQRT1_2/);
assert.match(dock, /layer\.enabled:\s*true/);
assert.match(dock, /layer\.samples:\s*4/);
assert.match(dock, /layer\.smooth:\s*true/);
assert.equal((dock.match(/PathArc\s*\{/g) || []).length, 6);
assert.equal((dock.match(/direction:\s*PathArc\.Clockwise/g) || []).length, 6);
assert.equal((dock.match(/radiusX:\s*weatherThermometer\.outerBulbRadiusX/g) || []).length, 4);
assert.equal((dock.match(/radiusY:\s*weatherThermometer\.outerBulbRadiusY/g) || []).length, 4);
assert.equal((dock.match(/radiusX:\s*weatherThermometer\.innerBulbRadiusX/g) || []).length, 2);
assert.equal((dock.match(/radiusY:\s*weatherThermometer\.innerBulbRadiusY/g) || []).length, 2);
assert.equal((dock.match(/startX:\s*weatherThermometer\.bulbCenterX/g) || []).length, 3);
assert.match(dock, /strokeWidth:\s*1\.5\s+strokeColor:\s*weatherThermometer\.glassColor\s+joinStyle:\s*ShapePath\.RoundJoin\s+capStyle:\s*ShapePath\.RoundCap/);

// Check pixel-space offsets, avoiding hidden one-sided clearance regressions.
function readGaugeNumber(property) {
    const pattern = new RegExp("readonly property real " + property + ": ([0-9.]+)");
    const result = dock.match(pattern);
    assert.ok(result, "gauge property " + property);
    return Number(result[1]);
}
const width = 17, height = 35;
const cx = width / 2, cy = readGaugeNumber("bulbCenterY");
const outerRx = readGaugeNumber("outerBulbRadiusX");
const outerRy = readGaugeNumber("outerBulbRadiusY");
const innerRx = readGaugeNumber("innerBulbRadiusX");
const innerRy = readGaugeNumber("innerBulbRadiusY");
const strokeHalf = 1.5 / 2;
const glassGapX = outerRx - innerRx - strokeHalf;
const glassGapY = outerRy - innerRy - strokeHalf;
const tubeRightGap = (12.2 - strokeHalf) - 9.75;
const tubeLeftGap = 7.25 - (4.8 + strokeHalf);
assert.ok(glassGapX >= 1.5 && glassGapY >= 1.5, "visible dark air around fluid");
assert.ok(Math.abs(glassGapX - glassGapY) < 0.2, "radial inset stays balanced");
assert.ok(Math.abs(glassGapX - tubeRightGap) < 0.25, "tube/bulb right clearance");
assert.ok(Math.abs(tubeRightGap - tubeLeftGap) < 0.01, "tube voids mirrored");
assert.ok(cx - outerRx - strokeHalf >= 1, "left bulb does not clip");
assert.ok(cx + outerRx + strokeHalf <= width - 1, "right bulb does not clip");
assert.ok(cy + outerRy + strokeHalf < height, "bottom curve fits inside gauge");
assert.match(dock, /control2X:\s*weatherThermometer\.outerRightJoinX - 0\.58/);
assert.match(dock, /control1X:\s*weatherThermometer\.outerLeftJoinX \+ 0\.58/);
assert.match(dock, /control2X:\s*weatherThermometer\.innerRightJoinX - 0\.55/);
assert.match(dock, /control1X:\s*weatherThermometer\.innerLeftJoinX \+ 0\.55/);

// Measurement marks belong to the right of the tube, not over its liquid.
const tickStart = dock.lastIndexOf("Repeater {");
const ticks = dock.slice(tickStart, tickStart + 400);
assert.match(ticks, /x:\s*13\.2/);
assert.match(ticks, /width:\s*index % 2 === 0 \? 2\.5 : 1\.8/);
assert.ok(13.2 > 12.2 + strokeHalf);
assert.ok(13.2 + 2.5 < width);

// The real normalized level drives a vertical gradient through one connected
// inner tube+bulb path, rather than a permanently filled decorative bulb.
assert.match(dock, /readonly property real fillStart:[\s\S]*?1 - animatedLevel/);
assert.match(dock, /fillGradient:\s*LinearGradient\s*\{/);
assert.match(dock, /position:\s*weatherThermometer\.fillStart[\s\S]*?color:\s*weatherThermometer\.liquidColor/);
assert.match(dock, /visible:\s*weatherThermometer\.animatedLevel > 0/);
assert.doesNotMatch(dock, /id:\s*glassBulb/);
assert.doesNotMatch(dock, /id:\s*liquidBulb/);
// Scale marks are ordinary QML rectangles inside the tube and use exactly the
// same glass color and opacity as the outline.
assert.match(dock, /readonly property color glassColor:\s*Colors\.white/);
assert.match(dock, /readonly property real glassOpacity:\s*1\.0/);
assert.match(dock, /Repeater\s*\{\s*model:\s*4[\s\S]*?delegate:\s*Rectangle\s*\{[\s\S]*?color:\s*weatherThermometer\.glassColor[\s\S]*?opacity:\s*weatherThermometer\.glassOpacity/);
assert.match(dock, /Behavior on animatedLevel[\s\S]*?NumberAnimation\s*\{[\s\S]*?duration:\s*300/);
assert.match(dock, /Behavior on liquidColor[\s\S]*?ColorAnimation\s*\{\s*duration:\s*300/);
assert.match(dock, /WeatherDockPolicy\.temperatureState\(/);
assert.match(dock, /if \(!thermometerState\.valid\)[\s\S]*?return "transparent"/);
assert.match(dock, /if \(weatherDock\.open\)[\s\S]*?return Colors\.magenta/);
assert.match(dock, /property bool useCelsius:\s*false/);
assert.match(dock, /onRightClicked:\s*\{\s*useCelsius\s*=\s*!useCelsius;/);
assert.match(dock, /WeatherDockPolicy\.formatTemperature\([\s\S]*?weatherFresh,[\s\S]*?useCelsius/);
assert.match(dock, /id:\s*weatherConditionSlot[\s\S]*?implicitHeight:\s*46/);
assert.match(dock, /id:\s*weatherCondition[\s\S]*?text:\s*weatherDock\.weatherState\.icon[\s\S]*?font\.pixelSize:\s*42/);
assert.match(dock, /id:\s*weatherTemperatureValue[\s\S]*?text:\s*weatherDock\.temperatureLabel\.slice\(0, -2\)[\s\S]*?font\.pixelSize:\s*20/);
assert.match(dock, /id:\s*weatherTemperatureUnit[\s\S]*?text:\s*weatherDock\.temperatureLabel\.slice\(-1\)[\s\S]*?font\.pixelSize:\s*20/);
assert.match(dock, /id:\s*weatherDegree[\s\S]*?text:\s*"°"[\s\S]*?font\.pixelSize:\s*20[\s\S]*?color:\s*weatherDock\.open\s*\?\s*Colors\.magenta[\s\S]*?weatherDock\.pressed\s*\?\s*Colors\.white[\s\S]*?weatherDock\.hovered\s*\?\s*Colors\.orange\s*:\s*Colors\.white/);
assert.match(dock, /SafeDropShadow\s*\{[^}]*safeSource:\s*weatherDegree[^}]*color:\s*weatherDock\.open\s*\|\|\s*weatherDock\.pressed\s*\?\s*Colors\.magenta\s*:\s*Colors\.orange/s);
assert.match(dock, /id:\s*weatherContent[\s\S]*?anchors\.centerIn:\s*parent[\s\S]*?spacing:\s*6/);
assert.doesNotMatch(dock, /anchors\.horizontalCenterOffset:\s*2/);
assert.match(dock, /id:\s*weatherReadout[\s\S]*?spacing:\s*0/);
assert.match(dock, /id:\s*weatherTemperature[\s\S]*?spacing:\s*0/);
assert.match(dock, /contentGlowSource:\s*weatherContent/);
assert.match(dock, /opacity:\s*weatherDock\.contentGlowOpacity/);
assert.match(dock, /pressedContentGlowColor:\s*Colors\.magenta/);
assert.match(dock, /pressedDockGlowColor:\s*Colors\.magenta/);
assert.match(dock, /openForegroundColor:\s*Colors\.magenta/);
assert.match(dock, /openGlowColor:\s*Colors\.magenta/);
assert.match(dock, /pressedForegroundColor:\s*weatherColor/);
assert.match(dock, /implicitWidth:\s*Math\.ceil\(weatherContent\.implicitWidth\)\s*\+\s*6/);
// Idle uses observed weather colors; interaction takes the standard orange -> magenta path.
for (const [property, color] of [
    ["normalForegroundColor", "weatherColor"],
    ["normalContentGlowColor", "weatherColor"],
    ["normalDockGlowColor", "weatherColor"],
    ["hoverForegroundColor", "Colors.orange"],
    ["hoverContentGlowColor", "Colors.orange"],
    ["hoverDockGlowColor", "Colors.orange"],
    ["pressedForegroundColor", "weatherColor"],
    ["pressedContentGlowColor", "Colors.magenta"],
    ["pressedDockGlowColor", "Colors.magenta"],
    ["openForegroundColor", "Colors.magenta"],
    ["openGlowColor", "Colors.magenta"],
    ["openFillColor", "Colors.yellow"]
]) {
    assert.ok(dock.includes(property + ": " + color), property + " should use " + color);
}
assert.match(dock, /property color liquidColor:\s*weatherDock\.thermometerLiquidColor/);
assert.match(dock, /id:\s*weatherContent[\s\S]*?spacing:\s*6/);
assert.ok(dock.indexOf("id: weatherCondition") < dock.indexOf("id: weatherTemperature"));
assert.ok(dock.indexOf("id: weatherTemperature") < dock.indexOf("id: weatherThermometer"));
assert.ok(dock.indexOf("id: weatherTemperatureUnit") < dock.indexOf("id: weatherThermometer"));
assert.match(dock, /WeatherDockPolicy\.classify/);
assert.doesNotMatch(dock, /\bProcess\s*\{/);
assert.match(shell, /Weather\s*\{[^}]*weatherService:\s*weatherService/s);

console.log("Weather dock live state contracts: PASS");
