#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");
function policy(file) {
    const ctx = {
        Date, Math, Number, String, Object, Array, RegExp, JSON,
        isFinite, isNaN
    };
    vm.runInNewContext(read(file).replace(/^\.pragma library\s*/m, ""), ctx);
    return ctx;
}
const m22 = policy("widgets/weather/StationDossierPreviewPolicy.js");
const m23 = policy("widgets/weather/StationDossierCapturePolicy.js");
const m24Path = "widgets/weather/StationDossierSerializationPolicy.js";
const m24 = policy(m24Path);

const now = Date.UTC(2026, 10, 2, 20, 0, 0);
const selected = {
    sourceId:"gdacs", sourceLabel:"GDACS", id:"FL:1000:1",
    title:"Flood A", typeLabel:"FLOOD",
    latitude:-33.87, longitude:-151.21,
    timeMs:now - 3600000
};
const nearby = [{
    sourceId:"usgs", sourceLabel:"USGS", id:"quake-native-100",
    title:"Separate nearby quake", typeLabel:"EARTHQUAKE",
    latitude:-33.8, longitude:-151.1,
    timeMs:now - 2000000, distanceKm:13
}];
const radar = {
    available:true, covered:true, timeMs:now - 300000,
    receivedAtMs:now - 25000, frameLabel:"-5M", usingCache:true
};
const lightning = {
    available:true, covered:true, timeMs:now - 600000,
    receivedAtMs:now - 21000, windowMinutes:15, usingCache:false
};
const flood = {
    relevant:true, available:true, gaugeId:"ABCD",
    gaugeName:"Gauge A", eventGaugeDistanceKm:50,
    receivedAtMs:now - 11000,
    latestObserved:{timeMs:now - 250000, value:7.5, units:"ft"},
    observedCategory:"MINOR",
    thresholdContext:{supported:false, reason:"CLAIM WITHHELD"}
};
const timelines = [{
    sourceLabel:"NOAA MRMS", provenanceGroup:"REMOTE SENSING",
    kind:"RADAR FRAME", label:"Latest loaded frame",
    timeMs:now - 300000, receivedAtMs:now - 25000,
    provenance:"LOADED FRAME TIME", freshnessMode:"SNAPSHOT",
    runtimeSourceId:"mrms-radar"
}];
const relations = [{
    sourceLabel:"NOAA MRMS", evidenceClass:"REMOTE SENSING",
    relationClass:"FRAME COVERAGE",
    spatialLabel:"EVENT POINT INSIDE FRAME",
    temporalLabel:"5M BEFORE SOURCE",
    timeBand:"WITHIN 1H", timeDeltaMinutes:5,
    distanceKm:-1, reason:"FRAME COVERS EVENT POINT",
    limitation:"FRAME DOES NOT PROVE CAUSALITY"
}];
const preview = m22.preview(
    selected, nearby, radar, lightning, flood,
    timelines, relations, now - 1000
);
assert.equal(preview.ok, true);
const staged = m23.stage(preview, now, true);
assert.equal(staged.ok, true);
assert.equal(staged.candidate.state, "UNSAVED_REVIEW_ONLY");
let encoded = m24.serialize(staged);
assert.equal(encoded.ok, true);
assert.equal(encoded.reason, "SERIALIZED_IN_MEMORY_ONLY");
assert.ok(encoded.characters > 0);
assert.ok(encoded.characters <= m24.MAX_ENVELOPE_CHARS);
assert.equal(encoded.envelope.version, 0);
assert.equal(encoded.envelope.state, "UNSAVED_TRANSPORT_PROBE_ONLY");

let loaded = m24.inspect(encoded.text);
assert.equal(loaded.ok, true);
assert.equal(loaded.reason, "PARSED_IN_MEMORY_ONLY");
assert.equal(JSON.stringify(loaded.envelope), encoded.text);
assert.equal(loaded.envelope.candidate.selectedEvent.sourceId, "gdacs");
assert.equal(loaded.envelope.candidate.selectedEvent.eventId, "FL:1000:1");
assert.equal(loaded.envelope.candidate.selectedEvent.point.latitude, -33.87);
assert.equal(loaded.envelope.candidate.nearbyEvents[0].sourceId, "usgs");
assert.equal(loaded.envelope.candidate.nearbyEvents[0].eventId, "quake-native-100");
assert.equal(loaded.envelope.candidate.operationalEvidence[0].provider, "NOAA MRMS");
assert.equal(loaded.envelope.candidate.operationalEvidence[0].sourceTimeMs,
    now - 300000);
assert.equal(loaded.envelope.candidate.operationalEvidence[0].receivedAtMs,
    now - 25000);
assert.equal(loaded.envelope.candidate.operationalEvidence[2].provider,
    "NOAA NWPS");
assert.equal(loaded.envelope.candidate.operationalEvidence[2].gaugeId, "ABCD");
assert.equal(loaded.envelope.candidate.relationships[0].limitation,
    "FRAME DOES NOT PROVE CAUSALITY");
assert.equal(loaded.envelope.candidate.semantics.incidentMerge, false);
assert.equal(loaded.envelope.candidate.semantics.persistence, "NONE");
const check = m24.probe(staged);
assert.equal(check.ok, true);
assert.equal(check.equal, true);
assert.equal(check.characters, encoded.characters);

// No input references or historical reinterpretation after a probe.
staged.candidate.selectedEvent.title = "changed later";
staged.candidate.nearbyEvents[0].title = "changed later";
staged.candidate.relationships[0].limitation = "changed later";
assert.equal(loaded.envelope.candidate.selectedEvent.title, "Flood A");
assert.equal(loaded.envelope.candidate.nearbyEvents[0].title, "Separate nearby quake");
assert.equal(loaded.envelope.candidate.relationships[0].limitation,
    "FRAME DOES NOT PROVE CAUSALITY");

const good = JSON.parse(encoded.text);
function badEnvelope(edit, reason) {
    const payload = JSON.parse(JSON.stringify(good));
    edit(payload);
    const result = m24.inspect(JSON.stringify(payload));
    assert.equal(result.ok, false);
    assert.equal(result.reason, reason);
    assert.equal(result.envelope, null);
}
badEnvelope(x => {x.version = 1;}, "UNSUPPORTED_VERSION");
badEnvelope(x => {x.state = "SETTLED";}, "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.unexpected = "EXTRA";}, "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.extra = "UNVERIFIED_DATA";},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.format = "unknown";},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.selectedEvent.sourceId = "unknown";},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.selectedEvent.point.latitude = -91;},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.counts.nearby = 2;},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.nearbyEvents[0].sourceId = "gdacs";},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.nearbyEvents[0].sameIncidentClaim = true;},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.nearbyEvents[0].rawPixels = [1,2];},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.operationalEvidence[0].provider="UNVERIFIED";},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.operationalEvidence[0].limitation="";},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.operationalEvidence[0].sourceTimeMs=-99;},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.operationalEvidence.push(x.candidate.operationalEvidence[0]);
    x.candidate.counts.operational=4;},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.evidenceTimeline[0].provenance="";},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.relationships[0].sameIncidentClaim=true;},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.semantics.incidentMerge=true;},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.assembledAtMs=0;},
    "INVALID_ENVELOPE_OR_EVIDENCE");
badEnvelope(x => {x.candidate.reviewedAtMs=x.candidate.assembledAtMs-1;},
    "INVALID_ENVELOPE_OR_EVIDENCE");

assert.equal(m24.inspect("{}").reason, "UNKNOWN_FORMAT");
assert.equal(m24.inspect("{bad json").reason, "INVALID_JSON");
assert.equal(m24.inspect("").reason, "INPUT_SIZE_OR_TYPE_INVALID");
assert.equal(m24.inspect("x".repeat(m24.MAX_ENVELOPE_CHARS+1)).reason,
    "INPUT_SIZE_OR_TYPE_INVALID");
assert.equal(m24.serialize(null).reason, "UNTRUSTED_OR_UNSTAGED_CANDIDATE");
assert.equal(m24.serialize({ok:true,candidate:good.candidate}).reason,
    "UNTRUSTED_OR_UNSTAGED_CANDIDATE");
assert.equal(m24.serialize({...m23.stage(preview, now, false)}).ok, false);

// Unknown historical versions fail closed: no implicit migration or repair.
const future = {...good, version:15};
assert.equal(m24.inspect(JSON.stringify(future)).reason, "UNSUPPORTED_VERSION");

// No file, command, process, timer, runtime owner, or filesystem pathname.
const code = read(m24Path);
for (const forbidden of [
    "FileView {", "Process {", "Timer {", "Quickshell.dataDir",
    "setText(", "writeFile(", "unlink(", "readFileSync("
]) {
    assert.equal(code.includes(forbidden), false, forbidden);
}
const store = read("services/weather/WeatherEventArchiveStore.qml");
assert.equal((store.match(/\bFileView\s*\{/g)||[]).length, 1);
const map = read("widgets/weather/StationDiscovery.qml");
assert.equal((map.match(/eventArchiveStore\.archiveEvent\(/g)||[]).length,1);
console.log("Weather M24 in-memory dossier serialization and refusal: PASS");
