#!/usr/bin/env node
"use strict";

// Exercise production WorldClockPolicy against system tzdata from GNU date.
// No host timezone change, network, clock writes or process persistence.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { execFileSync } = require("node:child_process");
const file = path.join(__dirname, "../../services/time/WorldClockPolicy.js");
const src = fs.readFileSync(file, "utf8").replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(src, policy, { filename: "WorldClockPolicy.js" });

function utc(y, m, d, h, minute = 0, second = 0) {
    return Date.UTC(y, m - 1, d, h, minute, second);
}
function zoneOffset(zone, timeMs) {
    return execFileSync(
        "date", ["-d", "@" + String(Math.floor(timeMs / 1000)), "+%z"],
        { encoding: "utf8", env: { ...process.env, TZ: zone, LC_ALL: "C" } }
    ).trim();
}
function at(zone, time, use24Hour) {
    return policy.snapshot(time, zoneOffset(zone, time), use24Hour);
}

for (const [raw, expected] of [
    ["+0000", 0], ["-0000", 0], ["-0400", -240],
    ["+0545", 345], ["+1245", 765], ["+1400", 840]
]) assert.equal(policy.parseOffset(raw), expected);
for (const invalid of [
    "", null, undefined, "+25", "GMT", "-05:00",
    "+1460", "+1401", "+9999", "UTC+05:45", {},
]) assert.equal(policy.parseOffset(invalid), null, String(invalid));

const moment = utc(2026, 10, 22, 17, 19, 28);
assert.equal(at("UTC", moment, true).readout, "17:19:28//PM");
assert.equal(at("UTC", moment, false).readout, "05:19:28//PM");
assert.equal(at("America/New_York", moment, true).readout, "13:19:28//PM");
assert.equal(at("America/New_York", moment, false).readout, "01:19:28//PM");
assert.equal(at("Asia/Tokyo", moment, true).readout, "02:19:28//AM");
assert.equal(at("Asia/Tokyo", moment, true).localDate, "2026-10-23");
assert.equal(at("Asia/Kathmandu", moment, true).utcOffsetLabel, "UTC+05:45");

// The system zone database controls DST. No fixed -05/-04 offsets are coded.
const winter = utc(2026, 1, 22, 17);
const summer = utc(2026, 7, 22, 17);
assert.equal(at("America/New_York", winter, true).utcOffsetLabel, "UTC-05:00");
assert.equal(at("America/New_York", summer, true).utcOffsetLabel, "UTC-04:00");
assert.equal(at("Europe/London", winter, true).utcOffsetLabel, "UTC+00:00");
assert.equal(at("Europe/London", summer, true).utcOffsetLabel, "UTC+01:00");

// The same instant can occur twice in a fall-back civil hour.
const pre = at("America/New_York", utc(2026, 11, 1, 5, 30), true);
const post = at("America/New_York", utc(2026, 11, 1, 6, 30), true);
assert.equal(pre.readout, "01:30:00//AM");
assert.equal(post.readout, "01:30:00//AM");
assert.equal(pre.utcOffsetLabel, "UTC-04:00");
assert.equal(post.utcOffsetLabel, "UTC-05:00");
assert.equal(at("America/New_York", utc(2026, 3, 8, 7), true).readout, "03:00:00//AM");

for (const v of [null, undefined, "", {}, true, Number.NaN, Infinity]) {
    assert.equal(policy.snapshot(v, "+0000", true).state, "unavailable");
}
assert.equal(policy.snapshot(moment, "+0000", "true").state, "unavailable");
assert.equal(policy.snapshot(moment, "+9999", true).state, "unavailable");
assert.equal(policy.snapshot(utc(2200, 1, 1, 0), "+0000", true).state, "unavailable");

console.log("TIMEW WORLD CLOCK POLICY: PASS");
