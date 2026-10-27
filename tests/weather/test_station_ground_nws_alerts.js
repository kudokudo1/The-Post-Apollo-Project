#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
function load(file) {
    const source = fs.readFileSync(path.join(root, file), "utf8")
        .replace(/^\.pragma library\s*/m, "");
    const context = {Date, Number, String, isFinite, Array, JSON, Object, Math};
    vm.runInNewContext(source, context);
    return context;
}

const policy = load("services/notifications/NwsOfficialAlertPolicy.js");
const now = Date.parse("2026-10-27T09:00:00Z");
function feature(id, severity, urgency, expires) {
    return {
        type: "Feature",
        id,
        properties: {
            id,
            event: severity + " Test Alert",
            status: "Actual",
            severity,
            urgency,
            certainty: "Likely",
            messageType: "Alert",
            category: "Met",
            response: "Prepare",
            headline: severity + " test headline",
            areaDesc: "TEST AREA",
            senderName: "NWS TEST OFFICE",
            sent: "2026-10-27T08:00:00Z",
            updated: "2026-10-27T08:05:00Z",
            effective: "2026-10-27T08:00:00Z",
            onset: "2026-10-27T08:10:00Z",
            expires,
            ends: expires,
        },
    };
}
const raw = JSON.stringify({
    type: "FeatureCollection",
    features: [
        feature("moderate", "Moderate", "Expected", "2026-10-27T13:00:00Z"),
        feature("extreme", "Extreme", "Immediate", "2026-10-27T14:00:00Z"),
    ],
});
const parsed = policy.parseActive(raw, now);
assert.equal(parsed.length, 2);
let outcome = policy.advance({}, parsed);
let rows = Array.from(policy.visibleAlerts(outcome.state));
assert.deepEqual(rows.map(x => x.id), ["extreme", "moderate"]);
assert.equal(rows[0].severity, "Extreme");
assert.equal(rows[0].urgency, "Immediate");
assert.equal(rows[0].certainty, "Likely");
assert.equal(rows[0].effective, "2026-10-27T08:00:00.000Z");
assert.equal(rows[0].expires, "2026-10-27T14:00:00.000Z");
assert.equal(rows[0].issuer, "NWS TEST OFFICE");
assert.equal(rows[0].listingState, "ACTIVE");

outcome = policy.advance(outcome.state, []);
rows = Array.from(policy.visibleAlerts(outcome.state));
assert.equal(rows.length, 2);
assert.ok(rows.every(x => x.listingState === "RECHECK PENDING"));
outcome = policy.advance(outcome.state, []);
assert.equal(policy.visibleAlerts(outcome.state).length, 0);

const producer = fs.readFileSync(
    path.join(root, "services/notifications/NwsOfficialAlertNotificationProducer.qml"),
    "utf8"
);
const shell = fs.readFileSync(path.join(root, "shell.qml"), "utf8");
const station = fs.readFileSync(
    path.join(root, "widgets/weather/WeatherStationW.qml"), "utf8"
);
const ground = fs.readFileSync(
    path.join(root, "widgets/weather/StationGround.qml"), "utf8"
);

assert.match(producer, /POST_APOLLO_NWS_ALERT_POINT/);
assert.match(producer, /api\.weather\.gov\/alerts\/active\?point=/);
assert.match(producer, /Accept: application\/geo\+json/);
assert.match(producer, /Post-Apollo-WeatherStation/);
assert.match(producer, /interval: 900000/);
assert.match(producer, /readonly property var alertList: NwsPolicy\.visibleAlerts\(activeAlerts\)/);
assert.match(producer, /readonly property bool configured: alertPoint !== ""/);
assert.match(producer, /producer\.lastUpdated = new Date\(\)/);
assert.match(producer, /producer\.errorText = "NWS REQUEST FAILED"/);
assert.doesNotMatch(producer, /weatherService|wttr\.in/);

assert.match(shell, /NwsOfficialAlertNotificationProducer \{ id: nwsOfficialAlerts \}/);
assert.match(shell, /nwsAlertSource: nwsOfficialAlerts/);
assert.match(station, /property var nwsAlertSource: null/);
assert.match(station, /StationGround \{[\s\S]*?nwsAlertSource: weatherStation\.nwsAlertSource/);

assert.match(ground, /property var nwsAlertSource: null/);
assert.match(ground, /title: "OFFICIAL ALERTS \/\/ NWS"/);
assert.match(ground, /model: ground\.officialAlerts/);
assert.match(ground, /POST_APOLLO_NWS_ALERT_POINT=LAT,LON/);
assert.match(ground, /WEATHER FIX IS NEVER USED FOR EMERGENCY TARGETING/);
assert.match(ground, /modelData\.severity/);
assert.match(ground, /modelData\.urgency/);
assert.match(ground, /modelData\.certainty/);
assert.match(ground, /modelData\.effective/);
assert.match(ground, /modelData\.expires/);
assert.match(ground, /modelData\.issuer/);
assert.match(ground, /modelData\.listingState/);
assert.match(ground, /OFFICIAL API PRODUCT, NOT FORECAST INFERENCE/);

const alertArea = ground.slice(
    ground.indexOf('title: "OFFICIAL ALERTS // NWS"'),
    ground.indexOf('title: "AIR // PARTICULATES"')
);
assert.doesNotMatch(alertArea, /Process\s*\{|curl|Qt\.openUrlExternally/);

console.log("Weather GROUND official NWS shared-source contracts: PASS");
