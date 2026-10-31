#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const policySource = read("services/weather/SeismicPolicy.js");
const ctx = {Date, Math, Number, String, Array, Object, JSON, isFinite, isNaN};
vm.runInNewContext(
    policySource.replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "parseFeed", "distanceKm", "formatUtc", "depthBand",
    "magnitudeRadius", "recentRows"
]) {
    assert.equal(typeof ctx[fn], "function", fn);
}

const now = Date.UTC(2026, 9, 31, 20, 0, 0);
const features = [];
for (let i = 0; i < 8; i++) {
    features.push({
        type: "Feature",
        id: "quake-" + i,
        properties: {
            mag: 2.5 + i * 0.5,
            place: "Example " + i,
            time: now - i * 60000,
            updated: now - i * 30000,
            sig: 100 + i,
            tsunami: i === 1 ? 1 : 0,
            status: "reviewed",
            alert: i === 1 ? "yellow" : null,
            magType: "mww",
            type: "earthquake"
        },
        geometry: {
            type: "Point",
            coordinates: [-77 + i, 38 - i, i === 0 ? 12 : i === 1 ? 120 : 350]
        }
    });
}
features.push({
    type: "Feature",
    id: "too-small",
    properties: {
        mag: 2.0, place: "small", time: now,
        type: "earthquake"
    },
    geometry: {type:"Point", coordinates:[0,0,5]}
});
features.push({
    type: "Feature",
    id: "not-quake",
    properties: {
        mag: 4.0, place: "blast", time: now,
        type: "quarry blast"
    },
    geometry: {type:"Point", coordinates:[0,0,5]}
});

const parsed = Array.from(ctx.parseFeed({
    type: "FeatureCollection",
    features
}, 100));
assert.equal(parsed.length, 8);
assert.equal(parsed[0].id, "quake-0");
assert.equal(parsed[0].magnitude, 2.5);
assert.equal(parsed[0].significance, 100);
assert.equal(parsed[0].status, "reviewed");
assert.equal(parsed[0].magType, "mww");
assert.equal(parsed[1].tsunami, true);
assert.equal(parsed[1].alert, "yellow");
assert.equal(parsed[1].depthKm, 120);
assert.equal(parsed[7].depthKm, 350);

assert.equal(ctx.depthBand(12).id, "shallow");
assert.equal(ctx.depthBand(70).id, "intermediate");
assert.equal(ctx.depthBand(299).id, "intermediate");
assert.equal(ctx.depthBand(300).id, "deep");
assert.equal(ctx.depthBand(-1).id, "unknown");

assert.equal(ctx.magnitudeRadius(2.5), 4);
assert.ok(ctx.magnitudeRadius(5) > ctx.magnitudeRadius(3));
assert.equal(ctx.magnitudeRadius(20), 10);
assert.equal(Array.from(ctx.recentRows(parsed, 3)).length, 3);

const service = read("services/weather/SeismicService.qml");
assert.match(
    service,
    /earthquake\.usgs\.gov\/earthquakes\/feed\/v1\.0\/summary\/2\.5_day\.geojson/
);
assert.match(service, /SeismicPolicy\.parseFeed\(JSON\.parse\(raw\), 100\)/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 1);
assert.match(service, /interval:\s*900000/);

const station = read("widgets/weather/WeatherStationW.qml");
assert.equal(
    (station.match(/WeatherServices\.SeismicService\s*\{/g) || []).length,
    1
);
assert.match(
    station,
    /active: weatherStation\.menuOpen[\s\S]*?currentView === "ground"[\s\S]*?currentView === "map"/
);
assert.match(
    station,
    /StationGround\s*\{[\s\S]*?seismicSource: seismicService/
);
assert.match(
    station,
    /StationDiscovery\s*\{[\s\S]*?domain: "map"[\s\S]*?seismicSource: seismicService/
);

const ground = read("widgets/weather/StationGround.qml");
assert.match(ground, /property var seismicSource: null/);
assert.match(
    ground,
    /SeismicPolicy\.recentRows\(seismicSource\.events, 3\)/
);
assert.doesNotMatch(ground, /WeatherServices\.SeismicService\s*\{/);
assert.doesNotMatch(ground, /\bid:\s*quakeService\b/);
assert.match(ground, /model: ground\.recentSeismicEvents/);
assert.match(ground, /NOT AN EARTHQUAKE WARNING/);

const map = read("widgets/weather/StationDiscovery.qml");
assert.match(
    map,
    /import "\.\.\/\.\.\/services\/weather\/SeismicPolicy\.js" as SeismicPolicy/
);
assert.match(map, /property var seismicSource: null/);
assert.match(map, /property var selectedMapEarthquake: null/);
assert.match(map, /property bool mapShowEarthquakes: true/);
assert.match(
    map,
    /MapProjection\.plottable\(seismicSource\.events\)/
);
assert.match(map, /label: "EARTHQUAKES: "/);
assert.match(map, /SIZE=MAGNITUDE \/\/ COLOR=DEPTH/);
assert.match(map, /model: stationDiscovery\.mapEarthquakeRows/);
assert.match(
    map,
    /SeismicPolicy\.magnitudeRadius\([\s\S]*?modelData\.magnitude/
);
assert.match(
    map,
    /stationDiscovery\.earthquakeDepthColor\([\s\S]*?modelData\.depthKm/
);
assert.match(map, /title: "EARTHQUAKE INSPECTOR \/\/ USGS"/);
assert.match(map, /SeismicPolicy\.depthBand\(/);
assert.match(map, /TSUNAMI FLAG \/\/ /);
assert.match(
    map,
    /USGS OBSERVED EVENT \/\/ M2\.5\+ PAST DAY FEED \/\/ NOT AN EARTHQUAKE PREDICTION/
);
assert.match(map, /USGS \/\/ M2\.5\+ EARTHQUAKES \/\/ 24H/);
assert.doesNotMatch(
    map,
    /WeatherServices\.SeismicService\s*\{/
);

const workflow = read(".github/workflows/weather-teardown-contracts.yml");
assert.match(
    workflow,
    /node tests\/weather\/test_station_map_usgs_earthquakes\.js/
);

console.log("Weather shared USGS earthquake GROUND + MAP layer: PASS");
