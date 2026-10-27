#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const js = fs.readFileSync(path.join(root, "widgets/weather/StationGroundPollenPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const pollen = {};
vm.runInNewContext(js, pollen);
const parsed = pollen.species(true, {
    alderPollen: null, birchPollen: -1, grassPollen: 0,
    mugwortPollen: 2.25, olivePollen: "", ragweedPollen: 8.4
});
assert.equal(parsed.length, 6);
assert.deepEqual(Array.from(parsed, item => item.name),
    ["ALDER", "BIRCH", "GRASS", "MUGWORT", "OLIVE", "RAGWEED"]);
assert.equal(parsed[0].label, "--");
assert.equal(parsed[1].label, "--");
assert.equal(parsed[2].label, "0.0 gr/m³");
assert.equal(parsed[2].available, true);
assert.equal(parsed[3].label, "2.3 gr/m³");
assert.equal(parsed[4].label, "--");
assert.equal(parsed[5].label, "8.4 gr/m³");
assert.equal(pollen.species(false, {}).length, 0);
assert.equal(pollen.species(true, {}).filter(x => x.available).length, 0);
assert.equal(pollen.species(true, {grassPollen:"NaN"})[2].label, "--");

const ground = fs.readFileSync(path.join(root, "widgets/weather/StationGround.qml"), "utf8");
const svc = fs.readFileSync(path.join(root, "services/weather/WeatherService.qml"), "utf8");
assert.match(ground, /import "StationGroundPollenPolicy\.js" as PollenDetails/);
assert.match(ground, /readonly property var pollenSpecies: PollenDetails\.species/);
assert.match(ground, /aqiReady && weatherService\.pollenAvailable/);
for(const property of ["alderPollen", "birchPollen", "grassPollen",
                       "mugwortPollen", "olivePollen", "ragweedPollen"]) {
    assert.ok(ground.includes("weatherService." + property), property + " binding");
    assert.ok(svc.includes("property real " + property), property + " owner");
}
assert.match(ground, /title: "POLLEN \/\/ SPECIES"/);
assert.match(ground, /model: ground\.pollenSpecies/);
assert.match(ground, /modelData\.available \? Colors\.green : Colors\.white/);
assert.match(ground, /NO READING, NOT ZERO/);
assert.match(ground, /visible: scrollable/);
assert.match(ground, /title: "AIR \/\/ NEXT 12 HOURS"/);
assert.match(ground, /title: "GASES \/\/ POLLEN"/);
console.log("GROUND individual pollen species and unavailable-state contracts: PASS");
