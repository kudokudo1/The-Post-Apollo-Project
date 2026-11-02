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

const now = Date.parse("2026-11-02T10:15:00Z");
const point = "38.9,-76.9";
const alert = {
    id:"https://api.weather.gov/alerts/abc",
    event:"Flood Warning",
    headline:"Flood Warning test",
    area:"TEST AREA",
    issuer:"NWS TEST OFFICE",
    severity:"Severe",
    urgency:"Immediate",
    certainty:"Likely",
    status:"Actual",
    messageType:"Alert",
    category:"Met",
    response:"Prepare",
    displaySeverity:"normal",
    description:"Test description",
    instruction:"Test instruction",
    sent:"2026-11-02T09:00:00Z",
    updated:"2026-11-02T09:05:00Z",
    effective:"2026-11-02T09:00:00.000Z",
    onset:"2026-11-02T09:10:00.000Z",
    expires:"2026-11-02T14:00:00.000Z",
    ends:"2026-11-02T14:00:00.000Z",
    revision:"2026-11-02T09:05:00Z|Flood Warning test|Severe|1762092000000",
    accidentalProviderField:"DROP ME"
};

let doc = policy.initialDocument();
let result = policy.upsert(
    doc,
    "nws-alerts",
    now - 15 * 60000,
    {
        point,
        entries:[{
            id:alert.id,
            revision:alert.revision,
            absent:1,
            alert,
            accidental:"DROP ME"
        }]
    },
    now,
    point,
    "nws|" + point
);
assert.equal(result.ok, true);
doc = result.document;

assert.equal(policy.knownSourceIds().length, 13);
assert.ok(policy.knownSourceIds().includes("nws-alerts"));

const saved = doc.records["nws-alerts"];
assert.equal(saved.scopeKey, point);
assert.equal(saved.requestKey, "nws|" + point);
assert.equal(saved.payload.point, point);
assert.equal(saved.payload.entries.length, 1);
assert.equal(saved.payload.entries[0].absent, 1);
assert.equal(saved.payload.entries[0].alert.displaySeverity, "critical");
assert.equal(
    Object.prototype.hasOwnProperty.call(
        saved.payload.entries[0].alert,
        "accidentalProviderField"
    ),
    false
);
assert.equal(
    Object.prototype.hasOwnProperty.call(saved.payload.entries[0], "accidental"),
    false
);

// NWS cache identity is exact to the explicitly configured point. A record
// for one pinned emergency-alert point must never hydrate another point.
result = policy.upsert(
    doc,
    "nws-alerts",
    now,
    {point, entries:[]},
    now,
    "38.91,-76.9",
    "nws|38.91,-76.9"
);
assert.equal(result.ok, false);
assert.equal(result.reason, "INVALID_RECORD");

result = policy.upsert(
    doc,
    "nws-alerts",
    now,
    {point, entries:[]},
    now,
    point,
    "nws|tampered"
);
assert.equal(result.ok, false);
assert.equal(result.reason, "INVALID_RECORD");

result = policy.upsert(
    doc,
    "nws-alerts",
    now,
    {point:"38.91,-76.9", entries:[]},
    now,
    point,
    "nws|" + point
);
assert.equal(result.ok, false);
assert.equal(result.reason, "INVALID_RECORD");

// A successful live check with zero active alerts is still meaningful cache
// state. Persisting it is safe only because the UI labels it CACHE after a
// restart and the next live response remains authoritative.
result = policy.upsert(
    doc,
    "nws-alerts",
    now,
    {point, entries:[]},
    now + 1,
    point,
    "nws|" + point
);
assert.equal(result.ok, true);
assert.equal(result.document.records["nws-alerts"].payload.entries.length, 0);

const spec = runtime.sourceSpec("nws-alerts");
assert.equal(spec.retention, "PERSISTENT_LAST_GOOD");
assert.equal(spec.cadenceMs, 300000);
assert.equal(spec.expireMs, 6 * 3600000);
assert.match(runtime.retentionLabel(spec), /^PERSIST≤/);

const producer = read(
    "services/notifications/NwsOfficialAlertNotificationProducer.qml"
);
const shell = read("shell.qml");
const home = read("widgets/weather/StationHome.qml");
const ground = read("widgets/weather/StationGround.qml");
const station = read("widgets/weather/WeatherStationW.qml");

assert.match(producer, /property var cacheStore: null/);
assert.match(producer, /property bool usingPersistentCache: false/);
assert.match(
    producer,
    /cacheStore\.record\(\s*"nws-alerts",\s*Date\.now\(\),\s*producer\.alertPoint/
);
assert.match(producer, /producer\.persistAlertState\(\)/);
assert.match(
    producer,
    /cacheStore\.put\([\s\S]*?"nws-alerts"[\s\S]*?producer\.cacheRequestKey/
);
assert.match(producer, /fetchSucceeded \|\| usingPersistentCache/);
assert.match(producer, /producer\.usingPersistentCache = false/);
assert.equal((producer.match(/\bProcess\s*\{/g) || []).length, 1);
assert.equal((producer.match(/\bTimer\s*\{/g) || []).length, 1);
assert.match(producer, /interval: 300000/);
assert.doesNotMatch(producer, /weatherService|wttr\.in/);

assert.match(
    shell,
    /NwsOfficialAlertNotificationProducer \{[\s\S]*?cacheStore: weatherPersistentCache/
);
assert.match(
    home,
    /"usingCache": nwsAlertSource[\s\S]{0,100}usingPersistentCache/
);
assert.match(ground, /"usingCache": nwsUsingPersistentCache/);
assert.match(ground, /LAST SUCCESSFUL NWS CHECK LISTED NO ACTIVE ALERTS \/\/ CACHE/);
assert.match(station, /officialAlertUsingPersistentCache/);
assert.match(station, /officialAlertUsingPersistentCache \? " \/\/ CACHE" : ""/);

console.log("Weather persistent cache M7 NWS restart lifecycle: PASS");
