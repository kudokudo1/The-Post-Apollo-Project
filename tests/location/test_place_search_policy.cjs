#!/usr/bin/env node
"use strict";
// Offline fixture checks: no external requests, live location, or disk writes.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(
    path.join(__dirname, "../../services/location/PlaceSearchPolicy.js"),
    "utf8"
).replace(/^\.pragma library\s*/, "");
const policy = vm.runInNewContext(source + `
;({request, parseResponse, coordinate, cleanLabel, displayLabel})
`);

for (const q of ["", "x", " ", "a".repeat(81), "a\nTokyo", null, undefined]) {
    assert.equal(policy.request(q).reason, "QUERY_INVALID", String(q));
}
const lookup = policy.request("  Tokyo, Japan  ");
assert.equal(lookup.ok, true);
assert.equal(lookup.query, "Tokyo, Japan");
assert.equal(lookup.url,
    "https://geocoding-api.open-meteo.com/v1/search?name=Tokyo%2C%20Japan&count=8&language=en&format=json");
assert.equal(policy.request("Paris?&count=999").url.includes(
    "name=Paris%3F%26count%3D999&count=8"), true);

// Parse multiple same-named places without automatically choosing one.
const fixture = JSON.stringify({
    results: [
        {id:1, name:"Springfield", latitude:39.7989, longitude:-89.644,
         admin1:"Illinois", country:"United States",timezone:"America/Chicago"},
        {id:2, name:"Springfield", latitude:42.1015, longitude:-72.5898,
         admin1:"Massachusetts", country:"United States",
         timezone:"America/New_York"},
        {id:3, name:"Equator", latitude:0, longitude:0,
         country:"Test Country", timezone:"Etc/UTC"}
    ]
});
const parsed = policy.parseResponse(fixture);
assert.equal(parsed.ok, true);
assert.equal(parsed.rows.length, 3);
assert.equal(parsed.rows[0].label, "Springfield, Illinois, United States");
assert.equal(parsed.rows[1].label, "Springfield, Massachusetts, United States");
assert.equal(parsed.rows[0].latitude, 39.7989);
assert.equal(parsed.rows[1].timezone, "America/New_York");
assert.equal(parsed.rows[2].latitude, 0);
assert.equal(parsed.rows[2].longitude, 0);
assert.equal(parsed.rows[0].provider, "OPEN_METEO_GEONAMES");

assert.equal(policy.parseResponse("{}").rows.length, 0);
assert.equal(policy.parseResponse('{"results":[]}').rows.length, 0);
assert.equal(policy.parseResponse("not-json").reason, "JSON_INVALID");
assert.equal(policy.parseResponse("").reason, "RESPONSE_INVALID");
assert.equal(policy.parseResponse("x".repeat(65537)).reason, "RESPONSE_INVALID");
assert.equal(policy.parseResponse('{"error":true,"reason":"limit"}').reason,
             "PROVIDER_ERROR");
assert.equal(policy.parseResponse('{"results":{}}').reason,
             "RESPONSE_INVALID");

for (const invalid of [
    {name:"Unknown",latitude:"",longitude:1},
    {name:"Unknown",longitude:1},
    {name:"Unknown",latitude:90.1,longitude:1},
    {name:"Unknown",latitude:10,longitude:-180.1},
    {name:"<script>",latitude:10,longitude:10},
    {name:"Unknown",latitude:NaN,longitude:2},
]) {
    assert.equal(policy.parseResponse(JSON.stringify({results:[invalid]})).rows.length,
                 0);
}

const many = Array.from({length:30}, (_,i)=>({
    name:"City "+i, latitude:10+i/10,longitude:20+i/10,
    country:"Country",timezone:"Etc/UTC"
}));
const limited = policy.parseResponse(JSON.stringify({results:many}));
assert.equal(limited.ok,true);
assert.equal(limited.rows.length,8);
assert.equal(policy.displayLabel("Paris","Ile-de-France","France"),
             "Paris, Ile-de-France, France");

// Search responses are preview-only; there are no persistence methods.
assert.equal("saveHome" in policy, false);
assert.equal("exploreHere" in policy, false);
console.log("Place Search M4 explicit request, result disambiguation and bounds: PASS");
