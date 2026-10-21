#!/usr/bin/env node
"use strict";

// Weather Station palette contract after domain separation. This pass protects
// semantic identities and telemetry severity colors while layout polish remains
// intentionally deferred.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");

function read(relative) {
    return fs.readFileSync(path.join(root, relative), "utf8");
}

const windowSource = read("widgets/weather/WeatherStationW.qml");
const homeSource = read("widgets/weather/StationHome.qml");
const groundSource = read("widgets/weather/StationGround.qml");
const skySource = read("widgets/weather/StationSky.qml");
const spaceSource = read("widgets/weather/StationSpace.qml");

const mainHeaderStart = windowSource.indexOf("id: header");
const mainHeaderEnd = windowSource.indexOf("// NAVIGATION", mainHeaderStart);
assert.ok(mainHeaderStart >= 0 && mainHeaderEnd > mainHeaderStart);
const header = windowSource.slice(mainHeaderStart, mainHeaderEnd);
assert.match(
    header,
    /text: "✦ WEATHER STATION ✦"[\s\S]*?color: Colors\.magenta/
);
assert.match(header, /height: 2\s+color: Colors\.magenta/);
assert.match(header, /border\.color: weatherStation\.sourceStatusColor/);
assert.match(header, /accentColor: Colors\.red/);

// HOME no longer owns the three domains.
for (const title of ["⌁  GROUND", "☁  SKY", "✦  SPACE"])
    assert.ok(!homeSource.includes(title), "HOME still contains " + title);
assert.ok(homeSource.includes("FAVORITES // RELEVANT // AUTO"));

// Stable domain identities survive the structural split.
assert.match(groundSource, /text: "⌁  GROUND"[\s\S]*?color: Colors\.green/);
assert.match(skySource, /text: "☁  SKY"[\s\S]*?color: Colors\.cyan/);
assert.match(spaceSource, /text: "✦  SPACE"[\s\S]*?color: Colors\.magenta/);

// Existing semantic telemetry severity remains independent from page identity.
assert.match(groundSource, /readonly property color aqiColor:/);
for (const color of ["cyan", "yellow", "orange", "red"])
    assert.ok(groundSource.includes("Colors." + color));

for (const property of ["kpColor", "solarWindColor", "bzColor"])
    assert.ok(spaceSource.includes("readonly property color " + property));
for (const color of ["cyan", "yellow", "orange", "red"])
    assert.ok(spaceSource.includes("Colors." + color));

// Current weather content remains on SKY rather than being lost in the split.
for (const token of [
    "weatherService.tempF",
    "weatherService.feelsLikeF",
    "weatherService.condition",
    "weatherService.humidity",
    "weatherService.windMph",
])
    assert.ok(skySource.includes(token), token);

console.log("Weather Station domain palette contracts: PASS");
