#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/SpaceHistoryPolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const p = {Date, Number, String, Array, JSON, Object, Math, isFinite};
vm.runInNewContext(source, p, {filename:"SpaceHistoryPolicy.js"});

const rows = [];
for (let i = 0; i < 30; i++) {
    const hour = (i * 3) % 24;
    const day = 20 + Math.floor(i * 3 / 24);
    rows.push({
        time_tag: "2026-10-" + String(day).padStart(2,"0")
                  + "T" + String(hour).padStart(2,"0") + ":00:00",
        Kp: i % 10 === 9 ? 9 : (i % 7) / 1.5,
        a_running: i + 1,
        station_count: i % 5 === 0 ? 6 : 8
    });
}
rows.push({time_tag:"bad",Kp:3,a_running:1,station_count:8});
rows.push({time_tag:"2026-10-27T12:00:00",Kp:99,a_running:1,station_count:8});

const parsed = p.parseKpHistory(rows, 24);
assert.equal(parsed.rows.length, 24);
assert.equal(parsed.summary.bins, 24);
assert.equal(parsed.summary.hours, 72);
assert.equal(parsed.latest.time, parsed.rows[23].time);
assert.equal(parsed.summary.latestA, parsed.latest.aRunning);
assert.equal(parsed.summary.latestStationCount, parsed.latest.stationCount);
assert.equal(parsed.summary.minStationCount, 6);
assert.ok(parsed.summary.maxKp >= 0 && parsed.summary.maxKp <= 9);
assert.ok(parsed.summary.averageKp >= 0 && parsed.summary.averageKp <= 9);
assert.ok(parsed.summary.activeBins >= parsed.summary.stormBins);
assert.ok(parsed.rows.every(row => row.level >= 0 && row.level <= 1));
assert.ok(parsed.rows.every((row,index,array) =>
    index === 0 || array[index - 1].timeMs <= row.timeMs
));
assert.match(parsed.rows[0].timeLabel, /^\d{2}-\d{2} \d{2}Z$/);
assert.throws(() => p.parseKpHistory([], 24));

const service = read("services/weather/SpaceService.qml");
assert.match(service, /SpaceHistoryPolicy\.js" as SpaceHistoryPolicy/);
assert.match(service, /property var kpHistory: \[\]/);
assert.match(service, /property var kpHistorySummary:/);
assert.match(service, /SpaceHistoryPolicy\.parseKpHistory\([\s\S]*JSON\.parse\(rawText\), 24/);
assert.match(service, /kp = parsed\.latest\.kp/);
assert.match(service, /kpTime = parsed\.latest\.time/);
assert.match(service, /kpHistory = parsed\.rows/);
assert.match(service, /kpHistorySummary = parsed\.summary/);
assert.equal((service.match(/noaa-planetary-k-index\.json/g) || []).length, 1);
assert.equal((service.match(/id: kpFetch/g) || []).length, 1);
assert.equal((service.match(/interval: 300000/g) || []).length >= 1, true);

const ui = read("widgets/weather/StationSpace.qml");
assert.match(ui, /readonly property var kpHistory:/);
assert.match(ui, /readonly property var kpHistorySummary:/);
assert.match(ui, /function kpHistoryColor\(value\)/);
assert.match(ui, /title: "GEOMAGNETIC \/\/ KP 72-HOUR HISTORY"/);
assert.match(ui, /"title": "MAX \/\/ 72H"/);
assert.match(ui, /"title": "AVG \/\/ 72H"/);
assert.match(ui, /"title": "ACTIVE \/ STORM"/);
assert.match(ui, /"title": "LATEST \/\/ Δ"/);
assert.match(ui, /model: space\.kpHistory/);
assert.match(ui, /height: 4 \+ 60 \* modelData\.level/);
assert.match(ui, /modelData\.timeLabel/);
assert.match(ui, /3-HOUR PUBLISHED BINS \/\/ SAME EXISTING 5-MIN FETCH \/\/ NO NEW REQUEST/);

console.log("Weather SPACE 72-hour Kp history from existing feed: PASS");
