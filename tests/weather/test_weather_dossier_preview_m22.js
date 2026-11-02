#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
const code = read("widgets/weather/StationDossierPreviewPolicy.js");
const ctx = {Date, Number, String, Math, JSON, Object, Array, isFinite, isNaN};
vm.runInNewContext(code.replace(/^\.pragma library\s*/m, ""), ctx);

const now = Date.UTC(2026, 10, 2, 20, 0, 0);
const selected = {
    sourceId:"gdacs", sourceLabel:"GDACS", id:"FL:900:1",
    title:"Flood event", typeLabel:"FLOOD",
    latitude:38.9, longitude:-77.1, timeMs:now - 3600000
};
const companions = [];
for (let i = 0; i < 15; i++) {
    companions.push({
        sourceId:i % 2 === 0 ? "usgs" : "eonet",
        id:"id-" + i,
        sourceLabel:i % 2 === 0 ? "USGS" : "NASA EONET",
        title:"Nearby independent record " + i,
        typeLabel:"EVENT", latitude:39, longitude:-77.2,
        timeMs:now - i * 60000, distanceKm:20 + i
    });
}
const radar = {
    available:true, covered:true, timeMs:now - 900000,
    receivedAtMs:now - 100000, frameLabel:"-15M", usingCache:true
};
const lightning = {
    available:true, covered:true, timeMs:now - 600000,
    receivedAtMs:now - 90000, windowMinutes:15, usingCache:false
};
const flood = {
    relevant:true, available:true, eventGaugeDistanceKm:60,
    gaugeId:"ABCD", gaugeName:"River Gauge",
    receivedAtMs:now - 30000,
    latestObserved:{timeMs:now - 300000,value:10.5,units:"ft"},
    observedCategory:"MINOR",
    thresholdContext:{supported:true,reason:"THRESHOLD MET"}
};
const timeline = Array.from({length:20}, (_,i) => ({
    sourceLabel:"NOAA MRMS", provenanceGroup:"REMOTE SENSING",
    kind:"RADAR FRAME", label:"Loaded Frame",
    timeMs:now - (i + 1) * 60000,
    receivedAtMs:now - 25000,
    freshnessMode:"SNAPSHOT", runtimeSourceId:"mrms-radar",
    provenance:"LOADED FRAME TIME"
}));
const relationships = Array.from({length:20}, (_,i) => ({
    sourceLabel:"NOAA MRMS",
    evidenceClass:"REMOTE SENSING",
    relationClass:"FRAME COVERAGE",
    spatialLabel:"EVENT POINT INSIDE LOADED MRMS FRAME",
    temporalLabel:"OFFSET " + i,
    timeBand:"WITHIN 1H", timeDeltaMinutes:i,
    distanceKm:-1,
    reason:"FRAME COVERS EVENT POINT",
    limitation:"NOT A PIXEL INTERPRETATION"
}));
const base = ctx.preview(
    selected, companions, radar, lightning, flood,
    timeline, relationships, now
);
assert.equal(base.ok, true);
const dossier = base.dossier;
assert.equal(dossier.state, "VOLATILE_PREVIEW_ONLY");
assert.equal(dossier.semantics.persistence, "NONE");
assert.equal(dossier.semantics.incidentMerge, false);
assert.equal(dossier.selectedEvent.sourceId, "gdacs");
assert.equal(dossier.selectedEvent.eventId, "FL:900:1");
assert.equal(dossier.selectedEvent.sourceTimeMs, now - 3600000);
assert.equal(dossier.assembledAtMs, now);
assert.equal(dossier.counts.nearby, 6);
assert.equal(dossier.counts.operational, 3);
assert.equal(dossier.counts.timeline, 8);
assert.equal(dossier.counts.relationships, 8);
assert.equal(dossier.operationalEvidence[0].provider, "NOAA MRMS");
assert.equal(dossier.operationalEvidence[0].receivedAtMs, now - 100000);
assert.equal(dossier.operationalEvidence[0].sourceTimeMs, now - 900000);
assert.equal(dossier.operationalEvidence[1].provider, "NOAA NOWCOAST");
assert.equal(dossier.operationalEvidence[2].provider, "NOAA NWPS");
assert.equal(dossier.operationalEvidence[2].gaugeId, "ABCD");
assert.equal(dossier.operationalEvidence[2].thresholdSupported, true);
assert.equal(dossier.operationalEvidence.every(row => row.sameIncidentClaim === false), true);
assert.equal(dossier.nearbyEvents.every(row => row.sourceId !== "gdacs"), true);
assert.equal(dossier.relationships.every(row => row.sameIncidentClaim === false), true);
assert.equal(dossier.evidenceTimeline.every(row => row.sameIncidentClaim === false), true);
assert.equal(dossier.evidenceTimeline[0].freshnessMode, "SNAPSHOT");
assert.equal(dossier.evidenceTimeline[0].receivedAtMs, now - 25000);
assert.equal("payload" in dossier.selectedEvent, false);
assert.equal("rawPixels" in dossier.operationalEvidence[0], false);

// Input mutation after capture cannot silently change a preview object.
selected.title = "MODIFIED AFTER PREVIEW";
companions[0].title = "MODIFIED AFTER PREVIEW";
radar.receivedAtMs = now;
relationships[0].limitation = "MODIFIED AFTER PREVIEW";
assert.equal(dossier.selectedEvent.title, "Flood event");
assert.equal(dossier.nearbyEvents[0].title, "Nearby independent record 0");
assert.equal(dossier.operationalEvidence[0].receivedAtMs, now - 100000);
assert.equal(dossier.relationships[0].limitation, "NOT A PIXEL INTERPRETATION");

// Incorrect source identities must not fall back to a merged incident.
for (const bad of [
    {...selected, id:""},
    {...selected, sourceId:"unknown"},
    null
]) {
    const result = ctx.preview(bad, companions, radar, lightning, flood,
        timeline, relationships, now);
    assert.equal(result.ok, false);
    assert.equal(result.dossier, null);
}
assert.equal(ctx.preview(
    {...selected, id:"FL:900:1"}, [], null, null, null, [], [], -1
).ok, false);

// Proximity/gauge/coverage gates still matter, even if an input is malformed.
const guarded = ctx.preview(
    {...selected, id:"FL:900:1"},
    [
        {...companions[0], sourceId:"gdacs"},
        {...companions[0], id:""},
        {...companions[0], distanceKm:300},
        {...companions[0], sourceId:"usgs", id:"good", distanceKm:10}
    ],
    {...radar, covered:false},
    {...lightning, covered:false},
    {...flood, eventGaugeDistanceKm:101},
    [], [], now
);
assert.equal(guarded.ok, true);
assert.equal(guarded.dossier.counts.nearby, 1);
assert.equal(guarded.dossier.counts.operational, 0);
assert.equal(guarded.dossier.nearbyEvents[0].eventId, "good");

// No source event point -> no implied frame coverage, nearby or gauge relation.
const noPoint = ctx.preview(
    {...selected, id:"FL:900:1", latitude:null, longitude:null},
    companions, radar, lightning, flood, timeline, relationships, now
);
assert.equal(noPoint.ok, true);
assert.equal(noPoint.dossier.selectedEvent.point, null);
assert.equal(noPoint.dossier.counts.nearby, 0);
assert.equal(noPoint.dossier.counts.operational, 0);

// Signed coordinates are real locations; negative non-time sentinels are not.
const signed = ctx.preview(
    {...selected, id:"FL:900:1", latitude:-33.8, longitude:-151.2},
    [], {available:true,covered:true,timeMs:-1,receivedAtMs:-1},
    null, null, [], [], now
).dossier;
assert.equal(signed.selectedEvent.point.latitude, -33.8);
assert.equal(signed.selectedEvent.point.longitude, -151.2);
assert.equal(signed.operationalEvidence[0].sourceTimeMs, -1);
assert.equal(signed.operationalEvidence[0].receivedAtMs, -1);

const map = read("widgets/weather/StationDiscovery.qml");
const card = read("widgets/weather/StationEventContextCard.qml");
assert.ok(map.includes('StationDossierPreviewPolicy.js" as DossierPreviewPolicy'));
assert.ok(map.includes("readonly property var selectedDossierPreview:"));
assert.ok(map.includes("DossierPreviewPolicy.preview("));
assert.ok(map.includes("dossierPreview:"));
assert.ok(map.includes("stationDiscovery.selectedDossierPreview"));
assert.ok(card.includes("DOSSIER PREVIEW // VOLATILE // NO DISK WRITE"));
assert.ok(card.includes("NO INCIDENT MERGE // NO CAUSAL CLAIM"));
assert.ok(card.includes("dossierPreviewReady"));
assert.equal((map.match(/eventArchiveStore\.archiveEvent\(/g) || []).length, 1);
assert.equal((code.match(/\bFileView\s*\{/g) || []).length, 0);
assert.equal((code.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((code.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal(code.includes("JSON.stringify("), false);

console.log("Weather M22 volatile dossier preview: PASS");
