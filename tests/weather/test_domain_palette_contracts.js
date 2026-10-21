#!/usr/bin/env node
"use strict";

// Weather Station palette contract: presentation changes must not affect
// raw telemetry, meter scaling, or risk-level text.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const windowSource = fs.readFileSync(
    path.join(root, "widgets/weather/WeatherStationW.qml"), "utf8");
const homeSource = fs.readFileSync(
    path.join(root, "widgets/weather/StationHome.qml"), "utf8");

const mainHeaderStart = windowSource.indexOf("id: header");
const mainHeaderEnd = windowSource.indexOf("// NAVIGATION", mainHeaderStart);
assert.ok(mainHeaderStart >= 0 && mainHeaderEnd > mainHeaderStart);
const header = windowSource.slice(mainHeaderStart, mainHeaderEnd);
assert.match(header, /text: "✦ WEATHER STATION ✦"[\s\S]*?color: Colors\.magenta/);
assert.match(header, /height: 2\s+color: Colors\.magenta/);
// Keep functional status and destructive controls independent.
assert.match(header, /border\.color: weatherStation\.sourceStatusColor/);
assert.match(header, /accentColor: Colors\.red/);

const markers = ["id: spaceBand", "id: skyBand", "id: groundBand"];
const positions = markers.map(x => homeSource.indexOf(x));
assert.ok(positions[0] >= 0 && positions[0] < positions[1]
          && positions[1] < positions[2]);
const areas = [
    homeSource.slice(positions[0], positions[1]),
    homeSource.slice(positions[1], positions[2]),
    homeSource.slice(positions[2])
];

const specs = [
    { name: "space", accent: "magenta",
      title: "✦  SPACE", meters: ["kp", "solarWind", "bz", "solarFlux"] },
    { name: "sky", accent: "cyan",
      title: "☁  SKY", meters: ["temperature", "aqi", "humidity", "wind"] },
    { name: "ground", accent: "green",
      title: "⌁  GROUND", meters: ["aqi", "pm25", "pm10"] }
];

for (let i = 0; i < specs.length; i++) {
    const {name, accent, title, meters} = specs[i];
    const section = areas[i], id = name + "Band";
    assert.ok(section.includes("readonly property color accentColor: Colors." + accent));
    // Identity is stable across pointer hover and current domain selection.
    assert.ok(section.includes('text: "' + title + '"'));
    const heading = section.slice(section.indexOf('text: "' + title + '"'),
                                  section.indexOf('text: "' + title + '"') + 260);
    assert.ok(heading.includes("color: " + id + ".accentColor"), name + " title");
    assert.ok(section.slice(0, section.indexOf("id: " + name + "Title"))
                     .includes("color: " + id + ".accentColor"), name + " left marker");
    assert.equal(section.split("border.color: " + id + ".accentColor").length - 1,
                 meters.length, name + " meter outlines");
    for (const meter of meters) {
        const location = "width: (parent.width - 4) * home." + meter + "Meter";
        const start = section.indexOf(location);
        assert.ok(start >= 0 && section.indexOf(location, start + 1) === -1,
                  name + "/" + meter + " unique meter");
        const fill = section.slice(start, start + 160);
        assert.ok(fill.includes("color: " + id + ".accentColor"),
                  name + "/" + meter + " fill");
    }
    assert.ok(section.includes("safeSource: " + id));
    assert.ok(section.includes("color: " + id + ".accentColor"),
              name + " selected glow");
}

// Semantic severity of source telemetry stays independent of domain accents.
assert.match(areas[0], /color: home\.kpColor/);
assert.match(areas[0], /color: home\.solarWindColor/);
assert.match(areas[0], /color: home\.bzColor/);
assert.match(areas[1], /color: home\.aqiColor/);
assert.match(areas[2], /color: home\.aqiColor/);
assert.match(homeSource, /readonly property real aqiMeter:\s*Math\.max/);
assert.match(homeSource, /readonly property real kpMeter:\s*Math\.max/);

console.log("Weather Station domain palette contracts: PASS");
