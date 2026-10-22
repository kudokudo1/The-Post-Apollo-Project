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
assert.equal(ids("a", 1000).length <= 6, true);
assert.equal(ids("a", 0).length, 0);
assert.equal(ids("A".repeat(101)).length, 0);
assert.equal(Array.isArray(search.parseCatalog(8)), true);
assert.equal(search.label("America/New_York"), "America/New York");

// Searching is deterministic and bounded even with large generated inputs.
const more = search.parseCatalog(
    Array.from({ length: 1600 },
        (_, i) => "Area/Place_" + String(i).padStart(4, "0")).join("\n"));
assert.equal(more.length, 1200);
assert.equal(search.search(more, "place").length, 6);

console.log("TIMEW WORLD ZONE SEARCH: PASS");
