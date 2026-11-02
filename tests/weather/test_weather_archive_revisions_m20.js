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

for (const fn of [
    "fieldLabel",
    "comparableFields",
    "valuesEqual",
    "displayFieldValue",
    "snapshotDiff",
    "revisionRows",
    "latestDiff"
]) {
    assert.equal(typeof ctx[fn], "function", fn);
}

const minute = 60000;
const now = Date.UTC(2026, 10, 2, 19, 0, 0);

const baseGdacs = {
    id:"FL:900:1",
    eventId:"900",
    episodeId:"1",
    eventType:"FL",
    eventTypeLabel:"FLOOD",
    name:"Archive Diff Flood",
    alertLevel:"ORANGE",
    alertScore:2,
    isCurrent:true,
    country:"United States",
    iso3:"USA",
    latitude:38.90,
    longitude:-77.10,
    fromUtc:"2026-11-02 12:00 UTC",
    toUtc:"2026-11-02 18:00 UTC",
    timeMs:now - 60 * minute,
    severity:2.2,
    severityText:"Moderate flooding",
    severityUnit:"m",
    reportUrl:"https://example.invalid/report",
    detailsUrl:"https://example.invalid/details"
};

const changedGdacs = {
    ...baseGdacs,
    alertLevel:"RED",
    alertScore:3,
    isCurrent:false,
    longitude:-77.25,
    severity:4.1,
    severityText:"Severe flooding",
    toUtc:"2026-11-02 19:00 UTC",
    timeMs:now - 10 * minute
};

const before = ctx.normalizeSnapshot(
    "gdacs", baseGdacs, now - 20 * minute
);
const after = ctx.normalizeSnapshot(
    "gdacs", changedGdacs, now - 5 * minute
);
assert.ok(before);
assert.ok(after);

let diff = ctx.snapshotDiff(before, after);
assert.equal(diff.available, true);
assert.equal(diff.sameIdentity, true);
assert.equal(diff.sourceId, "gdacs");
assert.equal(diff.eventId, baseGdacs.id);
assert.ok(diff.changedCount >= 7);

const byKey = Object.fromEntries(
    Array.from(diff.changes).map(row => [row.key, row])
);
for (const key of [
    "alertLevel",
    "alertScore",
    "isCurrent",
    "longitude",
    "severity",
    "severityText",
    "toUtc",
    "sourceTimeMs"
]) {
    assert.ok(byKey[key], key);
}

assert.equal(byKey.alertLevel.label, "ALERT LEVEL");
assert.equal(byKey.alertLevel.beforeText, "ORANGE");
assert.equal(byKey.alertLevel.afterText, "RED");
assert.equal(byKey.isCurrent.beforeText, "TRUE");
assert.equal(byKey.isCurrent.afterText, "FALSE");
assert.equal(byKey.longitude.beforeText, "-77.1");
assert.equal(byKey.longitude.afterText, "-77.25");
assert.equal(byKey.sourceTimeMs.label, "SOURCE TIME");

// Capture time alone is not provider evidence and must not create a diff.
const sameEvidenceLaterCapture = {
    ...before,
    capturedAtMs: before.capturedAtMs + 30 * minute
};
diff = ctx.snapshotDiff(before, sameEvidenceLaterCapture);
assert.equal(diff.available, true);
assert.equal(diff.changedCount, 0);

// Cross-provider or cross-event comparison fails closed.
const otherSource = {...after, sourceId:"usgs", sourceLabel:"USGS"};
diff = ctx.snapshotDiff(before, otherSource);
assert.equal(diff.available, false);
assert.equal(diff.sameIdentity, false);

const otherEvent = {...after, eventId:"FL:901:1", eventKey:"gdacs|FL:901:1"};
diff = ctx.snapshotDiff(before, otherEvent);
assert.equal(diff.available, false);

// Display semantics preserve signed coordinates but hide negative sentinels.
assert.equal(ctx.displayFieldValue("longitude", -77.25), "-77.25");
assert.equal(ctx.displayFieldValue("latitude", -12.5), "-12.5");
assert.equal(ctx.displayFieldValue("severity", -1), "--");
assert.equal(ctx.displayFieldValue("depthKm", -1), "--");
assert.equal(ctx.displayFieldValue("isCurrent", false), "FALSE");
assert.equal(ctx.fieldLabel("frpMw"), "FRP MW");
assert.equal(ctx.fieldLabel("confidenceLabel"), "CONFIDENCE");

let doc = ctx.initialDocument();
let result = ctx.append(
    doc, "gdacs", baseGdacs, now - 20 * minute
);
assert.equal(result.ok, true);
doc = result.document;

result = ctx.append(
    doc, "gdacs", changedGdacs, now - 5 * minute
);
assert.equal(result.ok, true);
doc = result.document;

const revisionRows = Array.from(
    ctx.revisionRows(doc, "gdacs", baseGdacs.id, now, 5)
);
assert.equal(revisionRows.length, 2);
assert.equal(revisionRows[0].position, 2);
assert.equal(revisionRows[0].total, 2);
assert.equal(revisionRows[0].capturedAtMs, now - 5 * minute);
assert.equal(revisionRows[1].position, 1);
assert.equal(revisionRows[1].capturedAtMs, now - 20 * minute);

diff = ctx.latestDiff(doc, "gdacs", baseGdacs.id, now);
assert.equal(diff.available, true);
assert.equal(diff.previousCapturedAtMs, now - 20 * minute);
assert.equal(diff.currentCapturedAtMs, now - 5 * minute);
assert.equal(diff.changedCount, Object.keys(byKey).length);

// One retained snapshot produces an unavailable latest diff, not an invented
// baseline change list.
let one = ctx.initialDocument();
result = ctx.append(one, "gdacs", baseGdacs, now);
assert.equal(result.ok, true);
one = result.document;
diff = ctx.latestDiff(one, "gdacs", baseGdacs.id, now);
assert.equal(diff.available, false);
assert.equal(diff.changedCount, 0);

// Revision query respects the bounded maximum and newest-first ordering.
let many = ctx.initialDocument();
for (let i = 0; i < 7; i++) {
    const row = {
        ...baseGdacs,
        alertScore:i,
        severity:2 + i / 10
    };
    result = ctx.append(
        many,
        "gdacs",
        row,
        now + i * minute
    );
    assert.equal(result.ok, true);
    many = result.document;
}
const limited = Array.from(
    ctx.revisionRows(
        many,
        "gdacs",
        baseGdacs.id,
        now + 10 * minute,
        5
    )
);
assert.equal(limited.length, 5);
assert.deepEqual(
    limited.map(row => row.position),
    [7,6,5,4,3]
);
assert.ok(
    limited.every((row, index) =>
        index === 0
        || limited[index - 1].capturedAtMs > row.capturedAtMs
    )
);

const store = read("services/weather/WeatherEventArchiveStore.qml");
assert.match(store, /function revisionRows\(sourceId, eventId, nowMs, maximum\)/);
assert.match(store, /ArchivePolicy\.revisionRows/);
assert.match(store, /function latestDiff\(sourceId, eventId, nowMs\)/);
assert.match(store, /ArchivePolicy\.latestDiff/);
assert.equal((store.match(/function archiveEvent\(/g) || []).length, 1);
assert.equal((store.match(/\bFileView\s*\{/g) || []).length, 1);
assert.equal((store.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((store.match(/\bProcess\s*\{/g) || []).length, 0);

const map = read("widgets/weather/StationDiscovery.qml");
assert.match(map, /readonly property var selectedArchiveRows:/);
assert.match(map, /eventArchiveStore\.revisionRows\(/);
assert.match(map, /readonly property var selectedArchiveDiff:/);
assert.match(map, /eventArchiveStore\.latestDiff\(/);
assert.match(
    map,
    /archiveRows:\s*stationDiscovery\.selectedArchiveRows/
);
assert.match(
    map,
    /archiveDiff:\s*stationDiscovery\.selectedArchiveDiff/
);
assert.equal(
    (map.match(/eventArchiveStore\.archiveEvent\(/g) || []).length,
    1
);

const card = read("widgets/weather/StationEventContextCard.qml");
for (const phrase of [
    "ARCHIVE HISTORY // SOURCE-NATIVE SNAPSHOTS",
    "BOUNDED SNAPSHOT HISTORY",
    "NOT A PERMANENT REVISION NUMBER",
    "LATEST ARCHIVE DIFF // NEWEST VS PREVIOUS",
    "BASELINE SNAPSHOT ONLY",
    "CAPTURE TIME IS NOT COUNTED AS A PROVIDER CHANGE",
    "EXACT ARCHIVED PROVIDER-FIELD CHANGES",
    "SOURCE IDENTITY UNCHANGED"
]) {
    assert.ok(card.includes(phrase), phrase);
}
assert.match(card, /property var archiveRows: \[\]/);
assert.match(card, /property var archiveDiff: null/);
assert.match(card, /modelData\.position/);
assert.match(card, /modelData\.capturedAtMs/);
assert.match(card, /modelData\.sourceTimeMs/);
assert.match(card, /modelData\.beforeText/);
assert.match(card, /modelData\.afterText/);
assert.equal((card.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bFileView\s*\{/g) || []).length, 0);

console.log("Weather M20 archive revision history and diff: PASS");
