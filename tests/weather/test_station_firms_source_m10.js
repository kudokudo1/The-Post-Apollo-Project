#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");
const policy = {};
vm.runInNewContext(
    read("services/weather/FirmsHotspotPolicy.js")
        .replace(/^\.pragma library\s*/m, ""),
    policy
);

function status(source, area) {
    return policy.sourceState(source, area);
}
const validView = {valid:true};
const tooWide = {valid:false,reason:"ZOOM IN // VIEW TOO WIDE"};
const configured = {configured:true,loading:false,ready:false,failed:false,
                    hotspots:[],errorText:""};

assert.equal(status(null,validView),"UNAVAILABLE");
assert.equal(status({configured:false},validView),"KEY REQUIRED");
assert.equal(status({...configured},validView),"MANUAL READY");
assert.equal(status({...configured},tooWide),"ZOOM IN // VIEW TOO WIDE");
assert.equal(status({...configured,loading:true},validView),"RECEIVING");
assert.equal(status({...configured,ready:true,hotspots:[]},validView),"HOTSPOTS 0");
assert.equal(status({...configured,ready:true,hotspots:[{},{}]},validView),
             "HOTSPOTS 2");
assert.equal(status({...configured,failed:true,
                     errorText:"FIRMS REQUEST COOLDOWN"},validView),
             "FIRMS REQUEST COOLDOWN");
assert.equal(status({...configured,failed:true,
                     errorText:"FIRMS REQUEST FAILED"},validView),
             "FIRMS REQUEST FAILED");
assert.equal(status({...configured,ready:true,hotspots:[{},{}],
                     failed:true,errorText:"FIRMS RESPONSE UNAVAILABLE"},validView),
             "LAST GOOD 2 // FIRMS RESPONSE UNAVAILABLE");
assert.equal(status({...configured,loading:true,ready:true,
                     failed:true,hotspots:[{}]},validView),"RECEIVING");
assert.equal(status({...configured,ready:true,failed:true,
                     hotspots:[{}],errorText:""},validView),
             "LAST GOOD 1 // REQUEST FAILED");

const ui = read("widgets/weather/StationDiscovery.qml");
assert.match(ui,/name:"NASA FIRMS \/\/ VIIRS HOTSPOTS",[\s\S]*?state: FirmsAreaPolicy\.sourceState\(firmsService, firmsArea\)/);
assert.match(ui,/name:"NASA FIRMS \/\/ VIIRS NOAA-21 HOTSPOTS",[\s\S]*?state: FirmsAreaPolicy\.sourceState\(firmsService, firmsArea\)/);
assert.match(ui,/text: FirmsAreaPolicy\.sourceState\(\s*firmsService, stationDiscovery\.firmsArea\)/);
assert.match(ui,/GET|FREE NASA FIRMS MAP_KEY REQUIRED/);
assert.match(ui,/SET POST_APOLLO_FIRMS_MAP_KEY BEFORE QUICKSHELL LAUNCH/);
assert.match(ui,/KEY NEVER SHOWN OR PASSED IN PROCESS ARGV/);
assert.doesNotMatch(ui,/firmsService\.mapKey/);

const service = read("services/weather/FirmsHotspotService.qml");
assert.match(service,/Quickshell\.env\("POST_APOLLO_FIRMS_MAP_KEY"\)/);
assert.match(service,/FirmsPolicy\.parseViirsCsv\(raw, 800\)/);
assert.match(service,/lastRequestMs > 0 && now - lastRequestMs < 30000/);
assert.doesNotMatch(service,/Qt\.openUrlExternally/);
assert.equal((service.match(/\bTimer\s*\{/g)||[]).length,0);

console.log("Weather FIRMS M10 truthful source status and secure key setup contract: PASS");
