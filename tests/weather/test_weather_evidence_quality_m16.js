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

for (const fn of [
    "thresholdMeasurementKind",
    "categoryRank",
    "observedThresholdContext",
    "timelineRow",
    "evidenceTimeline"
]) {
    assert.equal(typeof eventCtx[fn], "function", fn);
}

const base = Date.UTC(2026, 10, 2, 16, 0, 0);

const gaugeContext = {
    available:true,
    stageUnits:"ft",
    flowUnits:"kcfs",
    thresholds:[
        {id:"action", label:"ACTION", stage:8, flow:0.50},
        {id:"minor", label:"MINOR", stage:10, flow:1.00},
        {id:"moderate", label:"MODERATE", stage:12, flow:1.50},
        {id:"major", label:"MAJOR", stage:14, flow:2.00}
    ],
    impacts:[]
};

const minorGauge = {
    observedCategory:{id:"minor", label:"MINOR", rank:2}
};

const stageflowCrossing = {
    observed:{
        available:true,
        primaryName:"STAGE",
        primaryUnits:"ft",
        data:[
            {
                validMillis:base - 60 * 60000,
                validLabel:"2026-11-02 15:00Z",
                primary:9.80
            },
            {
                validMillis:base - 10 * 60000,
                validLabel:"2026-11-02 15:50Z",
                primary:10.25
            }
        ]
    }
};

let threshold = eventCtx.observedThresholdContext(
    minorGauge,
    gaugeContext,
    stageflowCrossing
);
assert.equal(threshold.available, true);
assert.equal(threshold.supported, true);
assert.equal(threshold.measurementKind, "stage");
assert.equal(threshold.units, "ft");
assert.equal(threshold.thresholdId, "minor");
assert.equal(threshold.thresholdLabel, "MINOR");
assert.equal(threshold.thresholdValue, 10);
assert.ok(Math.abs(threshold.aboveBy - 0.25) < 1e-9);
assert.equal(threshold.nextThresholdLabel, "MODERATE");
assert.equal(threshold.nextThresholdValue, 12);
assert.ok(Math.abs(threshold.nextGap - 1.75) < 1e-9);
assert.equal(threshold.crossedInSeries, true);
assert.equal(threshold.crossingFromTimeMs, base - 60 * 60000);
assert.equal(threshold.crossingToTimeMs, base - 10 * 60000);
assert.match(threshold.reason, /CROSSED IN LOADED OBSERVED SERIES/);

const mismatchGauge = {
    observedCategory:{id:"action", label:"ACTION", rank:1}
};
threshold = eventCtx.observedThresholdContext(
    mismatchGauge,
    gaugeContext,
    stageflowCrossing
);
assert.equal(threshold.available, true);
assert.equal(threshold.supported, false);
assert.equal(threshold.thresholdId, "minor");
assert.equal(threshold.crossedInSeries, false);
assert.match(threshold.reason, /CLAIM WITHHELD/);

const unitMismatch = {
    observed:{
        available:true,
        primaryName:"STAGE",
        primaryUnits:"m",
        data:[
            {validMillis:base - 10 * 60000, primary:3.1}
        ]
    }
};
threshold = eventCtx.observedThresholdContext(
    minorGauge,
    gaugeContext,
    unitMismatch
);
assert.equal(threshold.available, false);
assert.equal(threshold.supported, false);
assert.match(threshold.reason, /UNITS DO NOT MATCH/);

const flowGauge = {
    observedCategory:{id:"minor", label:"MINOR", rank:2}
};
const flowCrossing = {
    observed:{
        available:true,
        primaryName:"FLOW",
        primaryUnits:"kcfs",
        data:[
            {
                validMillis:base - 40 * 60000,
                validLabel:"2026-11-02 15:20Z",
                primary:0.90
            },
            {
                validMillis:base - 5 * 60000,
                validLabel:"2026-11-02 15:55Z",
                primary:1.10
            }
        ]
    }
};
threshold = eventCtx.observedThresholdContext(
    flowGauge,
    gaugeContext,
    flowCrossing
);
assert.equal(threshold.available, true);
assert.equal(threshold.supported, true);
assert.equal(threshold.measurementKind, "flow");
assert.equal(threshold.thresholdId, "minor");
assert.equal(threshold.crossedInSeries, true);
assert.equal(threshold.units, "kcfs");

const noneGauge = {
    observedCategory:{id:"none", label:"NO FLOODING", rank:0}
};
const belowAction = {
    observed:{
        available:true,
        primaryName:"STAGE",
        primaryUnits:"ft",
        data:[
            {
                validMillis:base - 5 * 60000,
                validLabel:"2026-11-02 15:55Z",
                primary:7.50
            }
        ]
    }
};
threshold = eventCtx.observedThresholdContext(
    noneGauge,
    gaugeContext,
    belowAction
);
assert.equal(threshold.available, true);
assert.equal(threshold.supported, true);
assert.equal(threshold.thresholdId, "");
assert.equal(threshold.crossedInSeries, false);
assert.match(threshold.reason, /BELOW ACTION/);

const unknownMeasurement = {
    observed:{
        available:true,
        primaryName:"PRIMARY",
        primaryUnits:"ft",
        data:[
            {validMillis:base - 5 * 60000, primary:10.25}
        ]
    }
};
threshold = eventCtx.observedThresholdContext(
    minorGauge,
    gaugeContext,
    unknownMeasurement
);
assert.equal(threshold.available, false);
assert.match(threshold.reason, /MEASUREMENT TYPE NOT IDENTIFIED/);

assert.equal(eventCtx.thresholdMeasurementKind("Stage"), "stage");
assert.equal(eventCtx.thresholdMeasurementKind("river height"), "stage");
assert.equal(eventCtx.thresholdMeasurementKind("Flow"), "flow");
assert.equal(eventCtx.thresholdMeasurementKind("Discharge"), "flow");
assert.equal(eventCtx.thresholdMeasurementKind("Primary"), "");

const selected = eventCtx.normalizeSelected("gdacs", {
    id:"FL:200:1",
    name:"Evidence Quality Flood",
    eventTypeLabel:"FLOOD",
    latitude:38.9,
    longitude:-77.0,
    timeMs:base,
    toUtc:"2026-11-02 16:00 UTC"
});
const companions = [{
    sourceLabel:"NASA EONET",
    typeLabel:"Floods",
    title:"Nearby independent record",
    timeMs:base - 12 * 60000
}];
const radar = {
    available:true,
    frameLabel:"NOW",
    timeMs:base - 4 * 60000
};
const lightning = {
    available:true,
    windowMinutes:15,
    timeMs:base - 14 * 60000
};
const flood = {
    available:true,
    gaugeId:"TEST1",
    latestObserved:{
        value:10.25,
        units:"ft",
        timeMs:base - 10 * 60000
    }
};
const timeline = Array.from(eventCtx.evidenceTimeline(
    selected,
    companions,
    radar,
    lightning,
    flood,
    8
));
assert.equal(timeline.length, 5);
assert.deepEqual(
    timeline.map(row => row.provenanceGroup),
    [
        "EVENT RECORD",
        "REMOTE SENSING",
        "GAUGE OBSERVATION",
        "EVENT RECORD",
        "REMOTE SENSING"
    ]
);
assert.deepEqual(
    timeline.map(row => row.sourceLabel),
    [
        "GDACS",
        "NOAA MRMS",
        "NOAA NWPS",
        "NASA EONET",
        "NOAA NOWCOAST"
    ]
);
assert.ok(
    timeline.every((row, index) =>
        index === 0 || timeline[index - 1].timeMs >= row.timeMs
    )
);
assert.ok(
    timeline.every(row =>
        typeof row.provenanceGroup === "string"
        && row.provenanceGroup.length > 0
        && typeof row.sourceLabel === "string"
        && row.sourceLabel.length > 0
        && typeof row.provenance === "string"
        && row.provenance.length > 0
    )
);

const runtimeSource = read("services/weather/WeatherRuntimePolicy.js")
    .replace(/^\.pragma library\s*/m, "");
const runtimeCtx = {
    Date, Math, Number, String, Array, Object, JSON, RegExp,
    isFinite, isNaN
};
vm.runInNewContext(runtimeSource, runtimeCtx, {
    filename:"services/weather/WeatherRuntimePolicy.js"
});
assert.equal(runtimeCtx.ageMinutes(base - 10 * 60000, base), 10);
assert.equal(runtimeCtx.compactAgeMinutes(10), "10m");
assert.equal(runtimeCtx.compactAgeMinutes(90), "1.5h");

const card = read("widgets/weather/StationEventContextCard.qml");
assert.match(
    card,
    /WeatherRuntimePolicy\.js" as RuntimePolicy/
);
assert.match(card, /property real runtimeNowMs: Date\.now\(\)/);
assert.match(card, /RuntimePolicy\.ageMinutes/);
assert.match(card, /RuntimePolicy\.compactAgeMinutes/);
for (const token of ["FRESH", "RECENT", "AGING", "OLDER"]) {
    assert.ok(card.includes(token), token);
}
for (const phrase of [
    "OBSERVED THRESHOLD // CLAIM WITHHELD",
    "CROSSING OBSERVED",
    "CATEGORY ALIGNED",
    "RECENCY = CLOCK AGE, NOT PROVIDER VALIDITY",
    "ROWS RETAIN SOURCE + GROUP PROVENANCE",
    "NOT ONE MERGED INCIDENT HISTORY"
]) {
    assert.ok(card.includes(phrase), phrase);
}
assert.match(card, /modelData\.provenanceGroup/);
assert.match(card, /modelData\.sourceLabel/);
assert.match(card, /modelData\.provenance/);
assert.equal((card.match(/\bTimer\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bProcess\s*\{/g) || []).length, 0);
assert.equal((card.match(/\bFileView\s*\{/g) || []).length, 0);

const map = read("widgets/weather/StationDiscovery.qml");
assert.match(
    map,
    /runtimeNowMs:\s*stationDiscovery\.runtimeNowMs/
);
assert.doesNotMatch(map, /Timer\s*\{[\s\S]*?evidence/i);

const policy = read("widgets/weather/StationEventContextPolicy.js");
assert.doesNotMatch(policy, /curl|https:\/\//);
assert.doesNotMatch(policy, /Timer\s*\{|Process\s*\{|FileView\s*\{/);

console.log("Weather M16 evidence freshness and threshold quality: PASS");
