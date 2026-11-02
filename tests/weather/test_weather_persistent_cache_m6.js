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

const riverPolicySource = read("services/weather/NwpsRiverPolicy.js");
const riverPolicy = {Date,Math,Number,String,Array,Object,JSON,isFinite};
vm.runInNewContext(
    riverPolicySource.replace(/^\.pragma library\s*/m, ""),
    riverPolicy
);

const hour = 3600000;
const now = Date.parse("2026-11-02T15:00:00Z");
const locationKey = "38.900|-76.900";
const otherLocationKey = "39.000|-77.000";

assert.equal(riverPolicy.requestKey(38.9, -76.9), locationKey);
assert.equal(riverPolicy.requestKey("bad", -76.9), "");

const riverGauge = {
    lid:"LNKM2",
    name:"Test River Gauge",
    latitude:38.88,
    longitude:-76.91,
    distanceKm:2.4,
    state:"MD",
    wfo:"LWX",
    rfc:"MARFC",
    observedPrimary:8.2,
    observedSecondary:900,
    forecastPrimary:8.6,
    forecastSecondary:950,
    primaryUnits:"ft",
    secondaryUnits:"cfs",
    observedCategory:{id:"none",label:"NO FLOODING",rank:0},
    forecastCategory:{id:"action",label:"ACTION",rank:1},
    accidental:"DROP ME"
};

const riverStageflow = {
    observed:{
        available:true,
        pedts:"HGIRG",
        issuedTime:"2026-11-02T14:00:00Z",
        issuedLabel:"2026-11-02 14:00Z",
        wfo:"LWX",
        timeZone:"UTC",
        primaryName:"STAGE",
        primaryUnits:"ft",
        secondaryName:"FLOW",
        secondaryUnits:"cfs",
        data:[{
            validTime:"2026-11-02T14:00:00Z",
            validMillis:now-hour,
            validLabel:"2026-11-02 14:00Z",
            generatedTime:"2026-11-02T13:55:00Z",
            primary:8.2,
            secondary:900,
            accidental:"DROP"
        }]
    },
    forecast:{
        available:true,
        pedts:"HGIFZ",
        issuedTime:"2026-11-02T14:00:00Z",
        issuedLabel:"2026-11-02 14:00Z",
        wfo:"LWX",
        timeZone:"UTC",
        primaryName:"STAGE",
        primaryUnits:"ft",
        secondaryName:"FLOW",
        secondaryUnits:"cfs",
        data:[{
            validTime:"2026-11-02T18:00:00Z",
            validMillis:now+3*hour,
            validLabel:"2026-11-02 18:00Z",
            generatedTime:"2026-11-02T13:55:00Z",
            primary:8.6,
            secondary:950
        }]
    }
};

const riverContext = {
    available:true,
    lid:"LNKM2",
    usgsId:"01600000",
    description:"Test gauge context",
    county:"TEST COUNTY",
    timeZone:"UTC",
    stageUnits:"ft",
    flowUnits:"cfs",
    thresholds:[{id:"minor",label:"MINOR",stage:10,flow:null,extra:"DROP"}],
    impacts:[{stage:11,statement:"Low road flooding.",extra:"DROP"}],
    recentCrests:[{
        occurredTime:"2026-10-01T12:00:00Z",
        occurredLabel:"2026-10-01 12:00Z",
        occurredMillis:Date.parse("2026-10-01T12:00:00Z"),
        stage:12.2,flow:1200,preliminary:"",oldDatum:false,extra:"DROP"
    }],
    historicCrests:[],
    inundationAvailable:false,
    notes:[{statement:"Test note",effective:"",expiration:"",extra:"DROP"}],
    accidental:"DROP"
};

const marineStation = {
    stationId:"44009",
    latitude:38.46,
    longitude:-74.70,
    sampleMillis:now-20*60000,
    sampleUtc:"2026-11-02 14:40Z",
    distanceKm:210,
    windDirection:310,
    windSpeedMs:7.2,
    gustMs:9.1,
    waveHeightM:1.4,
    dominantPeriodS:8,
    averagePeriodS:6,
    meanWaveDirection:110,
    pressureHpa:1015.2,
    pressureTendencyHpa:0.4,
    airTempC:16.8,
    waterTempC:17.2,
    dewpointC:11.1,
    visibilityNm:10,
    tideFt:null,
    accidental:"DROP"
};

const waterStation = {
    id:"8575512",
    name:"Annapolis",
    latitude:38.9833,
    longitude:-76.4817,
    distanceKm:40,
    state:"MD",
    timezone:"America/New_York",
    tidal:true,
    greatLakes:false,
    affiliations:"",
    predictionType:"",
    referenceId:"",
    accidental:"DROP"
};
const tideStation = {
    ...waterStation,
    id:"8574680",
    name:"Baltimore"
};
const waterLevel = {
    value:1.24,
    time:"2026-11-02 14:48",
    sampleMillis:now-12*60000,
    sampleUtc:"2026-11-02 14:48Z",
    sigma:0.03,
    flags:"",
    quality:"p",
    qualityLabel:"PRELIMINARY",
    accidental:"DROP"
};
const tidePredictions = [{
    time:"2026-11-02 18:00",
    sampleMillis:now+3*hour,
    sampleUtc:"2026-11-02 18:00Z",
    value:1.7,
    type:"H",
    label:"HIGH",
    high:true,
    accidental:"DROP"
}];

let doc = policy.initialDocument();

let result = policy.upsert(
    doc,
    "river",
    now-30*60000,
    {
        locationKey,
        gauge:riverGauge,
        nearbyGauges:[riverGauge],
        stageflow:riverStageflow,
        stageflowGaugeId:"LNKM2",
        gaugeContext:riverContext,
        contextGaugeId:"LNKM2"
    },
    now,
    locationKey,
    locationKey+"|LNKM2"
);
assert.equal(result.ok, true);
doc = result.document;

result = policy.upsert(
    doc,
    "marine",
    now-20*60000,
    {
        locationKey,
        station:marineStation,
        reportingStations:192
    },
    now,
    locationKey,
    locationKey+"|44009"
);
assert.equal(result.ok, true);
doc = result.document;

result = policy.upsert(
    doc,
    "coastal",
    now-12*60000,
    {
        locationKey,
        waterStation,
        tideStation,
        waterLevel,
        tidePredictions
    },
    now,
    locationKey,
    locationKey+"|8575512|8574680"
);
assert.equal(result.ok, true);
doc = result.document;

assert.equal(Object.keys(doc.records).length, 3);
for (const id of ["river","marine","coastal"]) {
    assert.equal(doc.records[id].scopeKey, locationKey);
    assert.ok(doc.records[id].requestKey.startsWith(locationKey+"|"));
}

// Persistence boundary strips accidental fields rather than trusting the
// in-memory service object just because it already came from a parser.
assert.equal(
    Object.prototype.hasOwnProperty.call(doc.records.river.payload.gauge,"accidental"),
    false
);
assert.equal(
    Object.prototype.hasOwnProperty.call(
        doc.records.river.payload.stageflow.observed.data[0],
        "accidental"
    ),
    false
);
assert.equal(
    Object.prototype.hasOwnProperty.call(
        doc.records.river.payload.gaugeContext.impacts[0],
        "extra"
    ),
    false
);
assert.equal(
    Object.prototype.hasOwnProperty.call(
        doc.records.marine.payload.station,
        "accidental"
    ),
    false
);
assert.equal(
    Object.prototype.hasOwnProperty.call(
        doc.records.coastal.payload.waterStation,
        "accidental"
    ),
    false
);
assert.equal(
    Object.prototype.hasOwnProperty.call(
        doc.records.coastal.payload.tidePredictions[0],
        "accidental"
    ),
    false
);

// Same payload + wrong location scope must be refused.
result = policy.upsert(
    doc,
    "marine",
    now,
    {
        locationKey,
        station:marineStation,
        reportingStations:192
    },
    now+1000,
    otherLocationKey,
    otherLocationKey+"|44009"
);
assert.equal(result.ok, false);
assert.equal(result.reason, "INVALID_RECORD");

// Same location + tampered station/gauge identity must be refused.
result = policy.upsert(
    doc,
    "river",
    now,
    {
        locationKey,
        gauge:riverGauge,
        nearbyGauges:[riverGauge],
        stageflow:riverStageflow,
        stageflowGaugeId:"LNKM2",
        gaugeContext:riverContext,
        contextGaugeId:"LNKM2"
    },
    now+1000,
    locationKey,
    locationKey+"|WRONG"
);
assert.equal(result.ok, false);
assert.equal(result.reason, "INVALID_RECORD");

result = policy.upsert(
    doc,
    "coastal",
    now,
    {
        locationKey,
        waterStation,
        tideStation,
        waterLevel,
        tidePredictions
    },
    now+1000,
    locationKey,
    locationKey+"|8575512|WRONG"
);
assert.equal(result.ok, false);
assert.equal(result.reason, "INVALID_RECORD");

// Round-trip retains keyed identity.
const parsed = policy.parse(JSON.stringify(doc));
assert.equal(parsed.ok, true);
for (const id of ["river","marine","coastal"]) {
    assert.equal(parsed.document.records[id].scopeKey, locationKey);
    assert.equal(
        parsed.document.records[id].requestKey,
        doc.records[id].requestKey
    );
}

// M7 later expands the additive envelope to thirteen known records.
assert.equal(policy.knownSourceIds().length, 13);
for (const id of ["river","marine","coastal"])
    assert.ok(policy.knownSourceIds().includes(id));

// Runtime cache windows stay source-specific.
const expectedExpiry = {
    river:12*hour,
    marine:6*hour,
    coastal:24*hour
};
for (const id of ["river","marine","coastal"]) {
    const spec = runtime.sourceSpec(id);
    assert.equal(spec.retention, "PERSISTENT_LAST_GOOD", id);
    assert.equal(spec.expireMs, expectedExpiry[id], id);
    assert.match(runtime.retentionLabel(spec), /^PERSIST≤/);
}

// The store supports exact scope filtering while preserving old unscoped API.
const store = read("services/weather/WeatherPersistentCacheStore.qml");
assert.match(store, /function record\(sourceId, nowMs, scopeKey\)/);
assert.match(store, /String\(saved\.scopeKey \|\| ""\) !== expectedScope/);
assert.match(store, /scopeKey,\s*requestKey/);
assert.doesNotMatch(store, /\bProcess\s*\{|\bTimer\s*\{|XMLHttpRequest|curl/);

// Service contracts: exact-key hydration, location invalidation, no extra owner.
const serviceContracts = [
    {
        file:"services/weather/NwpsRiverService.qml",
        id:"river",
        processCount:3,
        timerCount:2,
        fullKey:/currentKey \+ "\|" \+ String\(gauge\.lid \|\| ""\)/,
        antiRejuvenation:/stageflowUsingPersistentCache\s*\? null : stageflow/
    },
    {
        file:"services/weather/NdbcMarineService.qml",
        id:"marine",
        processCount:1,
        timerCount:2,
        fullKey:/currentKey \+ "\|"[\s\S]{0,80}station\.stationId/,
        antiRejuvenation:null
    },
    {
        file:"services/weather/CoopsCoastalService.qml",
        id:"coastal",
        processCount:3,
        timerCount:2,
        fullKey:/currentKey \+ "\|"[\s\S]{0,140}waterStation\.id[\s\S]{0,140}tideStation\.id/,
        antiRejuvenation:/Math\.min\(waterMs, tideMs\)/
    }
];

for (const contract of serviceContracts) {
    const src = read(contract.file);
    assert.match(src, /property var cacheStore: null/);
    assert.match(src, /property string loadedKey: ""/);
    assert.match(
        src,
        new RegExp('cacheStore\\.record\\("' + contract.id
            + '", Date\\.now\\(\\), currentKey\\)')
    );
    assert.match(src, new RegExp('cacheStore\\.put\\(\\s*"' + contract.id + '"'));
    assert.match(src, /onCurrentKeyChanged:\s*reconcileLocationKey\(\)/);
    assert.match(src, /loadedKey !== "" && loadedKey !== currentKey/);
    assert.match(src, /clearLoadedState\(\)/);
    assert.match(src, contract.fullKey);
    if (contract.antiRejuvenation)
        assert.match(src, contract.antiRejuvenation);
    assert.equal(
        (src.match(/\bProcess\s*\{/g) || []).length,
        contract.processCount,
        contract.id+" process count"
    );
    assert.equal(
        (src.match(/\bTimer\s*\{/g) || []).length,
        contract.timerCount,
        contract.id+" timer count"
    );
    assert.doesNotMatch(src, /FileView\s*\{/);
}

// Coastal specifically tracks product age independently.
const coastal = read("services/weather/CoopsCoastalService.qml");
assert.match(coastal, /property date waterLastUpdated/);
assert.match(coastal, /property date tideLastUpdated/);
assert.match(coastal, /waterUsingPersistentCache/);
assert.match(coastal, /tideUsingPersistentCache/);

// River cache age stays anchored to base gauge receipt; restored stage/context
// are omitted from a new persistent write until each live refresh arrives.
const river = read("services/weather/NwpsRiverService.qml");
assert.match(river, /const receivedAtMs = lastUpdated\.getTime\(\)/);
assert.match(river, /contextUsingPersistentCache\s*\? null : gaugeContext/);

// GROUND receives the one shared writer and reports restored data as CACHE.
const ground = read("widgets/weather/StationGround.qml");
assert.match(ground, /property var persistentCacheStore: null/);
for (const service of ["riverService","marineService","coastalService"]) {
    assert.match(
        ground,
        new RegExp('"usingCache": ' + service + '\\.usingPersistentCache')
    );
}
assert.equal(
    (ground.match(/cacheStore:\s*ground\.persistentCacheStore/g) || []).length,
    2
);

const station = read("widgets/weather/WeatherStationW.qml");
assert.match(
    station,
    /persistentCacheStore:\s*weatherStation\.persistentCacheStore/
);
assert.equal(
    (station.match(/WeatherServices\.NwpsRiverService\s*\{/g) || []).length,
    1
);
assert.match(
    station,
    /WeatherServices\.NwpsRiverService\s*\{[\s\S]*?cacheStore:\s*weatherStation\.persistentCacheStore/
);

// Volatile visual sources remain separate from the observation JSON cache.
for (const file of [
    "services/weather/NowcoastLightningService.qml"
]) {
    const src = read(file);
    assert.doesNotMatch(src, /cacheStore\.put\(/);
    assert.doesNotMatch(src, /usingPersistentCache/);
}
assert.equal(
    runtime.sourceSpec("lightning").retention,
    "FRAME_CACHE"
);
assert.equal(
    runtime.sourceSpec("nws-alerts").retention,
    "PERSISTENT_LAST_GOOD"
);
for (const id of ["mrms-radar","rainviewer"])
    assert.equal(runtime.sourceSpec(id).retention, "FRAME_CACHE");
for (const id of ["firms","hms-smoke"])
    assert.equal(runtime.sourceSpec(id).retention, "OPERATOR_SNAPSHOT");
assert.equal(runtime.sourceSpec("moon").retention, "KEY_BOUND");
assert.equal(runtime.sourceSpec("planet-rise-set").retention, "KEY_BOUND");

console.log("Weather persistent cache M6 keyed GROUND feeds: PASS");
