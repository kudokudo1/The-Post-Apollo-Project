#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");
function policy(file) {
    const c = {Date, Number, String, Math, Object, Array, JSON, isFinite, isNaN};
    vm.runInNewContext(read(file).replace(/^\.pragma library\s*/m, ""), c);
    return c;
}
const previewPolicy = policy("widgets/weather/StationDossierPreviewPolicy.js");
const capturePolicy = policy("widgets/weather/StationDossierCapturePolicy.js");
const codec = policy("widgets/weather/StationDossierSerializationPolicy.js");
const archive = policy("services/weather/WeatherDossierArchivePolicy.js");
const now = Date.UTC(2026,10,2,20,0,0);
function stagedFor(id, ms) {
    const preview = previewPolicy.preview({
        sourceId:"gdacs", id:id,
        sourceLabel:"GDACS", title:"Flood " + id,
        typeLabel:"FLOOD", latitude:38.9,
        longitude:-77.1, timeMs:now-1000000
    }, [{
        sourceId:"usgs", sourceLabel:"USGS", id:"quake-"+id,
        title:"Independent quake", typeLabel:"EARTHQUAKE",
        latitude:39, longitude:-77.15,
        timeMs:now-900000, distanceKm:15
    }], {
        available:true, covered:true, frameLabel:"-5M",
        timeMs:now-300000, receivedAtMs:now-20000,
        usingCache:false
    }, null, null, [{
        sourceLabel:"NOAA MRMS", provenanceGroup:"REMOTE SENSING",
        kind:"RADAR FRAME", label:"Frame",
        timeMs:now-300000, receivedAtMs:now-20000,
        provenance:"LOADED FRAME TIME",
        freshnessMode:"SNAPSHOT", runtimeSourceId:"mrms-radar"
    }], [{
        sourceLabel:"NOAA MRMS",
        evidenceClass:"REMOTE SENSING",
        relationClass:"FRAME COVERAGE",
        spatialLabel:"EVENT INSIDE FRAME",
        temporalLabel:"WITHIN 1H", timeBand:"WITHIN 1H",
        timeDeltaMinutes:5, distanceKm:-1,
        reason:"FRAME COVERS EVENT POINT",
        limitation:"DOES NOT INTERPRET PIXELS"
    }], ms-1000);
    assert.equal(preview.ok,true);
    const staged=capturePolicy.stage(preview, ms, true);
    assert.equal(staged.ok,true);
    return staged;
}
const fresh = archive.empty();
const s1 = stagedFor("FL:alpha",now);
let a = archive.append(fresh,s1,now,codec);
assert.equal(a.ok,true);
assert.equal(a.document.revision,1);
assert.equal(a.count,1);
assert.equal(a.document.entries[0].sequence,1);
assert.equal(a.document.entries[0].sourceId,"gdacs");
assert.equal(a.document.entries[0].eventId,"FL:alpha");
assert.equal(a.document.entries[0].capturedAtMs,now);
assert.equal(archive.latest(a.document,"gdacs","FL:alpha",codec).sequence,1);
assert.equal(archive.latest(a.document,"usgs","FL:alpha",codec),null);
assert.equal(archive.countForEvent(a.document,"gdacs","FL:alpha",codec),1);
assert.equal(archive.countForEvent(a.document,"gdacs","FL:beta",codec),0);

// JSON saved by one FileView owner can later be strictly reloaded as-is.
const diskLikeBytes=JSON.stringify(a.document)+"\n";
let loaded=archive.parse(diskLikeBytes,codec);
assert.equal(loaded.ok,true);
assert.equal(loaded.count,1);
assert.equal(loaded.document.revision,1);
assert.equal(loaded.document.entries[0].transport,a.document.entries[0].transport);
assert.equal(loaded.document.entries[0].capturedAtMs,now);
assert.equal(codec.inspect(loaded.document.entries[0].transport).ok,true);

// The second explicit capture has its own sequence and record.
const s2=stagedFor("FL:beta",now+1000);
let b=archive.append(loaded.document,s2,now+1000,codec);
assert.equal(b.ok,true);
assert.equal(b.count,2);
assert.equal(b.document.revision,2);
assert.equal(archive.countForEvent(b.document,"gdacs","FL:beta",codec),1);
assert.equal(archive.countForEvent(b.document,"gdacs","FL:alpha",codec),1);
assert.equal(archive.parse(JSON.stringify(b.document),codec).ok,true);
assert.equal(fresh.entries.length,0);
assert.equal(a.document.entries.length,1);

// Existing history is immutable if an append is rejected.
function rejectDocument(obj,reason) {
    const r=archive.parse(JSON.stringify(obj),codec);
    assert.equal(r.ok,false,reason);
    assert.equal(r.reason,reason);
    assert.equal(r.document,null);
}
let sample=JSON.parse(JSON.stringify(b.document));
sample.version=99;
rejectDocument(sample,"UNSUPPORTED_VERSION");
sample=JSON.parse(JSON.stringify(b.document));
sample.schema="post-apollo.other.v1";
rejectDocument(sample,"INVALID_SCHEMA");
sample=JSON.parse(JSON.stringify(b.document));
sample.records=[];
rejectDocument(sample,"INVALID_DOCUMENT_OR_VERSION");
sample=JSON.parse(JSON.stringify(b.document));
sample.entries[0].sourceId="usgs";
rejectDocument(sample,"ENTRY_PROVENANCE_MISMATCH");
sample=JSON.parse(JSON.stringify(b.document));
sample.entries[0].eventId="hijacked";
rejectDocument(sample,"ENTRY_PROVENANCE_MISMATCH");
sample=JSON.parse(JSON.stringify(b.document));
sample.entries[0].transport=sample.entries[0].transport.replace(
    "NOAA MRMS","FAKE SOURCE"
);
rejectDocument(sample,"INVALID_NESTED_DOSSIER");
sample=JSON.parse(JSON.stringify(b.document));
sample.entries[1].sequence=1;
rejectDocument(sample,"INVALID_ENTRY_OR_ORDER");
sample=JSON.parse(JSON.stringify(b.document));
sample.revision=1;
rejectDocument(sample,"REVISION_BEHIND_ENTRIES");
sample=JSON.parse(JSON.stringify(b.document));
sample.entries[1].capturedAtMs=1;
rejectDocument(sample,"ENTRY_PROVENANCE_MISMATCH");
sample=JSON.parse(JSON.stringify(b.document));
sample.entries[1].extra="unrecognized";
rejectDocument(sample,"INVALID_ENTRY_OR_ORDER");
assert.equal(archive.parse("{bad",codec).reason,"INVALID_JSON");
assert.equal(archive.parse("",codec).reason,"EMPTY_FILE_CORRUPT");
assert.equal(archive.parse(" \n  ",codec).reason,"EMPTY_FILE_CORRUPT");
assert.equal(archive.parse(JSON.stringify(archive.empty()),codec).count,0);
assert.equal(archive.parse("x".repeat(archive.MAX_DOCUMENT_CHARS+1),codec).reason,
    "INPUT_SIZE_OR_TYPE_INVALID");

const failed=archive.append(
    b.document,{ok:false,reason:"EXPLICIT_OPERATOR_REQUEST_REQUIRED"},
    now+2000,codec
);
assert.equal(failed.ok,false);
assert.equal(failed.document,null);
assert.equal(archive.append(b.document,s2,now-1,codec).ok,false);
assert.equal(archive.parse(JSON.stringify(b.document),codec).ok,true);

// Safety ceiling: reject new captures, never truncate earlier history.
let growing=b.document;
for (let i=2; i<archive.MAX_ENTRIES; i++) {
    const added=archive.append(growing,s1,now+i*1000,codec);
    assert.equal(added.ok,true,"append "+i);
    growing=added.document;
}
assert.equal(growing.entries.length,archive.MAX_ENTRIES);
assert.equal(growing.entries[0].sequence,1);
assert.equal(growing.entries[0].eventId,"FL:alpha");
assert.equal(growing.entries[archive.MAX_ENTRIES-1].sequence,
    archive.MAX_ENTRIES);
const full=archive.append(growing,s2,now+900000,codec);
assert.equal(full.ok,false);
assert.equal(full.reason,"ARCHIVE_AT_CAPACITY");
assert.equal(full.document,null);
assert.equal(growing.entries.length,archive.MAX_ENTRIES);
assert.equal(archive.parse(JSON.stringify(growing),codec).ok,true);

// Strict no-write UI wiring and separation from M19 writer.
const shell=read("shell.qml");
const ws=read("widgets/weather/WeatherStationW.qml");
const map=read("widgets/weather/StationDiscovery.qml");
const card=read("widgets/weather/StationEventContextCard.qml");
const owner=read("services/weather/WeatherDossierArchiveStore.qml");
assert.ok(shell.includes("WeatherDossierArchiveStore {"));
assert.ok(shell.includes("dossierArchiveStore: weatherDossierArchive"));
assert.ok(ws.includes("dossierArchiveStore: weatherStation.dossierArchiveStore"));
assert.ok(map.includes("function saveSelectedDossier()"));
assert.ok(map.includes("DossierCapturePolicy.stage("));
assert.ok(map.includes("dossierArchiveStore.capture(staged, now)"));
assert.ok(card.includes('label: "SAVE DOSSIER"'));
assert.ok(card.includes("onDossierSaveRequested:") === false);
assert.ok(map.includes("onDossierSaveRequested:"));
assert.ok(owner.includes('Quickshell.dataDir + "/weather-dossier-archive-v1.json"'));
assert.ok(owner.includes("atomicWrites: true"));
assert.ok(owner.includes("watchChanges: false"));
assert.ok(owner.includes('storageState: "loading"'));
assert.ok(owner.includes("dossierArchive.dossierSaved("));
assert.ok(owner.includes("onSaveFailed:"));
assert.equal((owner.match(/\bFileView\s*\{/g)||[]).length,1);
assert.equal((shell.match(/WeatherEventArchiveStore\s*\{/g)||[]).length,1);
assert.equal((map.match(/eventArchiveStore\.archiveEvent\(/g)||[]).length,1);
assert.equal((map.match(/dossierArchiveStore\.capture\(/g)||[]).length,1);
assert.equal(/Timer\s*\{/.test(owner),false);
assert.equal(/Process\s*\{/.test(owner),false);
assert.equal(owner.includes("autoCapture"),false);
console.log("Weather M25 independent persistent dossier: PASS");
