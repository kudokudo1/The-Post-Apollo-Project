#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
const policyPath = "widgets/weather/StationDossierCapturePolicy.js";
function load(rel) {
    const ctx = {Date, Number, String, Math, JSON, Object, Array, isFinite, isNaN};
    vm.runInNewContext(read(rel).replace(/^\.pragma library\s*/m, ""), ctx);
    return ctx;
}
const p = load(policyPath);
const source = load("widgets/weather/StationDossierPreviewPolicy.js");
const now = Date.UTC(2026, 10, 2, 20, 0, 0);
const selected = {
    sourceId:"gdacs", sourceLabel:"GDACS", id:"FL:900:1",
    title:"Sample flood", typeLabel:"FLOOD",
    latitude:-33.8, longitude:-151.2, timeMs:now - 3600000
};
const other = {
    sourceId:"usgs", sourceLabel:"USGS", id:"earthquake-native-id",
    title:"Nearby observation", typeLabel:"EARTHQUAKE",
    latitude:-33.9, longitude:-151.1, timeMs:now - 2700000,
    distanceKm:20
};
const radar = {
    available:true, covered:true,
    timeMs:now - 900000, receivedAtMs:now - 60000,
    usingCache:true, frameLabel:"-15M"
};
const lightning = {
    available:true, covered:true,
    timeMs:now - 600000, receivedAtMs:now - 40000,
    usingCache:false, windowMinutes:15
};
const flood = {
    relevant:true, available:true,
    gaugeId:"ABCD", gaugeName:"River",
    eventGaugeDistanceKm:80, receivedAtMs:now - 30000,
    observedCategory:"ACTION",
    latestObserved:{timeMs:now - 500000, value:8.5, units:"ft"},
    thresholdContext:{supported:false, reason:"CLAIM WITHHELD"}
};
const timelines = [{
    sourceLabel:"NOAA MRMS",
    provenanceGroup:"REMOTE SENSING", kind:"RADAR FRAME",
    label:"Source frame", timeMs:now - 900000,
    receivedAtMs:now - 60000, provenance:"LOADED FRAME TIME",
    freshnessMode:"SNAPSHOT", runtimeSourceId:"mrms-radar"
}];
const relations = [{
    sourceLabel:"NOAA MRMS", evidenceClass:"REMOTE SENSING",
    relationClass:"FRAME COVERAGE",
    spatialLabel:"LOADED FRAME COVERS POINT",
    temporalLabel:"15M BEFORE SOURCE",
    timeBand:"WITHIN 1H", timeDeltaMinutes:15,
    distanceKm:-1,
    reason:"FRAME COVERS THE EVENT POINT",
    limitation:"CANNOT INTERPRET PIXELS OR ATTRIBUTE INCIDENT"
}];
const preview = source.preview(
    selected, [other], radar, lightning, flood,
    timelines, relations, now - 1000
);
assert.equal(preview.ok, true);
let inspection = p.review(preview, now);
assert.equal(inspection.ready, true);
assert.equal(inspection.reason, "REVIEWABLE_NOT_SAVED");
assert.equal(inspection.saved, false);
assert.ok(inspection.characterCount > 0);
assert.ok(inspection.characterCount <= p.MAX_CHARACTERS);
let result = p.stage(preview, now, false);
assert.equal(result.ok, false);
assert.equal(result.reason, "EXPLICIT_OPERATOR_REQUEST_REQUIRED");
assert.equal(result.candidate, null);
result = p.stage(preview, now, true);
assert.equal(result.ok, true);
assert.equal(result.candidate.state, "UNSAVED_REVIEW_ONLY");
assert.equal(result.candidate.format, "post-apollo.weather-dossier-candidate.v0");
assert.equal(result.candidate.semantics.persistence, "NONE");
assert.equal(result.candidate.semantics.incidentMerge, false);
assert.equal(result.candidate.assembledAtMs, now - 1000);
assert.equal(result.candidate.reviewedAtMs, now);
assert.equal(result.candidate.selectedEvent.sourceId, "gdacs");
assert.equal(result.candidate.selectedEvent.eventId, "FL:900:1");
assert.equal(result.candidate.selectedEvent.point.latitude, -33.8);
assert.equal(result.candidate.selectedEvent.point.longitude, -151.2);
assert.equal(result.candidate.counts.nearby, 1);
assert.equal(result.candidate.counts.operational, 3);
assert.equal(result.candidate.counts.timeline, 1);
assert.equal(result.candidate.counts.relationships, 1);
assert.equal(result.candidate.nearbyEvents[0].sourceId, "usgs");
assert.equal(result.candidate.nearbyEvents[0].eventId, "earthquake-native-id");
assert.equal(result.candidate.operationalEvidence[0].sourceTimeMs, now - 900000);
assert.equal(result.candidate.operationalEvidence[0].receivedAtMs, now - 60000);
assert.equal(result.candidate.operationalEvidence[2].thresholdSupported, false);
assert.equal(result.candidate.evidenceTimeline[0].freshnessMode, "SNAPSHOT");
assert.equal(result.candidate.relationships[0].sameIncidentClaim, false);
assert.equal("payload" in result.candidate.selectedEvent, false);
assert.equal("rawPixels" in result.candidate.operationalEvidence[0], false);

// Explicit field projection must not retain mutable input references.
const candidate = result.candidate;
preview.dossier.selectedEvent.title = "CHANGED AFTER STAGE";
preview.dossier.nearbyEvents[0].title = "CHANGED AFTER STAGE";
preview.dossier.operationalEvidence[0].receivedAtMs = now;
preview.dossier.relationships[0].limitation = "CHANGED AFTER STAGE";
assert.equal(candidate.selectedEvent.title, "Sample flood");
assert.equal(candidate.nearbyEvents[0].title, "Nearby observation");
assert.equal(candidate.operationalEvidence[0].receivedAtMs, now - 60000);
assert.equal(candidate.relationships[0].limitation,
    "CANNOT INTERPRET PIXELS OR ATTRIBUTE INCIDENT");

const clone = () => JSON.parse(JSON.stringify(preview));
function rejected(change, reason) {
    const copy = clone();
    change(copy.dossier);
    const blocked = p.stage(copy, now, true);
    assert.equal(blocked.ok, false, reason);
    assert.equal(blocked.reason, reason);
    assert.equal(blocked.candidate, null);
}
rejected(d => { d.format = "unknown"; }, "PREVIEW_FORMAT_UNSUPPORTED");
rejected(d => { d.semantics.incidentMerge = true; }, "PREVIEW_SEMANTICS_UNTRUSTED");
rejected(d => { d.semantics.relationshipMeaning = "SAME_INCIDENT"; },
    "PREVIEW_SEMANTICS_UNTRUSTED");
rejected(d => { d.semantics.rawFrameBytes = "INCLUDED"; },
    "PREVIEW_SEMANTICS_UNTRUSTED");
rejected(d => { d.selectedEvent.eventId = ""; }, "INVALID_PROVIDER_NATIVE_IDENTITY");
rejected(d => { d.selectedEvent.sourceId = "unknown"; }, "INVALID_PROVIDER_NATIVE_IDENTITY");
rejected(d => { d.selectedEvent.point.longitude = -200; }, "INVALID_PROVIDER_NATIVE_IDENTITY");
rejected(d => { d.counts.nearby = 100; }, "EVIDENCE_BOUNDS_OR_COUNTS_INVALID");
rejected(d => { d.nearbyEvents[0].sourceId = "gdacs"; }, "NEARBY_PROVENANCE_INVALID");
rejected(d => { d.nearbyEvents[0].sameIncidentClaim = true; }, "NEARBY_PROVENANCE_INVALID");
rejected(d => { d.nearbyEvents[0].distanceKm = 400; }, "NEARBY_PROVENANCE_INVALID");
rejected(d => { d.nearbyEvents.push(d.nearbyEvents[0]); d.counts.nearby=2; },
    "NEARBY_IDENTITY_DUPLICATED");
rejected(d => { d.operationalEvidence[0].sameIncidentClaim=true; },
    "OPERATIONAL_PROVENANCE_INVALID");
rejected(d => { d.operationalEvidence[0].interpretation="RADAR PROVED INCIDENT"; },
    "OPERATIONAL_PROVENANCE_INVALID");
rejected(d => { d.operationalEvidence[1].limitation="NO LIMITATION"; },
    "OPERATIONAL_PROVENANCE_INVALID");
rejected(d => { d.operationalEvidence[0].receivedAtMs=-999; },
    "OPERATIONAL_PROVENANCE_INVALID");
rejected(d => { d.operationalEvidence[2].eventGaugeDistanceKm=200; },
    "GAUGE_IDENTITY_OR_DISTANCE_INVALID");
rejected(d => { d.evidenceTimeline[0].sourceTimeMs=-1; },
    "TIMELINE_PROVENANCE_INVALID");
rejected(d => { d.evidenceTimeline[0].provenance=""; },
    "TIMELINE_PROVENANCE_INVALID");
rejected(d => { d.relationships[0].limitation=""; },
    "RELATIONSHIP_LIMITATION_INVALID");
rejected(d => { d.relationships[0].sameIncidentClaim=true; },
    "RELATIONSHIP_LIMITATION_INVALID");
rejected(d => { d.relationships[0].distanceKm=-9; },
    "RELATIONSHIP_LIMITATION_INVALID");

let old = p.review(preview, now + p.MAX_REVIEW_AGE_MS + 5000);
assert.equal(old.ready, false);
assert.equal(old.reason, "PREVIEW_TOO_OLD_OR_CLOCK_INVALID");
old = p.review(preview, now - 60000);
assert.equal(old.ready, false);
assert.equal(old.reason, "PREVIEW_TOO_OLD_OR_CLOCK_INVALID");
assert.equal(p.review(null, now).reason, "PREVIEW_UNAVAILABLE");

// Empty-but-valid M22 preview may be reviewed; missing external data is not
// replaced with invented evidence, nor is the event treated as merged.
const empty = source.preview(
    {...selected, id:"FL:901:1"},
    [], null, null, null, [], [], now - 1000
);
const emptyReview = p.review(empty, now);
assert.equal(emptyReview.ready, true);
const emptyStage = p.stage(empty, now, true);
assert.equal(emptyStage.candidate.counts.operational, 0);
assert.equal(emptyStage.candidate.counts.nearby, 0);

const map = read("widgets/weather/StationDiscovery.qml");
const card = read("widgets/weather/StationEventContextCard.qml");
const policy = read(policyPath);
assert.ok(map.includes('StationDossierCapturePolicy.js" as DossierCapturePolicy'));
assert.ok(map.includes("readonly property var selectedDossierCaptureReview:"));
assert.ok(map.includes("DossierCapturePolicy.review("));
assert.ok(map.includes("stationDiscovery.selectedDossierCaptureReview"));
assert.ok(card.includes("M23 DOSSIER ADMISSION // "));
assert.ok(card.includes("REVIEWABLE // NOT SAVED"));
assert.equal((map.match(/eventArchiveStore\.archiveEvent\(/g)||[]).length,1);
assert.equal((policy.match(/\bFileView\s*\{/g)||[]).length,0);
assert.equal((policy.match(/\bTimer\s*\{/g)||[]).length,0);
assert.equal((policy.match(/\bProcess\s*\{/g)||[]).length,0);
assert.equal(policy.includes("Quickshell.dataDir"),false);
assert.equal((map.match(/DossierCapturePolicy\.stage\(/g)||[]).length,0);
console.log("Weather M23 no-write dossier admission contract: PASS");
