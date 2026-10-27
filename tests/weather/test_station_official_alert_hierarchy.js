#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(
    path.join(root, "widgets/weather/StationOfficialAlertPolicy.js"),
    "utf8"
).replace(/^\.pragma library\s*/m, "");
const policy = {Date, Number, String, Array, Math, isFinite};
vm.runInNewContext(source, policy);

assert.equal(typeof policy.summary, "function");
assert.equal(typeof policy.compareAlerts, "function");
assert.equal(typeof policy.colorToken, "function");

function alert(id, severity, urgency, listingState = "ACTIVE", expires = "2026-10-27T14:00:00Z") {
    return {
        id,
        event: id + " Warning",
        headline: id + " headline",
        area: "TEST AREA",
        issuer: "NWS TEST OFFICE",
        severity,
        urgency,
        certainty: "Likely",
        listingState,
        expires,
    };
}

let summary = policy.summary([]);
assert.equal(summary.available, false);
assert.equal(summary.count, 0);
assert.equal(summary.headerText, "");
assert.equal(summary.dockText, "");

summary = policy.summary([
    alert("moderate", "Moderate", "Expected"),
    alert("severe", "Severe", "Expected"),
]);
assert.equal(summary.available, true);
assert.equal(summary.event, "SEVERE WARNING");
assert.equal(summary.severity, "SEVERE");
assert.equal(summary.colorToken, "orange");
assert.equal(summary.headerText, "NWS SEVERE // 2");
assert.equal(summary.dockText, "2");
assert.equal(summary.expiresLabel, "2026-10-27 14:00Z");

// Severity remains the first hierarchy dimension even during the one-check
// RECHECK window. The lifecycle marker is explicit instead of silently
// downgrading the official severity.
summary = policy.summary([
    alert("severe", "Severe", "Immediate"),
    alert("extreme", "Extreme", "Immediate", "RECHECK PENDING"),
]);
assert.equal(summary.event, "EXTREME WARNING");
assert.equal(summary.recheckPending, true);
assert.equal(summary.headerText, "NWS EXTREME // ?");
assert.equal(summary.colorToken, "red");

// At identical official severity + urgency, currently listed beats retained
// RECHECK PENDING state.
summary = policy.summary([
    alert("pending", "Severe", "Immediate", "RECHECK PENDING"),
    alert("active", "Severe", "Immediate", "ACTIVE"),
]);
assert.equal(summary.event, "ACTIVE WARNING");
assert.equal(summary.recheckPending, false);

assert.equal(policy.colorToken("Extreme"), "red");
assert.equal(policy.colorToken("Severe"), "orange");
assert.equal(policy.colorToken("Moderate"), "yellow");
assert.equal(policy.colorToken("Minor"), "cyan");
assert.equal(policy.colorToken("Unknown"), "white");

const windowSource = fs.readFileSync(
    path.join(root, "widgets/weather/WeatherStationW.qml"), "utf8"
);
const homeSource = fs.readFileSync(
    path.join(root, "widgets/weather/StationHome.qml"), "utf8"
);
const dockSource = fs.readFileSync(
    path.join(root, "modules/Weather.qml"), "utf8"
);
const shellSource = fs.readFileSync(path.join(root, "shell.qml"), "utf8");

assert.match(windowSource, /StationOfficialAlertPolicy\.js" as OfficialAlertPolicy/);
assert.match(windowSource, /readonly property var officialAlertSummary:/);
assert.match(
    windowSource,
    /readonly property string sourceStatusDisplay:\s*\{\s*if \(officialAlertSummary\.available\)\s*return officialAlertSummary\.headerText;/
);
assert.match(
    windowSource,
    /readonly property color sourceStatusColor:\s*\{\s*if \(officialAlertSummary\.available\)\s*return officialAlertColor/
);
assert.match(
    windowSource,
    /StationHome\s*\{[\s\S]*?nwsAlertSource: weatherStation\.nwsAlertSource/
);

assert.match(homeSource, /property var nwsAlertSource: null/);
assert.match(homeSource, /title: "OFFICIAL ALERT \/\/ NWS"/);
assert.match(homeSource, /visible: home\.officialAlertSummary\.available/);
for (const token of [
    "officialAlertSummary.event",
    "officialAlertSummary.listingState",
    "officialAlertSummary.severity",
    "officialAlertSummary.urgency",
    "officialAlertSummary.headline",
    "officialAlertSummary.area",
    "officialAlertSummary.certainty",
    "officialAlertSummary.expiresLabel",
    "officialAlertSummary.issuer",
])
    assert.ok(homeSource.includes(token), token);

assert.match(dockSource, /property var nwsAlertSource: null/);
assert.match(dockSource, /id: officialAlertDockBadge/);
assert.match(dockSource, /visible: weatherDock\.officialAlertSummary\.available/);
assert.match(dockSource, /text: weatherDock\.officialAlertSummary\.dockText/);
assert.match(dockSource, /normalForegroundColor: weatherColor/);
assert.match(dockSource, /normalDockGlowColor: weatherColor/);

// The ordinary weather classifier must remain independent from official
// bulletin state. Alerts are a separate projection, never weatherCode input.
const weatherStateStart = dockSource.indexOf("readonly property var weatherState:");
const skyCycleStart = dockSource.indexOf("readonly property var skyCycle:", weatherStateStart);
assert.ok(weatherStateStart >= 0 && skyCycleStart > weatherStateStart);
const weatherClassifier = dockSource.slice(weatherStateStart, skyCycleStart);
assert.doesNotMatch(weatherClassifier, /nwsAlert|officialAlert|NWS/);

const badgeStart = dockSource.indexOf("id: officialAlertDockBadge");
const rightClickStart = dockSource.indexOf("onRightClicked:", badgeStart);
assert.ok(badgeStart >= 0 && rightClickStart > badgeStart);
const badgeArea = dockSource.slice(badgeStart, rightClickStart);
assert.doesNotMatch(badgeArea, /Process\s*\{|Timer\s*\{|curl|weatherState\s*=/);

assert.match(
    shellSource,
    /Weather\s*\{[\s\S]*?nwsAlertSource: nwsOfficialAlerts/
);
assert.match(
    shellSource,
    /WeatherStationW\s*\{[\s\S]*?nwsAlertSource: nwsOfficialAlerts/
);

const policySource = fs.readFileSync(
    path.join(root, "widgets/weather/StationOfficialAlertPolicy.js"), "utf8"
);
assert.doesNotMatch(policySource, /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest/);

console.log("Weather official-alert HOME/header/dock hierarchy contracts: PASS");
