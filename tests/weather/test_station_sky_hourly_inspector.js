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
const details = load("widgets/weather/StationSkyHourlyPolicy.js");
const data = load("services/weather/WeatherDataPolicy.js");
const qml = fs.readFileSync(path.join(root, "widgets/weather/StationSky.qml"), "utf8");

const payload = {
    weather: [{
        date: "2026-10-27", maxtempF: "67", mintempF: "42",
        astronomy: [{sunrise: "07:30 AM", sunset: "06:15 PM",
                     moon_phase: "Waning Gibbous", moon_illumination: "98"}],
        hourly: [{
            time: "2100", tempF: "55", FeelsLikeF: "50", DewPointF: "44",
            humidity: "70", windspeedMiles: "12", winddir16Point: "NW",
            pressure: "1012", visibilityMiles: "8", cloudcover: "40",
            precipMM: "0.5", chanceofrain: "40", chanceofsnow: "0",
            uvIndex: "0", weatherCode: "116",
            weatherDesc: [{value: "Partly cloudy"}]
        },{
            time: "0", tempF: "-5", FeelsLikeF: "-9", DewPointF: "-14",
            humidity: "", windspeedMiles: "", winddir16Point: "",
            pressure: "", visibilityMiles: "", cloudcover: "",
            precipMM: "", chanceofrain: "", chanceofsnow: "",
            uvIndex: "", weatherCode: "113",
            weatherDesc: [{value: "Clear"}]
        }]
    }]
};
const parsed = data.parseForecast(payload, {localObsDateTime:"2026-10-27 06:00 PM"}, 6);
assert.equal(parsed.hourly.length, 1);
const first = parsed.hourly[0];
assert.equal(details.selectedHour(parsed.hourly, 0).timeLabel, "9 PM");
assert.equal(details.selectedHour(parsed.hourly, -4), first);
assert.equal(details.selectedHour(parsed.hourly, 90), first);
assert.equal(details.selectedHour([], 0), null);
assert.equal(details.hourlyMetrics(null).length, 0);
assert.match(details.hourCaption(first), /2026-10-27 \/\/ 9 PM \/\/ PARTLY CLOUDY/);

const metrics = Object.fromEntries(Array.from(
    details.hourlyMetrics(first), item => [item.title, item.value]
));
assert.equal(Object.keys(metrics).length, 11);
assert.equal(metrics["FEELS LIKE"], "50°F");
assert.equal(metrics["DEW POINT"], "44°F");
assert.equal(metrics.HUMIDITY, "70%");
assert.equal(metrics.WIND, "12 MPH // NW");
assert.equal(metrics.PRESSURE, "1012 hPa");
assert.equal(metrics.VISIBILITY, "8.0 mi");
assert.equal(metrics["CLOUD COVER"], "40%");
assert.equal(metrics.PRECIP, "0.5 mm");
assert.equal(metrics["RAIN CHANCE"], "40%");
assert.equal(metrics["SNOW CHANCE"], "0%");
assert.equal(metrics["UV INDEX"], "0");

// Missing values cannot silently become zero or favorable weather.
const absent = details.hourlyMetrics({
    feelsLikeF: -999, dewPointF: "", humidity: null, windMph: "",
    windDirection: "N", pressureHpa: null, visibilityMiles: -1,
    cloudCover: undefined, precipMm: -1, chanceRain: -1,
    chanceSnow: undefined, uvIndex: ""
});
assert.ok(absent.every(item => item.value === "--"), "missing readings are --");
assert.equal(details.windText(6, "unsafe text / other"), "6 MPH");
assert.equal(details.windText("oops", "N"), "--");
assert.equal(details.reading(-9, -900, 200, 0, "°F"), "-9°F");
assert.equal(details.reading(150, 0, 100, 0, "%"), "--");
assert.equal(details.hourCaption(null), "NO HOURLY FORECAST AVAILABLE");

// Presentation is a single-click selection over already parsed data.
assert.match(qml, /import "StationSkyHourlyPolicy\.js" as HourlyDetails/);
assert.match(qml, /readonly property var inspectedHour:/);
assert.match(qml, /HourlyDetails\.selectedHour\(hourlyForecast, inspectedHourIndex\)/);
assert.match(qml, /property int inspectedHourIndex: -1/);
assert.match(qml, /onHourlyForecastChanged: inspectedHourIndex = -1/);
assert.match(qml, /readonly property var inspectedHour: inspectedHourIndex >= 0/);
assert.match(qml, /TapHandler\s*\{\s*onTapped: sky\.inspectedHourIndex = index/);
assert.match(qml, /ActionButton\s*\{[\s\S]*?id: inspectorClose[\s\S]*?label: "X"[\s\S]*?onClicked: sky\.inspectedHourIndex = -1/);
assert.match(qml, /model: sky\.inspectedHourMetrics/);
assert.match(qml, /FORECAST, NOT OBSERVED/);
assert.match(qml, /visible: sky\.inspectedHour !== null/);
// Prevent the actual failure: implicit-height forecast delegates cannot
// own an anchors.fill MouseArea that loops back to their own height.
// Pointer handlers aren't positioned children and preserve the old artwork.
const nextHours = qml.indexOf('title: "FORECAST // NEXT HOURS"');
const inspectorHeader = qml.indexOf('title: "HOURLY // INSPECT SELECTED FORECAST"');
assert.ok(nextHours > 0 && inspectorHeader > nextHours);
const cards = qml.slice(nextHours, inspectorHeader);
assert.match(cards, /Row\s*\{\s*spacing:\s*10\s*Repeater/);
assert.match(cards, /model:\s*sky\.hourlyForecast/);
assert.match(cards, /delegate: Column\s*\{\s*required property var modelData\s*required property int index/);
assert.match(cards, /height:\s*74/);
assert.match(cards, /font\.pixelSize:\s*80/);
assert.match(cards, /WeatherCelestialGlyph\s*\{/);
assert.match(cards, /RAIN /);
assert.doesNotMatch(cards, /MouseArea\s*\{[\s\S]*?anchors\.fill:\s*parent/);
assert.match(cards, /HoverHandler\s*\{\s*cursorShape:\s*Qt\.PointingHandCursor/);
// The inspector is a sibling after cards, not a replacement. It must
// remain dismissible and preserve daily weather underneath.
assert.match(qml, /visible: sky\.inspectedHour !== null/);
assert.match(qml, /inspectorClose\.left/);
assert.match(qml, /NeonScrollBar\s*\{/);
assert.match(qml, /title: "FORECAST \/\/ DAILY"/);
assert.match(qml, /title: "FORECAST \/\/ NEXT HOURS"/);
assert.doesNotMatch(qml, /HourlyDetails\.(?:fetch|refresh|request)/);
console.log("SKY hourly inspector existing-data, missing-field and selection contracts: PASS");
