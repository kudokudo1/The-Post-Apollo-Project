#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {Date, Number, String, Array, JSON, Object, Math, isFinite};
vm.runInNewContext(
    read("services/weather/StationDiscoveryPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

const payload = {
    events: [
        {
            id: "EONET_WF_TEST",
            title: "Test Wildfire",
            description: "Observed fire event for parser validation.",
            link: "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_WF_TEST",
            categories: [{id: "wildfires", title: "Wildfires"}],
            sources: [
                {id: "InciWeb", url: "https://example.invalid/fire"},
                {id: "EO", url: "https://example.invalid/eo"}
            ],
            geometry: [
                {
                    date: "2026-10-26T18:30:00Z",
                    type: "Point",
                    coordinates: [-120.125, 38.625]
                }
            ],
            magnitudeValue: 1200,
            magnitudeUnit: "acres",
            magnitudeDescription: "Burned area"
        },
        {
            id: "EONET_STORM_TEST",
            title: "Test Severe Storm",
            link: "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_STORM_TEST",
            categories: [{id: "severeStorms", title: "Severe Storms"}],
            sources: [{id: "JTWC"}],
            geometry: [
                {
                    date: "2026-10-27T03:00:00Z",
                    type: "Polygon",
                    coordinates: [[[-70,20],[-69,20],[-69,21],[-70,20]]]
                }
            ]
        }
    ]
};

const rows = Array.from(ctx.parseEvents(payload));
assert.equal(rows.length, 2);

const fire = rows[0];
assert.equal(fire.id, "EONET_WF_TEST");
assert.equal(fire.categoryId, "wildfires");
assert.equal(fire.category, "Wildfires");
assert.equal(fire.coordinates, "38.63, -120.13");
assert.equal(fire.latitude, 38.625);
assert.equal(fire.longitude, -120.125);
assert.equal(fire.geometryType, "Point");
assert.equal(fire.time, "2026-10-26 18:30 UTC");
assert.equal(fire.sourceNames, "InciWeb / EO");
assert.equal(fire.magnitude, "1200 acres // Burned area");
assert.equal(fire.action, "INSPECT HERE");
assert.match(fire.description, /Observed fire event/);

const storm = rows[1];
assert.equal(storm.categoryId, "severeStorms");
assert.equal(storm.geometryType, "Polygon");
assert.equal(storm.coordinates, "Polygon");
assert.equal(storm.sourceNames, "JTWC");
assert.equal(storm.magnitude, "NOT REPORTED");

// Session cache is keyed by the active EONET category and does not turn a
// stale result into a fresh one. Copies prevent local list append mutation
// from changing the stored cache.
const t = 1793094005000;
ctx.storeMapRows("wildfires", [fire], t);
let cached = ctx.cachedMapRows("wildfires", t + 1000);
assert.equal(cached.fresh, true);
assert.equal(cached.updatedAtMs, t);
assert.equal(cached.rows.length, 1);
cached.rows.push(storm);
assert.equal(ctx.cachedMapRows("wildfires", t + 2000).rows.length, 1);
assert.equal(ctx.cachedMapRows("wildfires", t + 900001).fresh, false);
assert.equal(ctx.cachedMapRows("severeStorms", t + 1000).rows.length, 0);

const service = read("services/weather/StationDiscoveryService.qml");
assert.match(service, /property string mapCategory: ""/);
assert.match(service, /events\?status=open&limit=40/);
assert.match(service, /"&category=" \+ category/);
assert.match(service, /DiscoveryPolicy\.cachedMapRows\(mapCategory, Date\.now\(\)\)/);
assert.match(service, /DiscoveryPolicy\.storeMapRows\(mapCategory, parsed, now\)/);
assert.match(service, /onMapCategoryChanged:/);
assert.match(service, /changeMapCategory\(\)/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1,
             "MAP filters must reuse the existing fetch process");

const ui = read("widgets/weather/StationDiscovery.qml");
for (const label of ["ALL EVENTS", "WILDFIRE", "SEVERE STORM"])
    assert.ok(ui.includes('"label": "' + label + '"'), label);
assert.match(ui, /id: mapFilterRail/);
assert.match(ui, /delegate: ModeButton/);
assert.match(ui, /bordered: false/);
assert.match(ui, /selected: stationDiscovery\.mapFilter === modelData\.id/);
assert.match(ui, /mapCategory: stationDiscovery\.mapCategoryForFilter/);
assert.match(ui, /title: "EVENT INSPECTOR \/\/ NASA EONET"/);
for (const field of [
    "selectedMapEvent.category",
    "selectedMapEvent.coordinates",
    "selectedMapEvent.time",
    "selectedMapEvent.geometryType",
    "selectedMapEvent.magnitude",
    "selectedMapEvent.sourceNames",
    "selectedMapEvent.description"
])
    assert.ok(ui.includes(field), field);

const openRowStart = ui.indexOf("function openRow(row)");
const closeViewerStart = ui.indexOf("function closeViewer()", openRowStart);
assert.ok(openRowStart >= 0 && closeViewerStart > openRowStart);
const openRow = ui.slice(openRowStart, closeViewerStart);
assert.match(openRow, /if \(domain === "map"\)[\s\S]*selectedMapEvent = row;[\s\S]*return;/);
assert.match(openRow, /if \(row && row\.url\)[\s\S]*Qt\.openUrlExternally\(row\.url\)/);
assert.ok(
    openRow.indexOf('if (domain === "map")')
    < openRow.indexOf("Qt.openUrlExternally"),
    "MAP must return to its internal inspector before any external-open fallback"
);
assert.match(ui, /stationDiscovery\.domain === "map" \? "INSPECT HERE"/);
assert.match(ui, /SESSION CACHE \/\/ 15m/);
assert.match(ui, /EONET \+ FIRMS \+ MRMS \+ HMS SMOKE CONNECTED/);
assert.match(ui, /NATURAL EARTH BASEMAP \+ EONET \+ FIRMS \+ MRMS \+ HMS SMOKE CONNECTED/);

// Official NOAA MRMS radar is manual; RainViewer remains fallback-only.
assert.match(ui, /NASA FIRMS \/\/ VIIRS NOAA-21 HOTSPOTS/);
assert.match(ui, /KEY REQUIRED/);
assert.match(ui, /NOAA\/NWS MRMS \/\/ BASE REFLECTIVITY/);
assert.match(ui, /RAINVIEWER \/\/ RADAR FALLBACK", state:"NOT WIRED"/);
assert.match(ui, /NOAA HMS \/\/ SMOKE PLUME POLYGONS/);

console.log("Weather MAP EONET hazard filters, cache and inspector: PASS");
