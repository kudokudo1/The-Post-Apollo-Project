#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const eventCtx = {
    Date, Math, Number, String, Array, Object, JSON, RegExp,
    isFinite, isNaN
};
vm.runInNewContext(
    read("widgets/weather/StationEventContextPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    eventCtx,
    {filename:"widgets/weather/StationEventContextPolicy.js"}
);

const runtimeCtx = {
    Date, Math, Number, String, Array, Object, JSON, RegExp,
    isFinite, isNaN
};
vm.runInNewContext(
    read("services/weather/WeatherRuntimePolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    runtimeCtx,
    {filename:"services/weather/WeatherRuntimePolicy.js"}
);

for (const fn of [
    "radarCoverage",
    "lightningCoverage",
    "floodGaugeContext",
    "timelineRow",
    "evidenceTimeline"
]) {
    assert.equal(typeof eventCtx[fn], "function", fn);
}
for (const fn of ["sourceSpec", "temporalBand", "freshness"]) {
    assert.equal(typeof runtimeCtx[fn], "function", fn);
}

const now = Date.UTC(2026, 10, 2, 17, 0, 0);

const selected = eventCtx.normalizeSelected("gdacs", {
    id:"FL:400:1",
    name:"Freshness Semantics Flood",
    eventTypeLabel:"FLOOD",
    latitude:38.90,
    longitude:-77.00,
    timeMs:now - 3 * 86400000,
    toUtc:"2026-10-30 17:00 UTC"
});

const radar = eventCtx.radarCoverage(
    selected,
    {valid:true, west:-78, south:38, east:-76, north:40},
    0,
    now - 5 * 60000,
    false,
    new Date(now - 2 * 60000)
);
assert.equal(radar.receivedAtMs, now - 2 * 60000);

const lightning = eventCtx.lightningCoverage(
    selected,
    {west:-80, south:36, east:-74, north:42},
    true,
    new Date(now - 10 * 60000).toISOString(),
    15,
    8,
    320,
    false,
    new Date(now - 8 * 60000)
);
assert.equal(lightning.receivedAtMs, now - 8 * 60000);
assert.equal(lightning.timeMs, now - 10 * 60000);

const gauge = {
    lid:"TEST1",
    name:"Test River",
    latitude:38.95,
    longitude:-77.05,
    distanceKm:8,
    observedPrimary:9.5,
    primaryUnits:"ft",
    observedCategory:{id:"action", label:"ACTION", rank:1},
    forecastCategory:{id:"minor", label:"MINOR", rank:2}
};
const stageflow = {
    observed:{
        available:true,
        primaryName:"STAGE",
        primaryUnits:"ft",
        data:[
            {
                validMillis:now - 80 * 60000,
                validLabel:"2026-11-02 15:40Z",
                primary:8.8
            },
            {
                validMillis:now - 20 * 60000,
                validLabel:"2026-11-02 16:40Z",
                primary:9.5
            }
        ]
    }
};
const flood = eventCtx.floodGaugeContext(
    selected,
    gauge,
    null,
    stageflow,
    100,
    new Date(now - 6 * 60000)
);
assert.equal(flood.available, true);
assert.equal(flood.receivedAtMs, now - 6 * 60000);
assert.equal(flood.latestObserved.timeMs, now - 20 * 60000);

const companions = [{
    sourceLabel:"NASA EONET",
    typeLabel:"Floods",
    title:"Old independent event record",
    timeMs:now - 2 * 86400000
}];

const timeline = Array.from(eventCtx.evidenceTimeline(
    selected,
    companions,
    radar,
    lightning,
    flood,
    8
));
assert.equal(timeline.length, 5);

const bySource = Object.fromEntries(
    timeline.map(row => [row.sourceLabel, row])
);

assert.equal(bySource["GDACS"].freshnessMode, "AGE_ONLY");
assert.equal(bySource["GDACS"].runtimeSourceId, "");
assert.equal(bySource["GDACS"].receivedAtMs, -1);

assert.equal(bySource["NASA EONET"].freshnessMode, "AGE_ONLY");
assert.equal(bySource["NASA EONET"].runtimeSourceId, "");
assert.equal(bySource["NASA EONET"].receivedAtMs, -1);

assert.equal(bySource["NOAA MRMS"].freshnessMode, "SNAPSHOT");
assert.equal(bySource["NOAA MRMS"].runtimeSourceId, "mrms-radar");
assert.equal(bySource["NOAA MRMS"].receivedAtMs, now - 2 * 60000);

assert.equal(
    bySource["NOAA NOWCOAST"].freshnessMode,
    "PROVIDER_CONTRACT"
);
assert.equal(
    bySource["NOAA NOWCOAST"].runtimeSourceId,
    "lightning"
);
assert.equal(
    bySource["NOAA NOWCOAST"].receivedAtMs,
    now - 8 * 60000
);

assert.equal(
    bySource["NOAA NWPS"].freshnessMode,
    "PROVIDER_CONTRACT"
);
assert.equal(bySource["NOAA NWPS"].runtimeSourceId, "river");
assert.equal(bySource["NOAA NWPS"].receivedAtMs, now - 6 * 60000);

const lightningSpec = runtimeCtx.sourceSpec("lightning");
assert.equal(
    runtimeCtx.temporalBand(
        lightningSpec, now - 10 * 60000, now
    ),
    "FRESH"
);
assert.equal(
    runtimeCtx.temporalBand(
        lightningSpec, now - 30 * 60000, now
    ),
    "AGING"
);
assert.equal(
    runtimeCtx.temporalBand(
        lightningSpec, now - 60 * 60000, now
    ),
    "STALE"
);
assert.equal(
    runtimeCtx.temporalBand(
        lightningSpec, now - 130 * 60000, now
    ),
    "EXPIRED"
);

const riverSpec = runtimeCtx.sourceSpec("river");
assert.equal(
    runtimeCtx.temporalBand(
        riverSpec, now - 20 * 60000, now
    ),
    "FRESH"
);
assert.equal(
    runtimeCtx.temporalBand(
        riverSpec, now - 60 * 60000, now
    ),
    "AGING"
);
assert.equal(
    runtimeCtx.temporalBand(
        riverSpec, now - 180 * 60000, now
    ),
    "STALE"
);
assert.equal(
    runtimeCtx.temporalBand(
        riverSpec, now - 780 * 60000, now
    ),
    "EXPIRED"
);

assert.equal(
    runtimeCtx.freshness(
        runtimeCtx.sourceSpec("mrms-radar"),
        now - 5 * 60000,
        now
    ),
    "SNAPSHOT"
);

const card = read("widgets/weather/StationEventContextCard.qml");
const map = read("widgets/weather/StationDiscovery.qml");
const policy = read("widgets/weather/StationEventContextPolicy.js");

assert.match(card, /function timelineFreshnessLabel\(row\)/);
assert.match(card, /RuntimePolicy\.sourceSpec/);
assert.match(card, /RuntimePolicy\.temporalBand/);
for (const token of [
    "AGE ONLY",
    "SNAPSHOT",
    "PROVIDER_CONTRACT",
    "CONTRACT "
]) {
    assert.ok(card.includes(token), token);
}
assert.match(
    card,
    /\+ " \/\/ FRESHNESS "\s*\+ card\.timelineFreshnessLabel/
);
for (const phrase of [
    "RECENCY = CLOCK AGE, NOT PROVIDER VALIDITY",
    "PROVIDER FRESHNESS = RECEIVE-TIME CONTRACT ONLY FOR OPERATIONAL EVIDENCE",
    "EVENT RECORDS = AGE ONLY",
    "NOT ONE MERGED INCIDENT HISTORY"
]) {
    assert.ok(card.includes(phrase), phrase);
}

assert.match(
    map,
    /mrmsRadarService\.usingFrameCache,\s*mrmsRadarService\.lastUpdated/
);
assert.match(
    map,
    /lightningSource \? lightningSource\.lastUpdated : null/
);
assert.match(
    map,
    /riverSource && riverSource\.stageflowReady[\s\S]*?riverSource\.stageflowLastUpdated/
);

assert.match(policy, /freshnessMode:/);
assert.match(policy, /runtimeSourceId:/);
assert.match(policy, /receivedAtMs:/);
assert.equal((card.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bFileView\s*\{/g) || []).length, 0);
assert.doesNotMatch(policy, /curl|https:\/\//);
assert.doesNotMatch(policy, /Timer\s*\{|Process\s*\{|FileView\s*\{/);

console.log("Weather M18 provider-aware evidence freshness: PASS");
