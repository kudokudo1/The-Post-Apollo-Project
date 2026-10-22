#!/usr/bin/env node
"use strict";

// Pure tests: no local system mutation or QML runtime required.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const script = fs.readFileSync(
    path.join(__dirname, "../../services/time/WorldZoneSearch.js"), "utf8"
).replace(/^\.pragma library\s*/m, "");
const search = vm.createContext({});
vm.runInContext(script, search, { filename: "WorldZoneSearch.js" });

const raw = [
    "Africa/Abidjan",
    "America/Argentina/Buenos_Aires",
    "America/Los_Angeles",
    "America/New_York",
    "America/New_York", // duplicates
    "Asia/Kathmandu",
    "Asia/Tokyo",
    "Etc/GMT+5",
    "Europe/London",
    "Pacific/Chatham",
    "UTC",
    "../../etc/passwd",
    "America/New_York;rm -rf /",
    "$(echo pwned)",
    "/etc/passwd",
    "",
].join("\n");
const catalog = search.parseCatalog(raw);
assert.equal(catalog.length, 10);
assert.equal(catalog.filter(x => x === "America/New_York").length, 1);
assert.equal(catalog.includes("../../etc/passwd"), false);
assert.equal(catalog.includes("America/New_York;rm -rf /"), false);
assert.equal(catalog.includes("Etc/GMT+5"), true);
assert.equal(catalog.includes("America/Argentina/Buenos_Aires"), true);
assert.equal(search.contains(catalog, "America/New_York"), true);
assert.equal(search.contains(catalog, "Europe/Paris"), false);
assert.equal(search.contains(catalog, "../../etc/passwd"), false);

function ids(query, limit = 6) {
    return Array.from(search.search(catalog, query, limit), item => item.id);
}
assert.equal(ids("new york")[0], "America/New_York");
assert.equal(ids("New_York")[0], "America/New_York");
assert.equal(ids("tokyo")[0], "Asia/Tokyo");
assert.equal(ids("Buenos Aires")[0], "America/Argentina/Buenos_Aires");
assert.equal(ids("America Los")[0], "America/Los_Angeles");
assert.equal(ids("europe london")[0], "Europe/London");
assert.equal(ids("Kathmandu")[0], "Asia/Kathmandu");
assert.equal(ids("gmt+5")[0], "Etc/GMT+5");
assert.equal(ids("").length, 0); // empty query returns no suggestions
assert.equal(ids(" ").length, 0);
assert.equal(ids("token-that-does-not-exist").length, 0);
assert.equal(ids("a", 3).length, 3);
assert.equal(ids("a", 1000).length <= 120, true);
assert.equal(ids("a", 0).length, 0);
assert.equal(ids("A".repeat(101)).length, 0);
assert.equal(Array.isArray(search.parseCatalog(8)), true);
assert.equal(search.label("America/New_York"), "America/New York");

// Searching is deterministic and bounded even with large generated inputs.
const more = search.parseCatalog(
    Array.from({ length: 1600 },
        (_, i) => "Area/Place_" + String(i).padStart(4, "0")).join("\n"));
assert.equal(more.length, 1200);
assert.equal(search.search(more, "place").length, 120);

// Real tzdata shapes: iso3166.tab lists country names; zone.tab associates
// countries with IANA identifiers, including multiple zones per country.
const names = search.parseCountryNames([
    "# ISO 3166 sample",
    "US\tUnited States",
    "GB\tBritain (UK)",
    "JP\tJapan",
    "IN\tIndia",
    "XX\tExample Islands",
].join("\n"));
assert.equal(names.US, "United States");
assert.equal(names.JP, "Japan");
assert.equal(search.parseCountryNames(4).US, undefined);
const zoneMap = search.parseCountryZones([
    "# ISO\tcoords\tzone\tcomment",
    "US\t+404251-0740023\tAmerica/New_York\tEastern",
    "US\t+340308-1181434\tAmerica/Los_Angeles\tPacific",
    "JP\t+353916+1394441\tAsia/Tokyo",
    "GB\t+513030-0000731\tEurope/London",
    "IN\t+2232+08822\tAsia/Kathmandu",  // Synthetic mapping tests parser behavior
    "XX,JP\t+0123+04567\tPacific/Chatham",
    "US\t+0000+0000\t../../etc/passwd",
].join("\n"), names);
assert.equal(zoneMap["America/New_York"][0].name, "United States");
assert.equal(zoneMap["Pacific/Chatham"].length, 2);
assert.equal(zoneMap["../../etc/passwd"], undefined);
function countryIds(q) {
    return Array.from(search.search(catalog, q, 120, zoneMap), x => x.id);
}
assert.equal(countryIds("United States").includes("America/New_York"), true);
assert.equal(countryIds("United States").includes("America/Los_Angeles"), true);
assert.equal(countryIds("japan").includes("Asia/Tokyo"), true);
assert.equal(countryIds("US").includes("America/New_York"), true);
assert.equal(countryIds("Britain").includes("Europe/London"), true);
assert.equal(countryIds("India").includes("Asia/Kathmandu"), true);
assert.equal(countryIds("Japan").includes("Africa/Abidjan"), false);
// Unknown/unmapped country names don't manufacture a matching zone.
assert.equal(countryIds("Neverland").length, 0);
assert.equal(Array.isArray(search.search(catalog, "Tokyo", 120, {})), true);
assert.equal(search.search(catalog, "United States", 120, zoneMap)[0].country, "United States");
// Country searches can return many matches, for the scrollable UI.
const syntheticCatalog = search.parseCatalog(
    Array.from({length: 80}, (_, i) => "America/City_" + i).join("\n"));
const manyZones = {};
for (const zone of syntheticCatalog)
    manyZones[zone] = [{code: "US", name: "United States"}];
assert.equal(search.search(syntheticCatalog, "United States", 120, manyZones).length, 80);
assert.equal(search.search(syntheticCatalog, "United States", 5, manyZones).length, 5);

console.log("TIMEW WORLD ZONE SEARCH: PASS");
