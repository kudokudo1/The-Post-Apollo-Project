#!/usr/bin/env node
"use strict";
// M6c: provider diagnostics state is derived from samples; no extra fetch.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const src = fs.readFileSync(
    path.join(__dirname, "../../widgets/weather/StationProviderDiagnosticsPolicy.js"),
    "utf8"
).replace(/^\.pragma library\s*/, "");
const policy = vm.runInNewContext(src +
    "\n;({millis,ageText,providerName,stateFor,snapshot})");

const now = 1793700000000;
assert.equal(policy.ageText(now - 30000, now), "<1m");
assert.equal(policy.ageText(now - 125000, now), "2m");
assert.equal(policy.ageText(now - 2*3600000 - 10*60000, now), "2h 10m");
assert.equal(policy.ageText(now + 30000, now), "--");
assert.equal(policy.ageText(null, now), "--");
assert.equal(policy.providerName("WTTR"), "WTTR.IN");
assert.equal(policy.providerName("OPEN_METEO"), "OPEN-METEO");
assert.equal(policy.providerName("OTHER"), "NONE");
assert.equal(policy.stateFor("PARSE_FAILED"), "DATA INVALID");
assert.equal(policy.stateFor("REQUEST_FAILED"), "REQUEST FAILED");

const base = {
    ready:true, loading:false, activeProvider:"WTTR",cachedProvider:"",
    usingCache:false,lastUpdated:now-2*60000,
    selectedPlace:{label:"Example City",latitude:38.8243,longitude:-76.7451,
                   source:"MANUAL"},
    primaryStatus:"READY",fallbackStatus:"IDLE",fallbackError:"",
    primaryLastSuccessAt:now-2*60000,fallbackLastSuccessAt:null,
    aqiReady:true,aqiLoading:false,aqiUsingCache:false,
    aqiLastUpdated:now-10*60000,aqiError:"",error:""
};
let x=policy.snapshot(base,now);
assert.equal(x.currentState,"LIVE");
assert.equal(x.header,"LIVE // WTTR");
assert.equal(x.providerLabel,"WTTR.IN");
assert.equal(x.currentAge,"2m");
assert.equal(x.primary.age,"2m");
assert.equal(x.fallback.age,"--");
assert.equal(x.aqi.state,"LIVE");
assert.equal(x.location,"Example City");

x=policy.snapshot({
    ...base,activeProvider:"OPEN_METEO",primaryStatus:"REQUEST_FAILED",
    fallbackStatus:"READY",fallbackLastSuccessAt:now-60000
},now);
assert.equal(x.currentState,"FALLBACK");
assert.equal(x.header,"FALLBACK // METEO");
assert.equal(x.providerLabel,"OPEN-METEO // FALLBACK");
assert.equal(x.reason,"PRIMARY REQUEST FAILED");
assert.equal(x.fallback.age,"1m");
assert.equal(x.primary.state,"REQUEST FAILED");

x=policy.snapshot({
    ...base,activeProvider:"CACHE",usingCache:true,cachedProvider:"OPEN_METEO",
    primaryStatus:"FETCHING",aqiUsingCache:true
},now);
assert.equal(x.currentState,"CACHE");
assert.equal(x.header,"CACHE // METEO");
assert.equal(x.providerLabel,"CACHE // OPEN-METEO");
assert.equal(x.aqi.state,"CACHE");
assert.match(x.reason,/NOT A LIVE READING/);
assert.equal(x.primary.age,"2m"); // only actual successful provider call, not cache

x=policy.snapshot({
    ...base,ready:false,loading:true,activeProvider:"NONE",
    primaryStatus:"FETCHING",lastUpdated:null,selectedPlace:null,
    aqiReady:false,aqiLoading:true,aqiLastUpdated:null
},now);
assert.equal(x.currentState,"READING");
assert.equal(x.header,"WEATHER // READING");
assert.equal(x.location,"UNSPECIFIED // LEGACY LOCATION");
assert.equal(x.currentAge,"--");
assert.equal(x.aqi.state,"READING");

x=policy.snapshot({
    ...base,ready:false,loading:false,primaryStatus:"REQUEST_FAILED",
    fallbackStatus:"REQUEST_FAILED",fallbackError:"connection timeout",
    error:"weather providers unavailable"
},now);
assert.equal(x.currentState,"OFFLINE");
assert.equal(x.header,"WEATHER // OFFLINE");
assert.equal(x.reason,"connection timeout");

x=policy.snapshot({
    ...base,activeProvider:"CACHE",usingCache:true,
    cachedProvider:"WTTR",primaryLastSuccessAt:null,
    fallbackLastSuccessAt:null
},now);
assert.equal(x.currentState,"CACHE");
assert.equal(x.header,"CACHE // WTTR");
assert.equal(x.primary.age,"--");
assert.equal(x.fallback.age,"--");

// Do not turn failed retrievals into fake live successes.
x=policy.snapshot({ready:false,loading:false,activeProvider:"NONE",
                   primaryStatus:"IDLE",fallbackStatus:"NO_MANUAL_PLACE"},now);
assert.equal(x.currentState,"WAITING");
assert.equal(x.fallback.state,"NO SELECTED PLACE");

console.log("Weather M6c provider diagnostic state and provenance: PASS");
