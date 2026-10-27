#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/WeatherHistoryPolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const policy = {Date, Number, String, Array, JSON, Object, Math, isFinite};
vm.runInNewContext(source, policy, {filename:"WeatherHistoryPolicy.js"});

let anchor = policy.parseAnchor("2026-10-27 05:45 PM");
assert.equal(anchor.date, "2026-10-27");
assert.equal(anchor.hour, 17);
anchor = policy.parseAnchor("2026-10-27 00:20");
assert.equal(anchor.hour, 0);
assert.equal(policy.parseAnchor("bad"), null);

const spec = policy.requestSpec("38.75", "-76.90", "2026-10-27 05:45 PM");
assert.equal(spec.valid, true);
assert.equal(spec.startDate, "2026-10-20");
assert.equal(spec.endDate, "2026-10-26");
assert.equal(spec.localHour, 17);
assert.equal(spec.key, "38.7500,-76.9000|2026-10-20|2026-10-26|17");
assert.equal(policy.requestSpec("95", "-76", "2026-10-27 12:00").valid, false);

const dates = [
 "2026-10-20","2026-10-21","2026-10-22","2026-10-23",
 "2026-10-24","2026-10-25","2026-10-26"
];
const rootPayload = {
 timezone:"America/New_York",
 timezone_abbreviation:"EDT",
 daily:{
   time:dates,
   temperature_2m_max:[70,72,74,76,78,80,82],
   temperature_2m_min:[50,51,52,53,54,55,56],
   precipitation_sum:[0,0.1,0,0.5,0.02,0,0.2],
   wind_speed_10m_max:[10,11,12,13,14,15,16]
 },
 hourly:{
   time:[
     "2026-10-26T16:00","2026-10-26T17:00","2026-10-26T18:00"
   ],
   temperature_2m:[73,74,72],
   relative_humidity_2m:[50,55,60],
   apparent_temperature:[72,73,71],
   pressure_msl:[1012,1011,1010],
   wind_speed_10m:[7,8,9]
 }
};

const parsed = policy.parseResponse(rootPayload, spec);
assert.equal(parsed.daily.length, 7);
assert.equal(parsed.sameHour.time, "2026-10-26T17:00");
assert.equal(parsed.sameHour.tempF, 74);
assert.equal(parsed.sameHour.humidity, 55);
assert.equal(parsed.sameHour.pressureHpa, 1011);
assert.equal(parsed.sameHour.windMph, 8);
assert.equal(parsed.summary.days, 7);
assert.equal(parsed.summary.maxHighF, 82);
assert.equal(parsed.summary.minLowF, 50);
assert.equal(parsed.summary.avgHighF, 76);
assert.equal(parsed.summary.avgLowF, 53);
assert.ok(Math.abs(parsed.summary.precipitationIn - 0.82) < 1e-9);
assert.equal(parsed.summary.wetDays, 4);
assert.equal(parsed.summary.maxPrecipIn, 0.5);
assert.equal(parsed.summary.maxPrecipDate, "2026-10-23");
assert.equal(parsed.timezone, "America/New_York");
assert.equal(parsed.timezoneAbbreviation, "EDT");
assert.equal(policy.signedDelta(78, 74, 0), "+4");
assert.equal(policy.signedDelta(70, 74, 0), "-4");
assert.equal(policy.signedDelta("bad", 74, 0), "--");

const service = read("services/weather/WeatherHistoryService.qml");
assert.match(service, /historical-forecast-api\.open-meteo\.com\/v1\/forecast/);
assert.match(service, /start_date=/);
assert.match(service, /end_date=/);
assert.match(service, /timezone=auto/);
assert.match(service, /temperature_unit=fahrenheit/);
assert.match(service, /wind_speed_unit=mph/);
assert.match(service, /precipitation_unit=inch/);
assert.match(service, /interval: 21600000/);
assert.match(service, /now - lastAttemptMs < 300000/);
assert.match(service, /property var inflightSpec: null/);
assert.match(service, /const spec = \{/);
assert.match(service, /HistoryPolicy\.parseResponse\([\s\S]*inflightSpec/);
assert.match(service, /loadedKey = inflightKey/);
assert.equal((service.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((service.match(/\bTimer\s*\{/g) || []).length, 1);
for (const forbidden of [
    "FileView", "JsonAdapter", "write(", "POST_APOLLO_", "Qt.openUrlExternally"
])
    assert.ok(!service.includes(forbidden), forbidden);

const station = read("widgets/weather/WeatherStationW.qml");
assert.match(station, /import "\.\.\/\.\.\/services\/weather" as WeatherServices/);
assert.match(station, /WeatherServices\.WeatherHistoryService\s*\{/);
assert.match(station, /active: weatherStation\.menuOpen[\s\S]*?currentView === "home"/);
assert.match(station, /latitude: weatherStation\.weatherService/);
assert.match(station, /anchorDateTime: weatherStation\.weatherService/);
assert.match(station, /StationHome\s*\{[\s\S]*?historyService: weatherHistoryService/);

const home = read("widgets/weather/StationHome.qml");
assert.match(home, /property var historyService: null/);
assert.match(home, /title: "RECENT HISTORY \/\/ ARCHIVED MODEL"/);
assert.match(home, /OPEN-METEO \/\/ HISTORICAL FORECAST/);
assert.match(home, /title: "YESTERDAY \/\/ SAME HOUR"/);
assert.match(home, /title: "7-DAY TEMP RANGE"/);
assert.match(home, /title: "PRECIP \/\/ 7 DAYS"/);
assert.match(home, /NOT STATION OBSERVATIONS/);
assert.match(home, /NO LOCAL DATABASE/);
assert.match(home, /model: home\.historyDaily/);
assert.match(home, /HistoryPolicy\.signedDelta/);

console.log("Weather HOME recent archived-model history contracts: PASS");
