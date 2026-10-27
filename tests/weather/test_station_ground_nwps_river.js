#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {Date, Number, String, Array, Object, Math, JSON, isFinite};
vm.runInNewContext(
    read("services/weather/NwpsRiverPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "distanceKm", "boundedBox", "categoryInfo",
    "normalizeGauge", "nearestGauge", "readingText"
])
    assert.equal(typeof ctx[fn], "function", fn);

const box = ctx.boundedBox(38.90, -77.00, 0.6);
assert.equal(box.xmin, -77.6);
assert.equal(box.xmax, -76.4);
assert.equal(box.ymin, 38.3);
assert.equal(box.ymax, 39.5);
assert.equal(ctx.boundedBox("", -77, 0.6), null);
assert.equal(ctx.boundedBox(38.9, -77, 4), null);

const categories = [
    ["major", "MAJOR", 4],
    ["Moderate Flooding", "MODERATE", 3],
    ["minor_flooding", "MINOR", 2],
    ["Action Stage", "ACTION", 1],
    ["No Flooding", "NO FLOODING", 0],
    ["Not Defined", "NOT DEFINED", -1]
];
for (const [raw, label, rank] of categories) {
    const result = ctx.categoryInfo(raw);
    assert.equal(result.label, label);
    assert.equal(result.rank, rank);
}

const nested = {
    lid: "TEST1",
    name: "Test River Near Town",
    latitude: 38.95,
    longitude: -77.05,
    state: {abbreviation:"MD", name:"Maryland"},
    wfo: {abbreviation:"LWX"},
    rfc: {abbreviation:"MARFC"},
    primaryUnits: "ft",
    secondaryUnits: "cfs",
    status: {
        observed: {
            primary: 7.25,
            secondary: 925,
            floodCategory: "No Flooding"
        },
        forecast: {
            primary: 8.50,
            secondary: 1100,
            floodCategory: "Action"
        }
    }
};

const flat = {
    lid: "TEST2",
    name: "Flat Shape Creek",
    latitude: 39.10,
    longitude: -76.90,
    primaryUnits: "ft",
    status_observed_primary: 12.3,
    status_observed_floodCategory: "Minor",
    status_forecast_primary: 13.8,
    status_forecast_floodCategory: "Moderate"
};

let gauge = ctx.normalizeGauge(nested, 38.9, -77.0);
assert.equal(gauge.lid, "TEST1");
assert.equal(gauge.state, "MD");
assert.equal(gauge.wfo, "LWX");
assert.equal(gauge.rfc, "MARFC");
assert.equal(gauge.observedPrimary, 7.25);
assert.equal(gauge.observedSecondary, 925);
assert.equal(gauge.observedCategory.label, "NO FLOODING");
assert.equal(gauge.forecastPrimary, 8.5);
assert.equal(gauge.forecastCategory.label, "ACTION");
assert.equal(gauge.primaryUnits, "ft");
assert.equal(gauge.secondaryUnits, "cfs");
assert.ok(gauge.distanceKm > 0 && gauge.distanceKm < 10);

gauge = ctx.normalizeGauge(flat, 38.9, -77.0);
assert.equal(gauge.observedPrimary, 12.3);
assert.equal(gauge.observedCategory.label, "MINOR");
assert.equal(gauge.forecastPrimary, 13.8);
assert.equal(gauge.forecastCategory.label, "MODERATE");

const response = {
    gauges: [
        {
            lid:"FAR01", name:"Far River",
            latitude:39.4, longitude:-77.4,
            status_observed_primary:1
        },
        nested,
        flat
    ]
};
gauge = ctx.nearestGauge(response, 38.9, -77.0);
assert.equal(gauge.lid, "TEST1");

assert.equal(
    ctx.nearestGauge({gauges:[]}, 38.9, -77.0),
    null
);
assert.throws(() => ctx.nearestGauge({}, 38.9, -77.0));
assert.throws(() => ctx.nearestGauge({gauges:[]}, "", -77));

assert.equal(ctx.readingText(7.25, "ft"), "7.25 ft");
assert.equal(ctx.readingText(925, "cfs"), "925.00 cfs");
assert.equal(ctx.readingText(null, "ft"), "--");

const service = read("services/weather/NwpsRiverService.qml");
assert.match(service, /api\.water\.noaa\.gov\/nwps\/v1\/gauges/);
assert.match(service, /bbox\.xmin=/);
assert.match(service, /bbox\.ymin=/);
assert.match(service, /bbox\.xmax=/);
assert.match(service, /bbox\.ymax=/);
assert.match(service, /srid=EPSG_4326/);
assert.match(service, /RiverPolicy\.boundedBox\(latitude, longitude, 0\.6\)/);
assert.match(service, /RiverPolicy\.nearestGauge/);
assert.match(service, /interval: 900000/);
assert.match(service, /running: river\.active && river\.configured/);
assert.match(service, /Post-Apollo-WeatherStation\/0\.4/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.doesNotMatch(service, /waterservices\.usgs\.gov|nwm|National Water Model/i);

const ground = read("widgets/weather/StationGround.qml");
assert.match(ground, /WeatherServices\.NwpsRiverService\s*\{/);
assert.match(ground, /latitude: weatherService \? weatherService\.latitude : ""/);
assert.match(ground, /longitude: weatherService \? weatherService\.longitude : ""/);
assert.match(ground, /title: "RIVER \/\/ NOAA NWPS"/);
assert.match(ground, /NEARBY GAUGE/);
assert.match(ground, /OBSERVED \/\/ PRIMARY/);
assert.match(ground, /FORECAST \/\/ PRIMARY/);
assert.match(ground, /riverService\.gauge\s*\.observedCategory\.label/);
assert.match(ground, /riverService\.gauge\s*\.forecastCategory\.label/);
assert.match(ground, /KM FROM WEATHER FIX/);
assert.match(ground, /INFORMATIONAL ONLY/);
assert.match(ground, /DOES NOT CHANGE THE EXPLICIT NWS ALERT TARGET/);
assert.match(ground, /STAGE IS RELATIVE TO THE GAUGE DATUM/);
assert.match(ground, /NEARBY GAUGE ≠ YOUR PROPERTY/);
assert.match(ground, /NOT A FLOOD WARNING/);

const riverStart = ground.indexOf('title: "RIVER // NOAA NWPS"');
const airStart = ground.indexOf('title: "AIR // PARTICULATES"', riverStart);
assert.ok(riverStart >= 0 && airStart > riverStart);
const riverArea = ground.slice(riverStart, airStart);
assert.doesNotMatch(
    riverArea,
    /Process\s*\{|curl|Qt\.openUrlExternally|POST_APOLLO_NWS_ALERT_POINT/
);

const serviceSource = read("services/weather/NwpsRiverService.qml");
assert.doesNotMatch(
    serviceSource,
    /POST_APOLLO_NWS_ALERT_POINT|alerts\/active/,
    "nearby informational river lookup must remain independent from emergency alert targeting"
);

console.log("Weather GROUND nearby NOAA NWPS gauge status: PASS");
