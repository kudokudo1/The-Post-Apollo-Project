#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const policySource = read("services/weather/WeatherPersistentCachePolicy.js");
const policy = {JSON,Math,Number,String,Array,Object,RegExp,isFinite};
vm.runInNewContext(
    policySource.replace(/^\.pragma library\s*/m, ""),
    policy
);

const runtimeSource = read("services/weather/WeatherRuntimePolicy.js");
const runtime = {Date,Math,Number,String,Array,Object,JSON,isFinite};
vm.runInNewContext(
    runtimeSource.replace(/^\.pragma library\s*/m, ""),
    runtime
);

const hour = 3600000;
const now = Date.parse("2026-11-02T12:00:00Z");

const ids = policy.knownSourceIds().slice().sort();
const m5SourceIds = [
    "weather-current","weather-forecast","air-quality",
    "space-kp","space-wind","space-imf","space-flux",
    "seismic","gdacs"
];
for (const id of m5SourceIds)
    assert.ok(ids.includes(id), id);

// M5's still-deferred categories remain excluded until their own milestone.
for (const id of [
    "lightning",
    "moon",
    "planet-rise-set",
    "firms",
    "mrms-radar",
    "rainviewer",
    "hms-smoke"
]) {
    assert.equal(ids.includes(id), false, id + " must remain excluded");
}

const seismicEvents = Array.from({length:80}, (_,i)=>({
    id:"usgs-"+i,
    magnitude:2.5 + (i % 20) / 10,
    place:"Test earthquake "+i,
    time:now - i * 60000,
    updated:now - i * 30000,
    utc:"12:00 UTC",
    depthKm:5 + i,
    latitude:10 + i / 100,
    longitude:-70 + i / 100,
    significance:100 + i,
    tsunami:i % 2 === 0,
    status:"reviewed",
    alert:"",
    magType:"ml",
    accidentalProviderField:"DO NOT PERSIST"
}));

const gdacsEvents = Array.from({length:80}, (_,i)=>({
    id:"EQ:"+i+":1",
    eventId:String(i),
    episodeId:"1",
    eventType:"EQ",
    eventTypeLabel:"EARTHQUAKE",
    name:"GDACS event "+i,
    alertLevel:i % 3 === 0 ? "RED" : i % 3 === 1 ? "ORANGE" : "GREEN",
    alertScore:2.5,
    alertToken:"orange",
    isCurrent:i < 10,
    country:"TEST",
    iso3:"TST",
    source:"GDACS",
    latitude:20 + i / 100,
    longitude:30 + i / 100,
    coordinates:"20.00, 30.00",
    geometryType:"Point",
    fromUtc:"2026-11-02 10:00 UTC",
    toUtc:"2026-11-02 11:00 UTC",
    timeMs:now - i * 60000,
    severity:4.2,
    severityText:"TEST",
    severityUnit:"units",
    reportUrl:"https://example.invalid/report/"+i,
    detailsUrl:"https://example.invalid/details/"+i,
    rawProviderObject:{huge:true}
}));

let doc = policy.initialDocument();
let result = policy.upsert(
    doc, "seismic", now - 5 * 60000,
    {events:seismicEvents}, now
);
assert.equal(result.ok, true);
doc = result.document;

result = policy.upsert(
    doc, "gdacs", now - 4 * 60000,
    {events:gdacsEvents}, now
);
assert.equal(result.ok, true);
doc = result.document;

assert.equal(doc.revision, 2);
assert.equal(doc.records.seismic.payload.events.length, 50);
assert.equal(doc.records.gdacs.payload.events.length, 50);
assert.equal(
    Object.prototype.hasOwnProperty.call(
        doc.records.seismic.payload.events[0],
        "accidentalProviderField"
    ),
    false
);
assert.equal(
    Object.prototype.hasOwnProperty.call(
        doc.records.gdacs.payload.events[0],
        "rawProviderObject"
    ),
    false
);

// Invalid rows are discarded at the persistence boundary.
result = policy.upsert(
    doc, "seismic", now,
    {events:[
        {id:"bad",magnitude:2.0,time:now,latitude:0,longitude:0},
        {id:"good",magnitude:3.1,time:now,latitude:39,longitude:-77}
    ]},
    now + 1000
);
assert.equal(result.ok, true);
assert.equal(result.document.records.seismic.payload.events.length, 1);
assert.equal(result.document.records.seismic.payload.events[0].id, "good");

// Both global event feeds use the existing 24h M3 expiry window.
for (const id of ["seismic","gdacs"]) {
    const spec = runtime.sourceSpec(id);
    assert.equal(spec.retention, "PERSISTENT_LAST_GOOD");
    assert.equal(spec.expireMs, 24 * hour);
    assert.equal(runtime.retentionLabel(spec), "PERSIST≤1d");
}

// Categories still deferred after later additive milestones remain non-persistent.
for (const id of ["lightning"]) {
    const spec = runtime.sourceSpec(id);
    assert.notEqual(spec.retention, "PERSISTENT_LAST_GOOD", id);
}
for (const id of ["lightning","mrms-radar","rainviewer"]) {
    const spec = runtime.sourceSpec(id);
    assert.equal(spec.retention, "FRAME_CACHE", id);
}
for (const id of ["hms-smoke","firms"]) {
    const spec = runtime.sourceSpec(id);
    assert.equal(spec.retention, "OPERATOR_SNAPSHOT", id);
}
assert.equal(runtime.sourceSpec("moon").retention, "KEY_BOUND");
assert.equal(runtime.sourceSpec("planet-rise-set").retention, "KEY_BOUND");

// Seismic remains one view-scoped network owner with cache-only restart help.
const seismic = read("services/weather/SeismicService.qml");
for (const needle of [
    "property var cacheStore: null",
    "property bool usingPersistentCache: false",
    'cacheStore.record("seismic", Date.now())',
    'cacheStore.put("seismic"',
    "usingPersistentCache = true",
    "usingPersistentCache = false"
])
    assert.ok(seismic.includes(needle), needle);
assert.match(
    seismic,
    /Component\.onCompleted:\s*\{\s*hydratePersistentCache\(\);\s*if \(active\)\s*refresh\(\);/
);
assert.equal((seismic.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((seismic.match(/\bTimer\s*\{/g) || []).length, 1);
assert.doesNotMatch(seismic, /FileView\s*\{/);

// GDACS remains MAP-scoped and keeps exactly one fetch owner/timer.
const gdacs = read("services/weather/GdacsService.qml");
for (const needle of [
    "property var cacheStore: null",
    "property bool usingPersistentCache: false",
    'cacheStore.record("gdacs", Date.now())',
    'cacheStore.put("gdacs"',
    "usingPersistentCache = true",
    "usingPersistentCache = false"
])
    assert.ok(gdacs.includes(needle), needle);
assert.match(
    gdacs,
    /Component\.onCompleted:\s*\{\s*hydratePersistentCache\(\);\s*if \(active\)\s*refresh\(false\);/
);
assert.equal((gdacs.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((gdacs.match(/\bTimer\s*\{/g) || []).length, 1);
assert.doesNotMatch(gdacs, /FileView\s*\{/);

// One existing shell store is routed into WeatherStationW, then into Seismic
// and the MAP-local GDACS service. No second persistent writer is created.
const shell = read("shell.qml");
assert.equal(
    (shell.match(/WeatherPersistentCacheStore\s*\{/g) || []).length,
    1
);
assert.match(
    shell,
    /persistentCacheStore:\s*weatherPersistentCache/
);

const station = read("widgets/weather/WeatherStationW.qml");
assert.match(station, /property var persistentCacheStore:\s*null/);
assert.match(
    station,
    /cacheStore:\s*weatherStation\.persistentCacheStore/
);
assert.match(
    station,
    /persistentCacheStore:\s*weatherStation\.persistentCacheStore/
);

const discovery = read("widgets/weather/StationDiscovery.qml");
assert.match(discovery, /property var persistentCacheStore:\s*null/);
assert.match(
    discovery,
    /cacheStore:\s*stationDiscovery\.persistentCacheStore/
);
assert.match(
    discovery,
    /"usingCache": gdacsService\.usingPersistentCache/
);
assert.match(
    discovery,
    /"usingCache": seismicSource[\s\S]{0,100}usingPersistentCache/
);

// Guard categories that remain deferred after the additive M7 milestone.
for (const file of [
    "services/weather/NowcoastLightningService.qml"
]) {
    const src = read(file);
    assert.doesNotMatch(src, /WeatherPersistentCache|persistentCacheStore/);
    assert.doesNotMatch(src, /cacheStore\.put\(/);
}

console.log("Weather persistent cache M5 global event intelligence: PASS");
