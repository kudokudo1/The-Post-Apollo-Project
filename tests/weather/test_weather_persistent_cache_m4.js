#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const policySource = read("services/weather/WeatherPersistentCachePolicy.js");
const ctx = {JSON, Math, Number, String, Array, Object, RegExp, isFinite};
vm.runInNewContext(
    policySource.replace(/^\.pragma library\s*/m, ""),
    ctx
);

for (const fn of [
    "initialDocument", "parse", "upsert", "record", "normalizeRecord",
    "knownSourceIds"
])
    assert.equal(typeof ctx[fn], "function", fn);

const minute = 60000;
const now = Date.parse("2026-11-02T10:00:00Z");
let doc = ctx.initialDocument();
assert.equal(doc.schema, "post-apollo.weather-last-known.v1");
assert.equal(doc.version, 1);
assert.equal(doc.revision, 0);
assert.deepEqual(Object.keys(doc.records), []);

const samples = {
    "weather-current": {
        receivedAtMs: now - 5 * minute,
        payload: {
            tempF:"61", feelsLikeF:"60", condition:"Clear",
            weatherCode:"113", uvIndex:2, humidity:"52",
            windMph:"6", windDirection:"NW", pressureHpa:1018,
            visibilityMiles:10, cloudCover:8, precipMm:0,
            observationTime:"2026-11-02 04:50 AM",
            localObservationDateTime:"2026-11-02 04:50 AM",
            latitude:"38.9", longitude:"-76.9"
        }
    },
    "weather-forecast": {
        receivedAtMs: now - 5 * minute,
        payload: {
            hourlyForecast: Array.from({length:20}, (_,i)=>({
                time:String(i*100), tempF:60+i
            })),
            dailyForecast: Array.from({length:20}, (_,i)=>({
                date:"2026-11-"+String(i+2).padStart(2,"0"),
                maxTempF:70+i
            }))
        }
    },
    "air-quality": {
        receivedAtMs: now - 4 * minute,
        payload: {
            aqi:42, aqiLabel:"GOOD", ozoneAqi:30,
            nitrogenDioxideAqi:20, carbonMonoxideAqi:10,
            pm25:5, pm10:8, carbonMonoxide:100,
            nitrogenDioxide:8, ozone:45, dust:0,
            alderPollen:0, birchPollen:0, grassPollen:1,
            mugwortPollen:0, olivePollen:0, ragweedPollen:0,
            pollenAvailable:true,
            airQualitySourceTime:"2026-11-02T09:00",
            airQualityUtcOffsetMinutes:-300,
            airQualityTimezone:"America/New_York",
            airQualityTimezoneAbbreviation:"EST",
            airQualityForecast:Array.from({length:12},(_,i)=>({
                time:"2026-11-02T"+String(i).padStart(2,"0")+":00",
                aqi:40+i
            }))
        }
    },
    "space-kp": {
        receivedAtMs: now - 3 * minute,
        payload: {
            kp:3.3, kpTime:"2026-11-02T09:57:00",
            kpHistory:Array.from({length:40},(_,i)=>({
                time:"2026-11-01T00:00:00", kp:i%9
            })),
            kpHistorySummary:{bins:24,hours:72,maxKp:5}
        }
    },
    "space-wind": {
        receivedAtMs: now - 2 * minute,
        payload:{solarWindSpeed:432,solarWindTime:"2026-11-02T09:58:00"}
    },
    "space-imf": {
        receivedAtMs: now - 2 * minute,
        payload:{magneticFieldBt:6.2,magneticFieldBz:-2.1,
                 magneticFieldTime:"2026-11-02T09:58:00"}
    },
    "space-flux": {
        receivedAtMs: now - minute,
        payload:{solarFlux:135,solarFluxTime:"2026-11-02T09:59:00"}
    }
};

for (const id of ctx.knownSourceIds()) {
    const sample = samples[id];
    assert.ok(sample, "fixture for " + id);
    const result = ctx.upsert(
        doc, id, sample.receivedAtMs, sample.payload, now
    );
    assert.equal(result.ok, true, id);
    doc = result.document;
}
assert.equal(doc.revision, 7);
assert.equal(Object.keys(doc.records).length, 7);

// Schema survives a full JSON round trip.
const parsed = ctx.parse(JSON.stringify(doc));
assert.equal(parsed.ok, true);
assert.equal(parsed.document.revision, 7);
assert.equal(Object.keys(parsed.document.records).length, 7);

// Bounded arrays prevent an unexpectedly huge provider response from becoming
// an unbounded persistent file.
assert.equal(
    parsed.document.records["weather-forecast"].payload.hourlyForecast.length,
    12
);
assert.equal(
    parsed.document.records["weather-forecast"].payload.dailyForecast.length,
    10
);
assert.equal(
    parsed.document.records["air-quality"].payload.airQualityForecast.length,
    6
);
assert.equal(
    parsed.document.records["space-kp"].payload.kpHistory.length,
    24
);

// Older data may never replace a newer retained record.
let result = ctx.upsert(
    parsed.document,
    "weather-current",
    now - 60 * minute,
    samples["weather-current"].payload,
    now + minute
);
assert.equal(result.ok, false);
assert.equal(result.reason, "OLDER_RECORD");

// Newer same-source data advances only one revision.
result = ctx.upsert(
    parsed.document,
    "weather-current",
    now,
    {...samples["weather-current"].payload,tempF:"63"},
    now + minute
);
assert.equal(result.ok, true);
assert.equal(result.document.revision, 8);
assert.equal(
    result.document.records["weather-current"].payload.tempF,
    "63"
);

// Future/corrupt/unknown storage must fail closed.
const future = JSON.parse(JSON.stringify(doc));
future.version = 99;
assert.equal(ctx.parse(JSON.stringify(future)).reason, "UNSUPPORTED_VERSION");
assert.equal(ctx.parse("{broken").reason, "INVALID_JSON");

const unknown = JSON.parse(JSON.stringify(doc));
delete unknown.records["space-flux"];
unknown.records["mystery-source"] = doc.records["space-flux"];
assert.equal(ctx.parse(JSON.stringify(unknown)).reason, "UNKNOWN_RECORD");

const badRecord = JSON.parse(JSON.stringify(doc));
badRecord.records["space-flux"].receivedAtMs = -1;
assert.equal(ctx.parse(JSON.stringify(badRecord)).reason, "INVALID_RECORD");

// Runtime policy now truthfully labels the seven reboot-surviving records.
const runtimeSource = read("services/weather/WeatherRuntimePolicy.js");
const runtime = {Date,Math,Number,String,Array,Object,JSON,isFinite};
vm.runInNewContext(
    runtimeSource.replace(/^\.pragma library\s*/m, ""),
    runtime
);
for (const id of ctx.knownSourceIds()) {
    const spec = runtime.sourceSpec(id);
    assert.ok(spec, id + " runtime spec");
    assert.equal(spec.retention, "PERSISTENT_LAST_GOOD", id);
    assert.match(runtime.retentionLabel({
        retention:spec.retention, expireMs:spec.expireMs
    }), /^PERSIST≤/);
}

// Store contract: exactly one bounded atomic Quickshell writer, no provider.
const store = read("services/weather/WeatherPersistentCacheStore.qml");
assert.match(store, /Quickshell\.dataDir \+ "\/weather-last-known-v1\.json"/);
assert.match(store, /FileView\s*\{/);
assert.match(store, /atomicWrites:\s*true/);
assert.match(store, /watchChanges:\s*false/);
assert.match(store, /onLoaded:\s*cache\.acceptLoaded/);
assert.match(store, /FileViewError\.FileNotFound/);
assert.match(store, /result\.reason === "UNSUPPORTED_VERSION"/);
assert.match(store, /\? "unsupported" : "error"/);
assert.match(store, /errorCode = "FILE_SAVE_FAILED"/);
assert.match(store, /function workingDocument\(\)/);
assert.match(store, /function applyDeferredUpdates\(\)/);
assert.match(store, /function flushQueued\(\)/);
assert.match(store, /age <= expireMs \? saved : null/);
assert.doesNotMatch(store, /\bProcess\s*\{|\bTimer\s*\{|curl|XMLHttpRequest/);

// One shell owner feeds both global services.
const shell = read("shell.qml");
assert.equal(
    (shell.match(/WeatherPersistentCacheStore\s*\{/g) || []).length,
    1
);
assert.match(shell, /id:\s*weatherPersistentCache/);
assert.equal(
    (shell.match(/cacheStore:\s*weatherPersistentCache/g) || []).length,
    2
);

// Weather hydration: cache first when available, live fetch still starts.
// Successful provider parses publish only normalized current/forecast/AQ.
const weather = read("services/weather/WeatherService.qml");
for (const needle of [
    "property var cacheStore: null",
    "usingPersistentCurrentCache",
    "usingPersistentForecastCache",
    "usingPersistentAqiCache",
    'cacheStore.record("weather-current", now)',
    'cacheStore.record("weather-forecast", now)',
    'cacheStore.record("air-quality", now)',
    'cacheStore.put("weather-current"',
    'cacheStore.put("weather-forecast"',
    'cacheStore.put("air-quality"'
])
    assert.ok(weather.includes(needle), needle);
assert.match(
    weather,
    /Component\.onCompleted:\s*\{\s*hydratePersistentCache\(\);\s*refresh\(\);/
);
assert.equal((weather.match(/\bProcess\s*\{/g) || []).length, 2);
assert.equal((weather.match(/\bTimer\s*\{/g) || []).length, 1);
assert.doesNotMatch(weather, /FileView\s*\{/);

// Space hydration is independent per product and keeps the single fetch owner.
const space = read("services/weather/SpaceService.qml");
for (const needle of [
    "usingPersistentKpCache",
    "usingPersistentSolarWindCache",
    "usingPersistentMagneticFieldCache",
    "usingPersistentSolarFluxCache",
    'cacheStore.record("space-kp", now)',
    'cacheStore.record("space-wind", now)',
    'cacheStore.record("space-imf", now)',
    'cacheStore.record("space-flux", now)',
    'cacheStore.put("space-kp"',
    'cacheStore.put("space-wind"',
    'cacheStore.put("space-imf"',
    'cacheStore.put("space-flux"'
])
    assert.ok(space.includes(needle), needle);
assert.match(
    space,
    /Component\.onCompleted:\s*\{\s*hydratePersistentCache\(\);\s*refresh\(\);/
);
assert.equal((space.match(/\bProcess\s*\{/g) || []).length, 4);
assert.equal((space.match(/\bTimer\s*\{/g) || []).length, 1);
assert.doesNotMatch(space, /FileView\s*\{/);

// A restored record must be visible as CACHE through every affected runtime
// surface, not silently masquerade as a live response.
for (const file of [
    "widgets/weather/StationHome.qml",
    "widgets/weather/StationGround.qml",
    "widgets/weather/StationSky.qml",
    "widgets/weather/StationSpace.qml",
    "widgets/weather/WeatherStationW.qml"
]) {
    const src = read(file);
    assert.match(src, /usingCache/);
    assert.match(src, /usingPersistent/);
}

// Persistence is operational cache only. History/dossier ownership stays out.
// Comments may name those systems to state the boundary; executable coupling
// to their owners/services is forbidden.
for (const forbidden of [
    "WeatherHistoryService",
    "WeatherEventDossier",
    "WeatherEventTimeline",
    "WeatherEventEvolution",
    "historyService",
    "dossierStore",
    "timelineStore"
]) {
    assert.equal(store.includes(forbidden), false, forbidden);
    assert.equal(policySource.includes(forbidden), false, forbidden);
}

console.log("Weather persistent last-known cache M4: PASS");
