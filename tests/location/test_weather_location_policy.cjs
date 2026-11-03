#!/usr/bin/env node
"use strict";
// M5: pure location routing contract. No network or live location access.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const src = fs.readFileSync(
    path.join(__dirname, "../../services/location/WeatherLocationPolicy.js"),
    "utf8"
).replace(/^\.pragma library\s*/, "");
const policy = vm.runInNewContext(src + "\n;({manualPoint, requestContextKey, locationQuery, coordinates})");
const home = {label:"Example",latitude:38.8243,longitude:-76.7451,source:"MANUAL"};
const alaska = {label:"Anchorage",latitude:61.2181,longitude:-149.9003,source:"MANUAL"};
assert.equal(policy.manualPoint(home).latitude, 38.8243);
assert.equal(policy.requestContextKey(home, ""), "MANUAL|38.8243|-76.7451");
assert.equal(policy.locationQuery(home, "ignored"), "38.8243,-76.7451");
assert.equal(policy.coordinates(home, "22", "33").latitude, "38.8243");
assert.equal(policy.coordinates(home, "22", "33").longitude, "-76.7451");

// Moving Explore changes both request identity and derived coordinates.
assert.equal(policy.requestContextKey(alaska, ""),
             "MANUAL|61.2181|-149.9003");
assert.notEqual(policy.requestContextKey(home, ""),
                policy.requestContextKey(alaska, ""));
assert.equal(policy.locationQuery(alaska, ""), "61.2181,-149.9003");
assert.equal(policy.coordinates(alaska, "", "").latitude, "61.2181");

// Explicit 0°/0° is a valid user selection; blank strings are not.
const zero={label:"Equator",latitude:0,longitude:0,source:"MANUAL"};
assert.equal(policy.manualPoint(zero).latitude,0);
assert.equal(policy.locationQuery(zero, ""), "0,0");
for (const candidate of [
    null, {}, {source:"AUTO",latitude:0,longitude:0},
    {source:"MANUAL",latitude:"",longitude:""},
    {source:"MANUAL",latitude:"0",longitude:"0"},
    {source:"MANUAL",latitude:91,longitude:0},
    {source:"MANUAL",latitude:40,longitude:-181},
    {source:"MANUAL",latitude:Infinity,longitude:0},
]) {
    assert.equal(policy.manualPoint(candidate), null);
}
assert.equal(policy.locationQuery(null, ""), "");
assert.equal(policy.locationQuery(null, " New York "), "New York");
assert.equal(policy.requestContextKey(null,""), "LEGACY|");
assert.equal(policy.coordinates(null,"","").latitude,"");
assert.equal(policy.coordinates(null,"", "0").longitude,"");
assert.equal(policy.coordinates(null,"0","0").longitude,"0");
assert.equal(policy.coordinates(null,"-90","180").latitude,"-90");
for (const bad of [
    ["", "0"],["0",""],["100","0"],["0","181"],
    ["12.3abc","0"],["NaN","0"],["Infinity","0"]
]) {
    assert.equal(policy.coordinates(null,bad[0],bad[1]).latitude, "");
}
const wttrResponse = {lat:"40",lon:"-75"};
assert.equal(policy.coordinates(home,wttrResponse.lat,wttrResponse.lon).latitude,
             "38.8243", "provider cannot rewrite Home");
console.log("Weather Location M5 coordinate precedence and strict missing-input policy: PASS");
