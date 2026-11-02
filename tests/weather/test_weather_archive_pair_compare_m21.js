#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
const ctx = {
    Date, Math, Number, String, Array, Object, JSON, RegExp,
    isFinite, isNaN
};
vm.runInNewContext(
    read("services/weather/WeatherEventArchivePolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    ctx,
    {filename:"services/weather/WeatherEventArchivePolicy.js"}
);

assert.equal(typeof ctx.pairDiff, "function");
const minute = 60000;
const now = Date.UTC(2026, 10, 2, 19, 0, 0);
const id = "FL:900:1";
const baseEvent = {
    id:id,
    eventId:"900",
    episodeId:"1",
    eventType:"FL",
    eventTypeLabel:"FLOOD",
    name:"Retained Flood",
    alertLevel:"ORANGE",
    alertScore:0,
    isCurrent:true,
    country:"United States",
    iso3:"USA",
    latitude:38.90,
    longitude:-77.10,
    timeMs:now - minute,
    severity:2.1,
    severityText:"Flood evidence",
    severityUnit:"m",
    reportUrl:"https://example.invalid/report",
    detailsUrl:"https://example.invalid/details"
};
let doc = ctx.initialDocument();
for (let i = 0; i < 7; i++) {
    const result = ctx.append(
        doc, "gdacs",
        {...baseEvent, alertScore:i, severity:2.1 + i / 10},
        now + i * minute
    );
    assert.equal(result.ok, true);
    assert.equal(result.changed, true);
    doc = result.document;
}
const checkTime = now + 10 * minute;
assert.equal(ctx.snapshotCount(doc, "gdacs", id, checkTime), 7);

// Any retained pair is supported, even beyond the five preview rows.
let diff = ctx.pairDiff(doc, "gdacs", id, checkTime, 2, 5);
assert.equal(diff.available, true);
assert.equal(diff.sameIdentity, true);
assert.equal(diff.previousCapturedAtMs, now + minute);
assert.equal(diff.currentCapturedAtMs, now + 4 * minute);
let score = Array.from(diff.changes).find(row => row.key === "alertScore");
assert.ok(score);
assert.equal(score.beforeValue, 1);
assert.equal(score.afterValue, 4);

diff = ctx.pairDiff(doc, "gdacs", id, checkTime, 1, 7);
assert.equal(diff.available, true);
score = Array.from(diff.changes).find(row => row.key === "alertScore");
assert.equal(score.beforeValue, 0);
assert.equal(score.afterValue, 6);

const defaultPair = ctx.pairDiff(doc, "gdacs", id, checkTime, 6, 7);
const m20Default = ctx.latestDiff(doc, "gdacs", id, checkTime);
assert.equal(defaultPair.available, true);
assert.equal(defaultPair.previousCapturedAtMs, m20Default.previousCapturedAtMs);
assert.equal(defaultPair.currentCapturedAtMs, m20Default.currentCapturedAtMs);
assert.equal(defaultPair.changedCount, m20Default.changedCount);

// Invalid, reversed or nonexistent choices must never silently compare
// a different pair. Provider identity is still enforced.
for (const pair of [
    [0, 7], [1, 8], [7, 1], [4, 4], [-1, 4],
    [1.5, 4], [2, NaN], [2, Infinity]
]) {
    diff = ctx.pairDiff(doc, "gdacs", id, checkTime, pair[0], pair[1]);
    assert.equal(diff.available, false, JSON.stringify(pair));
}
assert.equal(ctx.pairDiff(doc, "usgs", id, checkTime, 1, 7).available, false);
assert.equal(ctx.pairDiff(doc, "gdacs", "FL:999:1", checkTime, 1, 7).available, false);

const store = read("services/weather/WeatherEventArchiveStore.qml");
assert.match(store, /function pairDiff\(sourceId, eventId, nowMs, earlierPosition, laterPosition\)/);
assert.match(store, /ArchivePolicy\.pairDiff\(/);
assert.equal((store.match(/\bFileView\s*\{/g) || []).length, 1);
assert.equal((store.match(/function archiveEvent\(/g) || []).length, 1);
assert.equal((store.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((store.match(/\bProcess\s*\{/g) || []).length, 0);

const map = read("widgets/weather/StationDiscovery.qml");
assert.match(map, /readonly property string archivePairIdentity:/);
assert.match(map, /onArchivePairIdentityChanged:/);
assert.match(map, /onSelectedArchiveRevisionChanged:/);
assert.match(map, /function selectArchivePair\(earlierPosition, laterPosition\)/);
assert.match(map, /eventArchiveStore\.pairDiff\(/);
assert.match(map, /archivePairDiff:\s*stationDiscovery\.selectedArchivePairDiff/);
assert.match(map, /onArchivePairRequested:/);
assert.equal((map.match(/eventArchiveStore\.archiveEvent\(/g) || []).length, 1);

const card = read("widgets/weather/StationEventContextCard.qml");
for (const text of [
    "EARLIER // SNAP ",
    "LATER // SNAP ",
    "SELECT ANY RETAINED PAIR",
    "SELECTED ARCHIVE DIFF",
    "LATEST ARCHIVE DIFF // NEWEST VS PREVIOUS",
    "BOUNDED SNAPSHOT HISTORY"
]) {
    assert.ok(card.includes(text), text);
}
assert.match(card, /signal archivePairRequested\(int earlier, int later\)/);
assert.match(card, /readonly property var displayedArchiveDiff:/);
assert.match(card, /available: card\.archiveEarlierPosition > 1/);
assert.match(card, /available: card\.archiveLaterPosition[\s\S]*?< card\.archiveSnapshotCount/);
assert.equal((card.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bFileView\s*\{/g) || []).length, 0);

console.log("Weather M21 arbitrary retained snapshot pair comparison: PASS");
