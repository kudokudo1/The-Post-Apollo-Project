#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const ctx = {
    Date, Number, String, Array, Object, Math, JSON,
    isFinite, encodeURIComponent
};
vm.runInNewContext(
    read("services/weather/UsnoCelnavPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "requestInfo", "compassDirection", "constellationForNavStar",
    "constellationGroups", "almanacData", "normalizeObject",
    "emptyResult", "parse"
])
    assert.equal(typeof ctx[fn], "function", fn);

const request = ctx.requestInfo(
    Date.parse("2026-10-31T09:42:00Z"),
    38.9,
    -77.0
);
assert.equal(request.valid, true);
assert.equal(request.date, "2026-10-31");
assert.equal(request.time, "09:42");
assert.equal(
    request.endpoint,
    "https://aa.usno.navy.mil/api/celnav"
    + "?date=2026-10-31"
    + "&time=09%3A42"
    + "&coords=38.9000%2C-77.0000"
    + "&id=PostApW"
);
assert.equal(
    request.key,
    "2026-10-31|09:42|38.9000|-77.0000"
);
assert.equal(ctx.requestInfo(0, 38.9, -77).valid, false);
assert.equal(ctx.requestInfo(Date.now(), "", -77).valid, false);
assert.equal(ctx.requestInfo(Date.now(), 91, -77).valid, false);
assert.equal(
    ctx.requestInfo(Date.parse("2051-01-01T00:00:00Z"), 38.9, -77).valid,
    false
);

assert.equal(ctx.compassDirection(0), "N");
assert.equal(ctx.compassDirection(90), "E");
assert.equal(ctx.compassDirection(180), "S");
assert.equal(ctx.compassDirection(270), "W");
assert.equal(ctx.compassDirection(225), "SW");

assert.equal(ctx.constellationForNavStar(18, "Sirius"), "CANIS MAJOR");
assert.equal(ctx.constellationForNavStar(49, "Vega"), "LYRA");
assert.equal(ctx.constellationForNavStar(null, "Polaris"), "URSA MINOR");
assert.equal(ctx.constellationForNavStar(null, "Unknown"), "");

const grouped = Array.from(ctx.constellationGroups([
    {
        name:"RIGEL", constellation:"ORION",
        altitude:25, azimuth:160, direction:"SSE"
    },
    {
        name:"BETELGEUSE", constellation:"ORION",
        altitude:42, azimuth:145, direction:"SE"
    },
    {
        name:"VEGA", constellation:"LYRA",
        altitude:65, azimuth:290, direction:"WNW"
    },
    {
        name:"UNKNOWN", constellation:"",
        altitude:80, azimuth:10, direction:"N"
    }
]));
assert.equal(grouped.length, 2);
assert.equal(grouped[0].name, "LYRA");
assert.equal(grouped[0].count, 1);
assert.equal(grouped[0].anchorStar, "VEGA");
assert.equal(grouped[0].anchorAltitude, 65);
assert.equal(grouped[0].anchorDirection, "WNW");
assert.deepEqual(Array.from(grouped[0].starNames), ["VEGA"]);
assert.equal(grouped[1].name, "ORION");
assert.equal(grouped[1].count, 2);
assert.equal(grouped[1].anchorStar, "BETELGEUSE");
assert.equal(grouped[1].anchorAltitude, 42);
assert.deepEqual(
    Array.from(grouped[1].starNames),
    ["BETELGEUSE", "RIGEL"]
);

const fixture = {
    type:"Feature",
    geometry:{type:"Point", coordinates:[-77, 38.9]},
    properties:{
        year:2026,
        month:10,
        day:31,
        time:"09:42:00",
        data:[
            {
                object:"Moon",
                almanac_data:{hc:35.2, zn:124.6}
            },
            {
                object:"Venus",
                almanac_data:{hc:18.4, zn:101.0}
            },
            {
                object:"Jupiter",
                almanac_data:[{hc:42.1, zn:255.4}]
            },
            {
                object:"Sirius",
                nav_star_number:18,
                almanac_data:{hc:27.8, zn:165.0}
            },
            {
                object:"Vega",
                nav_star_number:"49",
                almanac_data:{hc:65.3, zn:290.0}
            },
            {
                object:"Sun",
                almanac_data:{hc:-8.1, zn:82.0}
            },
            {
                object:"Broken",
                nav_star_number:1,
                almanac_data:{hc:null, zn:10}
            }
        ]
    }
};

const parsed = ctx.parse(fixture);
assert.equal(parsed.available, true);
assert.equal(parsed.date, "2026-10-31");
assert.equal(parsed.time, "09:42:00");
assert.equal(parsed.moon.name, "MOON");
assert.equal(parsed.moon.altitude, 35.2);
assert.equal(parsed.moon.azimuth, 124.6);
assert.equal(parsed.moon.direction, "SE");
assert.equal(parsed.sun.name, "SUN");
assert.deepEqual(
    Array.from(parsed.planets, x => x.name),
    ["JUPITER", "VENUS"]
);
assert.equal(parsed.planets[0].altitude, 42.1);
assert.deepEqual(
    Array.from(parsed.stars, x => x.name),
    ["VEGA", "SIRIUS"]
);
assert.equal(parsed.stars[0].constellation, "LYRA");
assert.equal(parsed.stars[1].constellation, "CANIS MAJOR");

assert.equal(parsed.constellations.length, 2);
assert.equal(parsed.constellations[0].name, "LYRA");
assert.equal(parsed.constellations[0].anchorStar, "VEGA");
assert.equal(parsed.constellations[1].name, "CANIS MAJOR");
assert.equal(parsed.constellations[1].anchorStar, "SIRIUS");

assert.throws(() => ctx.parse(null));
assert.throws(() => ctx.parse({error:"bad request"}));
assert.throws(() => ctx.parse({properties:{data:[]}}));

const policy = read("services/weather/UsnoCelnavPolicy.js");
assert.match(policy, /https:\/\/aa\.usno\.navy\.mil\/api\/celnav/);
assert.match(policy, /&id=PostApW/);
assert.doesNotMatch(
    policy,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

const service = read("services/weather/UsnoCelnavService.qml");
assert.match(
    service,
    /^import QtQuick\s*\nimport Quickshell\s*\nimport Quickshell\.Io/m
);
assert.match(service, /Scope\s*\{/);
assert.match(service, /CelnavPolicy\.requestInfo/);
assert.match(service, /CelnavPolicy\.parse/);
assert.match(service, /property string inflightKey: ""/);
assert.match(service, /current\.key !== inflightKey/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 2);
assert.match(service, /interval: 300000/);
assert.match(service, /running: celnav\.active && celnav\.configured/);
assert.match(service, /interval: 250/);
assert.match(service, /--proto", "=https"/);
assert.match(service, /Post-Apollo-WeatherStation\/0\.6/);
assert.doesNotMatch(service, /Qt\.openUrlExternally|WebEngine/);

const sky = read("widgets/weather/StationSky.qml");
assert.match(sky, /WeatherServices\.UsnoCelnavService\s*\{/);
assert.match(sky, /active: sky\.visible/);
assert.match(sky, /title: "SKY NOW \/\/ USNO CELESTIAL FIX"/);
assert.match(sky, /MOON \/\/ CURRENT POSITION/);
assert.match(sky, /ALTITUDE \/\/ HC/);
assert.match(sky, /AZIMUTH \/\/ ZN/);
assert.match(sky, /PLANETS ABOVE HORIZON/);
assert.match(sky, /NAVIGATION STARS \/\/ CONSTELLATION CONTEXT/);
assert.match(sky, /CONSTELLATION ANCHORS \/\//);
assert.match(sky, /celnavService\.snapshot\.constellations/);
assert.match(sky, /modelData\.anchorStar/);
assert.match(sky, /modelData\.anchorAltitude/);
assert.match(sky, /modelData\.anchorDirection/);
assert.match(sky, /modelData\.starNames\.join\(" \/ "\)/);
assert.match(sky, /GROUP RETURNED NAVIGATION STARS ONLY/);
assert.match(sky, /NOT FULL IAU CONSTELLATION BOUNDARIES OR ALL VISIBLE STARS/);
assert.match(sky, /celnavService\.snapshot\.planets/);
assert.match(sky, /celnavService\.snapshot\.stars/);
assert.match(sky, /celnavService\.snapshot\.moon/);
assert.match(sky, /ABOVE-HORIZON CATALOG ≠ NAKED-EYE VISIBILITY/);
assert.match(sky, /DAYLIGHT, SUN GLARE, CLOUDS \+ TERRAIN ARE NOT MODELED/);
assert.match(sky, /UTC MINUTE USED FOR USNO UT1 INPUT/);

const skyNowStart = sky.indexOf(
    'title: "SKY NOW // USNO CELESTIAL FIX"'
);
const twilightStart = sky.indexOf(
    'title: "TWILIGHT // SOLAR WINDOWS"',
    skyNowStart
);
assert.ok(skyNowStart >= 0 && twilightStart > skyNowStart);
const skyNowArea = sky.slice(skyNowStart, twilightStart);
assert.doesNotMatch(
    skyNowArea,
    /Process\s*\{|Timer\s*\{|curl|Qt\.openUrlExternally|WebEngine/
);

console.log("Weather SKY USNO current Moon planets and stars: PASS");
