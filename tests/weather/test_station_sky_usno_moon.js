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
    read("services/weather/UsnoMoonPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "validDate", "snappedOffsetMinutes", "offsetHoursText",
    "requestInfo", "clockLabel", "illuminationPercent",
    "dataObject", "phenomenonKey", "emptyResult", "parse"
])
    assert.equal(typeof ctx[fn], "function", fn);

assert.equal(ctx.validDate("2026-10-28"), true);
assert.equal(ctx.validDate("2026-02-30"), false);
assert.equal(ctx.validDate("1699-12-31"), false);
assert.equal(ctx.validDate("2101-01-01"), false);

assert.equal(ctx.snappedOffsetMinutes(-240.868), -240);
assert.equal(ctx.offsetHoursText(-240.868), "-4");
assert.equal(ctx.offsetHoursText(330.2), "5.5");
assert.equal(ctx.offsetHoursText(345.1), "5.75");
assert.equal(ctx.snappedOffsetMinutes(-721), -720);
assert.equal(ctx.snappedOffsetMinutes(841), 840);
assert.equal(ctx.snappedOffsetMinutes(-730), null);
assert.equal(ctx.snappedOffsetMinutes(850), null);
assert.equal(ctx.snappedOffsetMinutes(null), null);

const request = ctx.requestInfo(
    "2026-10-28", 38.9, -77.0, -240.868
);
assert.equal(request.valid, true);
assert.equal(request.tzHours, "-4");
assert.equal(request.dateValid, true);
assert.equal(request.coordinatesValid, true);
assert.equal(request.offsetValid, true);
assert.equal(
    request.endpoint,
    "https://aa.usno.navy.mil/api/rstt/oneday"
    + "?date=2026-10-28"
    + "&coords=38.9000%2C-77.0000"
    + "&tz=-4"
);
assert.equal(
    request.key,
    "2026-10-28|38.9000|-77.0000|-4"
);
assert.equal(
    ctx.requestInfo("bad-date", 38.9, -77, -240).valid,
    false
);
assert.equal(
    ctx.requestInfo("bad-date", 38.9, -77, -240).dateValid,
    false
);
assert.equal(
    ctx.requestInfo("2026-10-28", "", -77, -240).valid,
    false
);
assert.equal(
    ctx.requestInfo("2026-10-28", "", -77, -240).coordinatesValid,
    false
);
assert.equal(
    ctx.requestInfo("2026-10-28", 38.9, "", -240).valid,
    false
);
assert.equal(
    ctx.requestInfo("2026-10-28", 38.9, -77, null).valid,
    false
);
assert.equal(
    ctx.requestInfo("2026-10-28", 38.9, -77, null).offsetValid,
    false
);

assert.equal(ctx.clockLabel("00:05"), "12:05 AM");
assert.equal(ctx.clockLabel("02:13"), "2:13 AM");
assert.equal(ctx.clockLabel("12:00"), "12:00 PM");
assert.equal(ctx.clockLabel("19:11"), "7:11 PM");
assert.equal(ctx.clockLabel("24:01"), "--");
assert.equal(ctx.clockLabel(null), "--");

assert.equal(ctx.illuminationPercent("91%"), 91);
assert.equal(ctx.illuminationPercent(0.42), 42);
assert.equal(ctx.illuminationPercent("0.75"), 75);
assert.equal(ctx.illuminationPercent(74), 74);
assert.equal(ctx.illuminationPercent(101), -1);
assert.equal(ctx.illuminationPercent("unknown"), -1);

const fixture = {
    type: "Feature",
    geometry: {
        type: "Point",
        coordinates: [-77.0, 38.9]
    },
    properties: {
        data: {
            year: 2026,
            month: 10,
            day: 28,
            tz: -4,
            curphase: "Waning Gibbous",
            fracillum: "91%",
            moondata: [
                {phen:"Set", time:"10:38"},
                {phen:"Rise", time:"19:11"},
                {phen:"Upper Transit", time:"02:13"}
            ]
        }
    }
};

let parsed = ctx.parse(fixture);
assert.equal(parsed.available, true);
assert.equal(parsed.rise, "7:11 PM");
assert.equal(parsed.transit, "2:13 AM");
assert.equal(parsed.set, "10:38 AM");
assert.equal(parsed.phase, "WANING GIBBOUS");
assert.equal(parsed.illumination, 91);
assert.equal(parsed.noRiseSet, false);
assert.equal(parsed.timezoneHours, "-4");
assert.equal(parsed.sourceDate, "2026-10-28");

// Tolerate the API's data object appearing inside a one-item array.
parsed = ctx.parse({
    properties: {
        data: [{
            year:2026, month:10, day:28, tz:5.5,
            curphase:"First Quarter",
            fracillum:0.5,
            moondata:[
                {phen:"Moonrise", time:"13:01"},
                {phen:"Transit", time:"19:20"},
                {phen:"Moonset", time:"01:44"}
            ]
        }]
    }
});
assert.equal(parsed.rise, "1:01 PM");
assert.equal(parsed.transit, "7:20 PM");
assert.equal(parsed.set, "1:44 AM");
assert.equal(parsed.phase, "FIRST QUARTER");
assert.equal(parsed.illumination, 50);
assert.equal(parsed.timezoneHours, "5.5");

// Null rise/set values are a legitimate high-latitude/special-case response.
// The UI must report no event instead of inventing a clock value.
parsed = ctx.parse({
    properties: {
        data: {
            year:2026, month:6, day:21, tz:0,
            curphase:"Waxing Crescent",
            fracillum:"33%",
            moondata:[
                {phen:"Rise", time:null},
                {phen:"Upper Transit", time:"12:11"},
                {phen:"Set", time:null}
            ]
        }
    }
});
assert.equal(parsed.available, true);
assert.equal(parsed.rise, "--");
assert.equal(parsed.transit, "12:11 PM");
assert.equal(parsed.set, "--");
assert.equal(parsed.noRiseSet, true);

assert.throws(() => ctx.parse({error:"bad request"}));
assert.throws(() => ctx.parse({properties:{data:[]}}));

const policy = read("services/weather/UsnoMoonPolicy.js");
assert.match(policy, /https:\/\/aa\.usno\.navy\.mil\/api\/rstt\/oneday/);
assert.doesNotMatch(
    policy,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

const service = read("services/weather/UsnoMoonService.qml");
assert.match(
    service,
    /^import QtQuick\s*\nimport Quickshell\s*\nimport Quickshell\.Io/m
);
assert.match(service, /Scope\s*\{/);
assert.match(service, /property var ephemeris: MoonPolicy\.emptyResult\(\)/);
assert.match(service, /MoonPolicy\.requestInfo\(/);
assert.match(service, /property string inflightKey: ""/);
assert.match(service, /request\.key !== inflightKey/);
assert.match(service, /request\.key === loadedKey/);
assert.match(service, /MoonPolicy\.parse\(/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 1);
assert.match(service, /interval: 250/);
assert.match(service, /repeat: false/);
assert.doesNotMatch(service, /repeat:\s*true/);
assert.doesNotMatch(service, /dst=/);
assert.match(service, /--proto", "=https"/);
assert.match(service, /Post-Apollo-WeatherStation\/0\.5/);

const weatherService = read("services/weather/WeatherService.qml");
assert.match(weatherService, /property var airQualityUtcOffsetMinutes: null/);
assert.match(weatherService, /property string airQualityTimezone: ""/);
assert.match(weatherService, /WeatherDataPolicy\.parseAirQualityContext\(root\)/);
assert.match(weatherService, /airQualityUtcOffsetMinutes = context\.utcOffsetMinutes/);
assert.match(weatherService, /&timezone=auto/);

const sky = read("widgets/weather/StationSky.qml");
assert.match(sky, /import "\.\.\/\.\.\/services\/weather" as WeatherServices/);
assert.match(sky, /WeatherServices\.UsnoMoonService\s*\{/);
assert.match(sky, /active: sky\.visible/);
assert.match(sky, /date: sky\.astronomySummary\.date/);
assert.doesNotMatch(sky, /date: sky\.skyCycle\.date/);
assert.match(sky, /readonly property bool openMeteoCivilOffsetAvailable/);
assert.match(sky, /weatherService\.airQualityUtcOffsetMinutes/);
assert.match(sky, /readonly property var moonCivilOffsetMinutes/);
assert.match(sky, /\? Number\(weatherService\.airQualityUtcOffsetMinutes\)/);
assert.match(sky, /: twilightSummary\.calibrationOffsetMinutes/);
assert.match(sky, /offsetMinutes: sky\.moonCivilOffsetMinutes/);
assert.match(sky, /moonCivilOffsetSource/);
assert.match(sky, /OPEN-METEO TIMEZONE/);
assert.match(sky, /SUNRISE CALIBRATION/);
assert.match(sky, /title: "MOON \/\/ USNO EPHEMERIS"/);
assert.match(sky, /text: "MOONRISE"/);
assert.match(sky, /text: "UPPER TRANSIT"/);
assert.match(sky, /text: "MOONSET"/);
assert.match(sky, /text: "USNO PHASE"/);
assert.match(sky, /text: "ILLUMINATION"/);
assert.match(sky, /moonService\.ephemeris\.rise/);
assert.match(sky, /moonService\.ephemeris\.transit/);
assert.match(sky, /moonService\.ephemeris\.set/);
assert.match(sky, /moonService\.ephemeris\.phase/);
assert.match(sky, /moonService\.ephemeris\.illumination/);
assert.match(sky, /NO MOONRISE OR MOONSET FOR THIS LOCAL DATE/);
assert.match(sky, /DATE-SCOPED REQUEST/);
assert.match(sky, /OPEN-METEO RESOLVED CIVIL OFFSET/);
assert.match(sky, /SUNRISE CALIBRATION FALLBACK/);
assert.match(sky, /function moonInputIssue\(\)/);
assert.match(sky, /INVALID\/MISSING/);

const cycleContext = {
    Date, Number, String, Array, Object, Math, JSON, isFinite
};
vm.runInNewContext(
    read("services/weather/WeatherCyclePolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    cycleContext
);
const staleCycle = cycleContext.atObservation(
    Date.parse("2026-10-31T09:00:00Z"),
    "2026-10-31 05:00 AM",
    Date.parse("2026-10-31T05:00:00Z"),
    [{
        date:"2026-10-31",
        sunrise:"07:35 AM",
        sunset:"06:09 PM",
        moonPhase:"Waning Gibbous",
        moonIllumination:78
    }]
);
assert.equal(staleCycle.date, "");
const fallbackAstronomy = cycleContext.astronomySummary(
    staleCycle.date,
    [{
        date:"2026-10-31",
        sunrise:"07:35 AM",
        sunset:"06:09 PM",
        moonPhase:"Waning Gibbous",
        moonIllumination:78
    }]
);
assert.equal(fallbackAstronomy.date, "2026-10-31");
assert.equal(
    ctx.requestInfo(
        fallbackAstronomy.date, 38.9, -77.0, -240
    ).dateValid,
    true
);

const astronomyStart = sky.indexOf(
    'title: "ASTRONOMY // SUN + MOON"'
);
const moonStart = sky.indexOf(
    'title: "MOON // USNO EPHEMERIS"',
    astronomyStart
);
const twilightStart = sky.indexOf(
    'title: "TWILIGHT // SOLAR WINDOWS"',
    moonStart
);
assert.ok(astronomyStart >= 0 && moonStart > astronomyStart);
assert.ok(twilightStart > moonStart);

const moonArea = sky.slice(moonStart, twilightStart);
assert.doesNotMatch(
    moonArea,
    /Process\s*\{|Timer\s*\{|curl|Qt\.openUrlExternally|WebEngine/
);

console.log("Weather SKY USNO moonrise/transit/moonset ephemeris: PASS");
