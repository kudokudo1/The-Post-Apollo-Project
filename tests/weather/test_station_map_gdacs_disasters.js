#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const policySource = read("services/weather/GdacsPolicy.js");
const ctx = {
    Date, Math, Number, String, Array, Object, JSON,
    isFinite, isNaN
};
vm.runInNewContext(
    policySource.replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "eventTypeLabel", "normalizeAlertLevel", "alertToken",
    "alertRank", "alertRadius", "parseEventList", "summary"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.equal(ctx.eventTypeLabel("EQ"), "EARTHQUAKE");
assert.equal(ctx.eventTypeLabel("TC"), "TROPICAL CYCLONE");
assert.equal(ctx.eventTypeLabel("FL"), "FLOOD");
assert.equal(ctx.eventTypeLabel("VO"), "VOLCANO");
assert.equal(ctx.eventTypeLabel("DR"), "DROUGHT");
assert.equal(ctx.eventTypeLabel("WF"), "WILDFIRE");
assert.equal(ctx.normalizeAlertLevel(" red "), "RED");
assert.equal(ctx.normalizeAlertLevel("wat"), "UNKNOWN");
assert.equal(ctx.alertToken("RED"), "red");
assert.equal(ctx.alertToken("Orange"), "orange");
assert.equal(ctx.alertToken("Green"), "cyan");
assert.ok(ctx.alertRadius("RED") > ctx.alertRadius("ORANGE"));
assert.ok(ctx.alertRadius("ORANGE") > ctx.alertRadius("GREEN"));

const payload = {
    type: "FeatureCollection",
    features: [
        {
            type: "Feature",
            geometry: {type: "Point", coordinates: [-77.01, 38.91]},
            properties: {
                eventid: 1100001,
                episodeid: 2,
                eventtype: "FL",
                name: "Flood in Example",
                alertlevel: "Red",
                alertscore: 2,
                country: "Exampleland",
                iso3: "EXP",
                fromdate: "2026-10-30T00:00:00",
                todate: "2026-10-31T18:00:00",
                iscurrent: true,
                source: "GDACS",
                severitydata: {
                    severity: 42,
                    severitytext: "Severe flood impact",
                    severityunit: "km2"
                },
                url: {
                    report: "https://www.gdacs.org/report.aspx?eventid=1100001&eventtype=FL",
                    details: "https://www.gdacs.org/gdacsapi/api/events/geteventdata?eventtype=FL&eventid=1100001"
                }
            }
        },
        {
            type: "Feature",
            geometry: {type: "Point", coordinates: [140.2, 18.4]},
            properties: {
                eventid: 1100002,
                episodeid: 1,
                eventtype: "TC",
                name: "Cyclone Example",
                alertlevel: "Orange",
                country: "Ocean",
                fromdate: "2026-10-29T00:00:00",
                todate: "2026-10-31T12:00:00",
                iscurrent: true,
                severitydata: {severitytext: "Tropical cyclone"}
            }
        },
        {
            type: "Feature",
            geometry: {type: "Point", coordinates: [-120, 37]},
            properties: {
                eventid: 1100003,
                episodeid: 4,
                eventtype: "WF",
                name: "Wildfire Example",
                alertlevel: "Green",
                country: "Exampleland",
                fromdate: "2026-10-20T00:00:00",
                todate: "2026-10-25T00:00:00",
                iscurrent: false,
                severitydata: {}
            }
        },
        {
            type: "Feature",
            geometry: {type: "Polygon", coordinates: []},
            properties: {eventid: 999, eventtype: "FL", alertlevel: "Red"}
        },
        {
            type: "Feature",
            geometry: {type: "Point", coordinates: [500, 0]},
            properties: {eventid: 998, eventtype: "EQ", alertlevel: "Red"}
        }
    ]
};

const rows = Array.from(ctx.parseEventList(payload, 100));
assert.equal(rows.length, 3);
assert.equal(rows[0].id, "FL:1100001:2");
assert.equal(rows[0].eventTypeLabel, "FLOOD");
assert.equal(rows[0].alertLevel, "RED");
assert.equal(rows[0].country, "Exampleland");
assert.equal(rows[0].iso3, "EXP");
assert.equal(rows[0].coordinates, "38.91, -77.01");
assert.equal(rows[0].severity, 42);
assert.equal(rows[0].severityText, "Severe flood impact");
assert.equal(rows[0].severityUnit, "km2");
assert.equal(rows[0].isCurrent, true);
assert.match(rows[0].fromUtc, /2026-10-30 00:00 UTC/);
assert.match(rows[0].toUtc, /2026-10-31 18:00 UTC/);
assert.equal(rows[1].alertLevel, "ORANGE");
assert.equal(rows[2].alertLevel, "GREEN");
assert.equal(rows[2].isCurrent, false);

const summary = ctx.summary(rows);
assert.deepEqual(
    JSON.parse(JSON.stringify(summary)),
    {count: 3, current: 2, red: 1, orange: 1, green: 1}
);

assert.throws(() => ctx.parseEventList({features: []}, 100));

const service = read("services/weather/GdacsService.qml");
assert.match(
    service,
    /gdacs\.org\/gdacsapi\/api\/events\/geteventlist\/events4app/
);
assert.match(service, /GdacsPolicy\.parseEventList\(JSON\.parse\(raw\), 100\)/);
assert.match(service, /property int cacheMs: 900000/);
assert.match(service, /now - lastFetchMs < cacheMs/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 1);
assert.doesNotMatch(service, /API[_ -]?KEY|TOKEN|PASSWORD/i);

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(
    ui,
    /import "\.\.\/\.\.\/services\/weather\/GdacsPolicy\.js" as GdacsPolicy/
);
assert.match(ui, /WeatherServices\.GdacsService\s*\{/);
assert.match(
    ui,
    /active: stationDiscovery\.domain === "map"[\s\S]*?stationDiscovery\.stationOpen[\s\S]*?stationDiscovery\.visible/
);
assert.match(ui, /property bool mapShowGdacs: true/);
assert.match(ui, /property var selectedMapGdacsEvent: null/);
assert.match(ui, /MapProjection\.plottable\(gdacsService\.events\)/);
assert.match(ui, /label: "GDACS: "/);
assert.match(ui, /model: stationDiscovery\.mapGdacsRows/);
assert.match(ui, /GdacsPolicy\.alertRadius\(modelData\.alertLevel\)/);
assert.match(ui, /title: "DISASTER INSPECTOR \/\/ GDACS"/);
assert.match(
    ui,
    /GLOBAL DISASTER AWARENESS AND COORDINATION SYSTEM, GDACS \/\/ EARLY-WARNING CONTEXT \/\/ VERIFY LOCAL\/NATIONAL WARNINGS/
);
assert.match(
    ui,
    /NATURAL EARTH \+ EONET \+ GDACS \+ USGS EARTHQUAKES \+ FIRMS \+ MRMS \+ RAINVIEWER FALLBACK \+ HMS SMOKE/
);
assert.match(
    ui,
    /SPATIAL PLOT \/\/ GDACS \+ USGS QUAKES \+ EONET \+ FIRMS \+ NEWS/
);

console.log("Weather MAP GDACS multi-hazard disaster intelligence: PASS");
