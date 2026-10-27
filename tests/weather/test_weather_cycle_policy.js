#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(path.join(root, "services/weather/WeatherCyclePolicy.js"), "utf8")
                 .replace(/^\.pragma library\s*/m, "");
const context = {};
vm.runInNewContext(source, context);

const today = {date: "2026-10-26", sunrise: "07:20 AM", sunset: "06:10 PM",
               moonPhase: "Waxing Crescent", moonIllumination: 24};
const tomorrow = {date: "2026-10-27", sunrise: "07:21 AM", sunset: "06:09 PM",
                  moonPhase: "First Quarter", moonIllumination: 50};
const daily = [today, tomorrow];

function at(time) {
    const h = Math.floor(time / 60), m = time % 60;
    const value = "2026-10-26 " + String(h).padStart(2, "0")
                  + ":" + String(m).padStart(2, "0");
    return context.atObservation(1000000, value, 1000000, daily);
}
assert.equal(at(6 * 60 + 49).solar, "night");
assert.equal(at(6 * 60 + 50).solar, "dawn");
assert.equal(at(7 * 60 + 19).solar, "dawn");
assert.equal(at(7 * 60 + 20).solar, "day");
assert.equal(at(18 * 60 + 9).solar, "day");
assert.equal(at(18 * 60 + 10).solar, "dusk");
assert.equal(at(18 * 60 + 39).solar, "dusk");
assert.equal(at(18 * 60 + 40).solar, "night");
assert.equal(at(4 * 60).moonPhase, "waxing-crescent");
assert.equal(at(4 * 60).moonIllumination, 24);
assert.equal(context.clockMinute("12:00 AM"), 0);
assert.equal(context.clockMinute("12:00 PM"), 720);
assert.equal(context.clockMinute("11:59 PM"), 1439);
assert.equal(context.clockMinute("--"), -1);
assert.equal(context.clockMinute("23:00 AM"), -1);
assert.ok(Number.isNaN(context.observationEpoch("2026-02-30 05:20 PM")));
assert.ok(Number.isNaN(context.observationEpoch("2026-10-26 26:20")));
assert.ok(Number.isNaN(context.observationEpoch("")));
assert.equal(context.atObservation(1000000, "", 1000000, daily).solar, "unknown");
assert.equal(context.atObservation(1000000, "2026-10-26 04:20 AM", 0, daily).solar, "unknown");
assert.equal(context.atObservation(1000000 + 3700000, "2026-10-26 04:20 AM", 1000000, daily).solar, "unknown");
assert.equal(context.atObservation(1000000 - 400000, "2026-10-26 04:20 AM", 1000000, daily).solar, "unknown");
assert.equal(context.atLocal("2026-10-26", 720, [{date: "2026-10-26", sunrise: "--", sunset: "--"}]).solar, "unknown");
assert.equal(context.atLocal("2026-10-26", 720, [{date: "2026-10-26", sunrise: "10:00 PM", sunset: "06:00 AM"}]).solar, "unknown");
assert.equal(context.atLocal("2026-10-30", 720, daily).moonPhase, "unknown");
// The provider-local time, not the PC zone, drives day/night boundaries.
assert.equal(context.atObservation(1000000, "2026-10-26 06:49 AM", 1000000, daily).solar, "night");
assert.equal(context.atObservation(1000000 + 60000, "2026-10-26 06:49 AM", 1000000, daily).solar, "dawn");
// Advance safely across the provider's date boundary.
assert.equal(context.atObservation(1000000 + 20 * 60000,
             "2026-10-26 11:50 PM", 1000000, daily).date, "2026-10-27");
assert.equal(context.atObservation(1000000 + 20 * 60000,
             "2026-10-26 11:50 PM", 1000000, daily).moonPhase, "first-quarter");

for (const [name, token] of [
    ["New Moon", "new"], ["Waxing Crescent", "waxing-crescent"],
    ["First Quarter", "first-quarter"], ["Waxing Gibbous", "waxing-gibbous"],
    ["Full Moon", "full"], ["Waning Gibbous", "waning-gibbous"],
    ["Last Quarter", "last-quarter"], ["Waning Crescent", "waning-crescent"]
])
    assert.equal(context.normalizedPhase(name), token);
assert.equal(context.normalizedPhase("Third Quarter"), "last-quarter");
assert.equal(context.normalizedPhase(""), "unknown");
assert.equal(context.atLocal("2026-10-26", 1200, [{...today, moonIllumination: -1}]).moonIllumination, -1);
assert.equal(context.atLocal("2026-10-26", 1200, [{...today, moonIllumination: 120}]).moonIllumination, -1);

assert.equal(context.forecast("2026-10-26", "600", daily).solar, "night");
assert.equal(context.forecast("2026-10-26", "900", daily).solar, "day");
assert.equal(context.forecast("2026-10-26", "2100", daily).solar, "night");
assert.equal(context.forecast("2026-10-26", "2500", daily).solar, "unknown");
assert.equal(context.forecast("2026-10-26", null, daily).solar, "unknown");

function state(label) { return { label: label, color: "orange", icon: "☀︎" }; }
for (const [label, kind] of [
    ["SUNNY / CLEAR", "clear"], ["PARTLY SUNNY", "cloud"],
    ["CLOUDS / FOG", "cloud"], ["RAIN", "rain"],
    ["SNOW / SLEET", "snow"], ["HAIL / ICE PELLETS", "hail"],
    ["THUNDERSTORM", "storm"], ["HIGH WIND // 28 MPH", "wind"],
    ["VERY HIGH UV 9", "none"], ["UNHEALTHY AIR // AQI 180", "none"],
    ["WEATHER UNAVAILABLE", "none"], ["UNKNOWN CONDITION", "none"]
]) {
    assert.equal(context.nightKind(state(label)), kind, label);
    assert.equal(context.artworkFor(state(label), {solar: "night"}),
                 kind === "none" ? "weather" : "night-weather", label);
}
assert.equal(context.artworkFor(state("SUNNY / CLEAR"), {solar:"day"}), "sun");
assert.equal(context.artworkFor(state("SUNNY / CLEAR"), {solar:"dawn"}), "sun");
assert.equal(context.artworkFor(state("SUNNY / CLEAR"), {solar:"dusk"}), "sun");
assert.equal(context.artworkFor(state("PARTLY SUNNY"), {solar:"day"}), "sun-cloud");
assert.equal(context.artworkFor(state("RAIN"), {solar:"day"}), "weather");
assert.equal(context.artworkFor(state("SUNNY / CLEAR"), {solar:"unknown"}), "weather");

const icon = fs.readFileSync(path.join(root, "components/WeatherCelestialGlyph.qml"), "utf8");
assert.match(icon, /import QtQuick\.Shapes/);
assert.match(icon, /ShapePath\s*\{/);
assert.match(icon, /PathArc\s*\{/);
assert.match(icon, /PathCubic\s*\{/);
assert.match(icon, /moonPhase === "full"/);
assert.match(icon, /moonPhase === "first-quarter"/);
assert.match(icon, /moonPhase === "last-quarter"/);
assert.match(icon, /property color ink: "white"/);
assert.doesNotMatch(icon, /🌕|🌗|🌒|✴|✦|✶/);
assert.doesNotMatch(icon, /ColorAnimation|NumberAnimation|Timer|ShaderEffect/);

// Both QML consumers import the components directory by path. Its explicit
// qmldir manifest must register new types, or Quickshell aborts shell startup
// with "WeatherCelestialGlyph is not a type" even if the .qml file exists.
const componentManifest = fs.readFileSync(path.join(root, "components/qmldir"), "utf8");
assert.match(componentManifest, /^WeatherCelestialGlyph\s+1\.0\s+WeatherCelestialGlyph\.qml\s*$/m);

const service = fs.readFileSync(path.join(root, "services/weather/WeatherService.qml"), "utf8");
const dock = fs.readFileSync(path.join(root, "modules/Weather.qml"), "utf8");
const sky = fs.readFileSync(path.join(root, "widgets/weather/StationSky.qml"), "utf8");
assert.match(service, /localObservationDateTime = String\(current\.localObsDateTime \|\| ""\)/);
assert.match(service, /localObservationAnchorMs = Date\.now\(\)/);
assert.match(dock, /^import "\.\.\/components"$/m);
assert.match(sky, /^import "\.\.\/\.\.\/components"$/m);
assert.match(dock, /WeatherCelestialGlyph\s*\{/);
assert.match(sky, /WeatherCelestialGlyph\s*\{/);
assert.match(dock, /WeatherCyclePolicy\.atObservation/);
assert.match(dock, /WeatherCyclePolicy\.artworkFor\(weatherState, skyCycle\)/);
assert.match(dock, /moonPhase: weatherDock\.skyCycle\.moonPhase/);
assert.match(dock, /ink: weatherDock\.foregroundColor/);
assert.match(dock, /id:\s*weatherThermometer/);
assert.match(dock, /normalDockGlowColor:\s*weatherColor/);
assert.match(sky, /WeatherCyclePolicy\.atObservation/);
assert.match(sky, /WeatherCyclePolicy\.forecast/);
assert.match(sky, /WeatherCyclePolicy\.atLocal/);
assert.match(sky, /WeatherCyclePolicy\.normalizedPhase\(modelData\.moonPhase\)/);
assert.match(sky, /mode: sky\.currentCelestialMode/);
assert.doesNotMatch(dock + sky, /Colors\.dawn|Colors\.dusk|Colors\.moon|Colors\.night/);
// Night rendering contract: illuminated phase = *weather* ink; shadow =
// shared dark purple; atmosphere = magenta. The glow does not overwrite the
// storm/UV/wind/rain semantic colors or change the actual phase geometry.
assert.match(icon, /import QtQuick\.Effects/);
assert.match(icon, /property color shadowInk:\s*Colors\.dark/);
assert.match(icon, /property color nightHalo:\s*Colors\.magenta/);
assert.match(icon, /nightGlowEnabled:[\s\S]*?solar === "night" && moonVisible/);
assert.match(icon, /RectangularShadow\s*\{[\s\S]*?color:\s*glyph\.nightHalo[\s\S]*?visible:\s*glyph\.nightGlowEnabled/);
assert.match(icon, /color:\s*glyph\.moonPhase === "full" \? glyph\.ink : glyph\.shadowInk/);
assert.match(icon, /ShapePath\s*\{[\s\S]*?fillColor:\s*glyph\.ink/);
assert.doesNotMatch(icon, /ColorAnimation|NumberAnimation|ShaderEffect|moonPhase.*Colors\./);

// Canonical moon geometry has one origin. Its lunar body moves upper-left
// inside a shared 40x40 scene, never by weather type or per-consumer anchor.
assert.match(icon, /nightComposition: mode === "night-weather"/);
assert.match(icon, /moonVisible:[\\s\\S]*?nightComposition/);
assert.match(icon, /x: glyph\\.nightComposition \\? -4 : 0/);
assert.match(icon, /y: glyph\\.nightComposition \\? -5 : 0/);
assert.match(icon, /readonly property bool foregroundCloud: nightComposition/);
assert.match(icon, /visible: glyph\\.foregroundCloud[\\s\\S]*?fillColor: glyph\\.ink/);
const lunarStart = icon.indexOf('id: lunarBody');
const filledCloud = icon.indexOf('// A FILLED foreground cloud');
assert.ok(lunarStart > 0 && filledCloud > lunarStart);
assert.match(icon.slice(lunarStart, filledCloud), /moonPhase === "full"/);
assert.match(icon.slice(filledCloud), /PathCubic/);
for (const kind of ["rain", "snow", "hail", "storm", "wind"])
    assert.match(icon, new RegExp('weatherKind === "' + kind + '"'));
assert.doesNotMatch(icon, /anchors\\.right: parent\\.right/);
const dockConditionArea = dock.slice(dock.indexOf("id: weatherConditionSlot"),
                                    dock.indexOf("id: weatherReadout"));
assert.match(dockConditionArea, /id:\\s*dockWeatherArt/);
assert.match(dockConditionArea, /weatherKind: WeatherCyclePolicy\\.nightKind\\(weatherDock\\.weatherState\\)/);
assert.match(dockConditionArea, /mode: weatherDock\\.celestialMode/);
assert.match(dockConditionArea, /ink: weatherDock\\.foregroundColor/);
assert.doesNotMatch(dockConditionArea, /dockNightMoon|anchors\\.top: parent\\.top|anchors\\.right: parent\\.right/);
const currentArea = sky.slice(sky.indexOf("id: conditionIconGlyph"),
                              sky.indexOf('text: "AIR QUALITY"'));
assert.match(currentArea, /weatherKind: WeatherCyclePolicy\\.nightKind\\(sky\\.conditionState\\)/);
assert.match(currentArea, /mode: sky\\.currentCelestialMode/);
assert.match(currentArea, /ink: sky\\.iconColor\\(sky\\.conditionState\\.color\\)/);
assert.doesNotMatch(currentArea, /currentNightMoon|anchors\\.top: parent\\.top|anchors\\.right: parent\\.right/);
const hourlyArea = sky.slice(sky.indexOf('title: "FORECAST // NEXT HOURS"'),
                             sky.indexOf('title: "FORECAST // DAILY"'));
assert.match(hourlyArea, /weatherKind: WeatherCyclePolicy\\.nightKind\\(parent\\.forecastState\\)/);
assert.match(hourlyArea, /mode: parent\\.forecastArt/);
assert.match(hourlyArea, /ink: sky\\.iconColor\\(parent\\.forecastState\\.color\\)/);
assert.doesNotMatch(hourlyArea, /anchors\\.top: parent\\.top[\\s\\S]*?mode: "moon"/);
// Daily lunar phase information remains separate from daily weather art.
// No new color vocabulary or clock mechanism is introduced by this patch.
assert.match(sky, /WeatherCyclePolicy\\.normalizedPhase\\(modelData\\.moonPhase\\)/);

console.log("Weather solar/lunar policy and QML wiring: PASS");
