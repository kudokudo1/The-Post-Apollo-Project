#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/WeatherEventRelationPolicy.js");
const ctx = {Date, Math, Number, String, Array, Object, JSON, isFinite};
vm.runInNewContext(source.replace(/^\.pragma library\s*/m, ""), ctx);

for (const fn of [
    "distanceKm", "canonicalHazard", "limits",
    "anchorFromEonet", "anchorFromGdacs",
    "anchorFromEarthquake", "anchorFromHotspot",
    "sourceCandidates", "relationsForAnchor"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.equal(ctx.canonicalHazard("wildfires"), "fire");
assert.equal(ctx.canonicalHazard("WF"), "fire");
assert.equal(ctx.canonicalHazard("EQ"), "earthquake");
assert.equal(ctx.canonicalHazard("severeStorms"), "storm");
assert.equal(ctx.canonicalHazard("TC"), "storm");
assert.equal(ctx.canonicalHazard("FL"), "flood");
assert.equal(ctx.canonicalHazard("VO"), "volcano");
assert.equal(ctx.canonicalHazard("DR"), "drought");
assert.equal(ctx.canonicalHazard("something else"), "unknown");

const dcToBaltimore = ctx.distanceKm(38.9072, -77.0369, 39.2904, -76.6122);
assert.ok(dcToBaltimore > 50 && dcToBaltimore < 70);
assert.equal(ctx.distanceKm(100, 0, 0, 0), -1);

const eonetFire = {
    id: "EONET_FIRE_1",
    title: "Example Fire",
    categoryId: "wildfires",
    latitude: 38.5,
    longitude: -77.2,
    rawTime: "2026-10-31T18:00:00Z"
};
const anchor = ctx.anchorFromEonet(eonetFire);
assert.equal(anchor.source, "NASA EONET");
assert.equal(anchor.hazard, "fire");
assert.equal(anchor.id, "EONET_FIRE_1");

const inputs = {
    eonet: [eonetFire, {
        id: "EONET_STORM",
        title: "Unrelated Storm",
        categoryId: "severeStorms",
        latitude: 38.6,
        longitude: -77.1,
        rawTime: "2026-10-31T18:00:00Z"
    }],
    gdacs: [{
        id: "WF:1:1",
        name: "GDACS Fire",
        eventType: "WF",
        latitude: 38.7,
        longitude: -77.0,
        timeMs: Date.parse("2026-10-31T19:00:00Z")
    }, {
        id: "WF:2:1",
        name: "Old GDACS Fire",
        eventType: "WF",
        latitude: 38.55,
        longitude: -77.15,
        timeMs: Date.parse("2026-10-20T19:00:00Z")
    }],
    earthquakes: [{
        id: "quake-near",
        place: "Nearby quake",
        latitude: 38.6,
        longitude: -77.1,
        time: Date.parse("2026-10-31T18:30:00Z")
    }],
    hotspots: [{
        id: "firms-near",
        title: "VIIRS HOTSPOT",
        latitude: 38.52,
        longitude: -77.18,
        acquiredUtc: "2026-10-31 18:15Z",
        confidenceLabel: "HIGH"
    }, {
        id: "firms-far",
        title: "VIIRS HOTSPOT",
        latitude: 30,
        longitude: -90,
        acquiredUtc: "2026-10-31 18:15Z",
        confidenceLabel: "HIGH"
    }],
    newsMentions: [{
        featureId: "place-near",
        name: "Nearby Place",
        latitude: 38.51,
        longitude: -77.19
    }]
};

const candidates = Array.from(ctx.sourceCandidates(inputs));
assert.equal(candidates.length, 8);

const relations = Array.from(ctx.relationsForAnchor(anchor, inputs, 8));
const ids = relations.map(row => row.id);
assert.ok(ids.includes("WF:1:1"), "near recent GDACS wildfire is context");
assert.ok(ids.includes("firms-near"), "near recent FIRMS hotspot is context");
assert.ok(ids.includes("place-near"), "near NEWS mention is spatial context");
assert.ok(!ids.includes("EONET_FIRE_1"), "anchor record excludes itself");
assert.ok(!ids.includes("EONET_STORM"), "hazard-incompatible source is excluded");
assert.ok(!ids.includes("quake-near"), "earthquake is not fire context");
assert.ok(!ids.includes("WF:2:1"), "old fire is outside temporal bound");
assert.ok(!ids.includes("firms-far"), "far hotspot is outside spatial bound");

const gdacs = relations.find(row => row.id === "WF:1:1");
assert.equal(gdacs.relationKind, "TIME + SPACE");
assert.match(gdacs.semantics, /NOT SAME-EVENT IDENTITY/);
assert.ok(gdacs.distanceKm > 0);
assert.ok(gdacs.deltaHours >= 0 && gdacs.deltaHours <= 2);

const mention = relations.find(row => row.id === "place-near");
assert.equal(mention.relationKind, "MENTION NEARBY");
assert.equal(mention.mentionOnly, true);
assert.match(mention.semantics, /NOT VERIFIED EVENT LOCATION/);

const noTime = Array.from(ctx.relationsForAnchor(
    ctx.anchorFromHotspot({
        id: "hotspot-anchor",
        title: "VIIRS HOTSPOT",
        latitude: 38.5,
        longitude: -77.2,
        acquiredUtc: ""
    }),
    {
        eonet: [{
            id: "fire-no-time",
            title: "Fire Without Time",
            categoryId: "wildfires",
            latitude: 38.51,
            longitude: -77.2,
            rawTime: ""
        }]
    },
    8
));
assert.equal(noTime.length, 1);
assert.equal(noTime[0].relationKind, "SPACE ONLY");
assert.equal(noTime[0].deltaHours, -1);

const quakeAnchor = ctx.anchorFromEarthquake({
    id: "q1",
    place: "M4.2 Example",
    latitude: 35,
    longitude: -118,
    time: Date.parse("2026-10-31T12:00:00Z")
});
const quakeRelations = Array.from(ctx.relationsForAnchor(
    quakeAnchor,
    {
        gdacs: [{
            id: "EQ:44:1",
            name: "GDACS Earthquake",
            eventType: "EQ",
            latitude: 35.3,
            longitude: -118.2,
            timeMs: Date.parse("2026-10-31T12:30:00Z")
        }],
        earthquakes: [{
            id: "q1",
            place: "M4.2 Example",
            latitude: 35,
            longitude: -118,
            time: Date.parse("2026-10-31T12:00:00Z")
        }]
    },
    8
));
assert.equal(quakeRelations.length, 1);
assert.equal(quakeRelations[0].source, "GDACS");
assert.equal(quakeRelations[0].relationKind, "TIME + SPACE");

console.log("Weather MAP conservative cross-source relations: PASS");
