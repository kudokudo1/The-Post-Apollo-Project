#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const source = read("services/weather/WeatherEventTimelinePolicy.js");
const ctx = {Date, Math, Number, String, Array, Object, JSON, isFinite};
vm.runInNewContext(source.replace(/^\.pragma library\s*/m, ""), ctx);

for (const fn of [
    "anchorKey", "relationKey", "relationState", "difference",
    "matchingDossiers", "timelineForAnchor",
    "sourceTransitionLabel", "recordTransitionLabel"
])
    assert.equal(typeof ctx[fn], "function", fn);

const anchor = {
    source: "GDACS",
    id: "WF:7:1",
    title: "Example Wildfire",
    hazard: "fire",
    latitude: 38.5,
    longitude: -77.2,
    observedMs: Date.parse("2026-10-31T18:00:00Z")
};
assert.equal(ctx.anchorKey(anchor), "GDACS|WF:7:1");
assert.equal(ctx.anchorKey({...anchor, id:""}), "");

const eonet = {
    source: "NASA EONET",
    id: "EONET_7",
    title: "Example Fire",
    hazard: "fire",
    latitude: 38.55,
    longitude: -77.15,
    distanceKm: 7.2,
    deltaHours: 1.5,
    relationKind: "TIME + SPACE",
    mentionOnly: false,
    semantics: "RELATED SOURCE CONTEXT, NOT SAME-EVENT IDENTITY"
};
const firms = {
    source: "NASA FIRMS",
    id: "FIRMS_7",
    title: "VIIRS HOTSPOT",
    hazard: "fire",
    latitude: 38.51,
    longitude: -77.19,
    distanceKm: 1.2,
    deltaHours: 0.3,
    relationKind: "TIME + SPACE",
    mentionOnly: false,
    semantics: "RELATED SOURCE CONTEXT, NOT SAME-EVENT IDENTITY"
};
const mention = {
    source: "GDELT GKG",
    id: "PLACE_7",
    title: "Nearby Place",
    hazard: "unknown",
    latitude: 38.52,
    longitude: -77.18,
    distanceKm: 2.4,
    deltaHours: -1,
    relationKind: "MENTION NEARBY",
    mentionOnly: true,
    semantics: "ARTICLE MENTION NEAR AN EVENT ANCHOR, NOT VERIFIED EVENT LOCATION"
};
const quake = {
    source: "USGS",
    id: "q-unrelated",
    title: "M4.0 Example",
    hazard: "earthquake",
    latitude: 39,
    longitude: -77,
    distanceKm: 55,
    deltaHours: 1,
    relationKind: "TIME + SPACE",
    mentionOnly: false,
    semantics: "RELATED SOURCE CONTEXT, NOT SAME-EVENT IDENTITY"
};

const t1 = Date.parse("2026-11-01T00:00:00Z");
const t2 = Date.parse("2026-11-01T01:00:00Z");
const t3 = Date.parse("2026-11-01T03:30:00Z");
const document = {
    version: 1,
    revision: 4,
    dossiers: [
        {
            id: "snap3",
            savedAtMs: t3,
            anchor,
            relations: [firms, mention]
        },
        {
            id: "other-source",
            savedAtMs: t2 + 500,
            anchor: {...anchor, source:"NASA EONET", id:"EONET_7"},
            relations: [quake]
        },
        {
            id: "snap2",
            savedAtMs: t2,
            anchor,
            relations: [eonet, firms, mention]
        },
        {
            id: "snap1",
            savedAtMs: t1,
            anchor,
            relations: [eonet]
        }
    ]
};

const matches = Array.from(ctx.matchingDossiers(document, anchor, 24));
assert.deepEqual(matches.map(x => x.id), ["snap1","snap2","snap3"]);
assert.equal(
    Array.from(ctx.matchingDossiers(
        document, {...anchor, source:"NASA EONET", id:"EONET_7"}, 24
    )).length,
    1,
    "different providers remain different timelines"
);

const timeline = ctx.timelineForAnchor(document, anchor, 24);
assert.equal(timeline.anchorKey, "GDACS|WF:7:1");
assert.equal(timeline.snapshots.length, 3);
assert.equal(timeline.summary.snapshotCount, 3);
assert.equal(timeline.summary.firstSavedMs, t1);
assert.equal(timeline.summary.lastSavedMs, t3);
assert.ok(Math.abs(timeline.summary.spanHours - 3.5) < 1e-9);
assert.equal(timeline.summary.uniqueSources, 3);
assert.equal(timeline.summary.maxRelations, 3);

const s1 = timeline.snapshots[0];
assert.equal(s1.baseline, true);
assert.equal(s1.relationCount, 1);
assert.deepEqual(Array.from(s1.sources), ["NASA EONET"]);
assert.deepEqual(Array.from(s1.addedSources), ["NASA EONET"]);
assert.equal(s1.addedCount, 1);
assert.equal(s1.removedCount, 0);
assert.equal(s1.relationDelta, 0);
assert.equal(ctx.sourceTransitionLabel(s1), "BASE SOURCES // NASA EONET");
assert.equal(ctx.recordTransitionLabel(s1), "BASELINE // 1 RELATED RECORDS");

const s2 = timeline.snapshots[1];
assert.equal(s2.baseline, false);
assert.equal(s2.relationCount, 3);
assert.deepEqual(Array.from(s2.addedSources), ["GDELT GKG","NASA FIRMS"]);
assert.deepEqual(Array.from(s2.removedSources), []);
assert.equal(s2.addedCount, 2);
assert.equal(s2.removedCount, 0);
assert.equal(s2.relationDelta, 2);
assert.equal(s2.mentionCount, 1);
assert.equal(s2.timeSpaceCount, 2);
assert.match(ctx.sourceTransitionLabel(s2), /GDELT GKG/);
assert.match(ctx.sourceTransitionLabel(s2), /NASA FIRMS/);
assert.equal(ctx.recordTransitionLabel(s2), "RECORDS +2 / -0 // TOTAL 3 // Δ +2");

const s3 = timeline.snapshots[2];
assert.equal(s3.relationCount, 2);
assert.deepEqual(Array.from(s3.addedSources), []);
assert.deepEqual(Array.from(s3.removedSources), ["NASA EONET"]);
assert.equal(s3.addedCount, 0);
assert.equal(s3.removedCount, 1);
assert.equal(s3.relationDelta, -1);
assert.equal(ctx.sourceTransitionLabel(s3), "- NASA EONET");
assert.equal(ctx.recordTransitionLabel(s3), "RECORDS +0 / -1 // TOTAL 2 // Δ -1");

const fallbackKey = ctx.relationKey({
    source:"GDELT GKG", id:"", title:"Place",
    latitude:38.123456, longitude:-77.123456
});
assert.equal(fallbackKey, "GDELT GKG|@38.1235,-77.1235|Place");

const noTimeline = ctx.timelineForAnchor(document, {...anchor, id:"missing"}, 24);
assert.equal(noTimeline.snapshots.length, 0);
assert.equal(noTimeline.summary.snapshotCount, 0);

const policyText = read("services/weather/WeatherEventTimelinePolicy.js");
assert.doesNotMatch(policyText, /\bProcess\s*\{|\bTimer\s*\{|FileView|curl|XMLHttpRequest/);
assert.match(policyText, /source \+ "\|" \+ id/);
assert.match(policyText, /Cross-provider relationships remain context/);

console.log("Weather MAP exact-source event dossier timelines: PASS");
