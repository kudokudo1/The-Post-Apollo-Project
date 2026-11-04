// Pure WORLD favorites policy regression tests. No Quickshell or OS writes.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "../..");
const policyPath = path.join(root, "services/time/WorldFavoritesPolicy.js");
const source = fs.readFileSync(policyPath, "utf8")
  .replace(/^\.pragma library\s*$/m, "");
const policy = {};
vm.runInNewContext(source, policy, {filename: policyPath});
const copy = (value) => JSON.parse(JSON.stringify(value));

assert.equal(policy.VERSION, 1);
assert.equal(policy.MAX_FAVORITES, 8);
assert.deepEqual(copy(policy.initialDocument()), {version: 1, zones: []});

for (const bad of ["", "../etc/passwd", "America/New_York;rm", "-UTC",
                   "Asia//Tokyo", "NYC", "a".repeat(101)]) {
  assert.equal(policy.validZone(bad), false, bad);
  assert.equal(policy.toggle([], bad).ok, false, bad);
}
assert.equal(policy.validZone("UTC"), true);
assert.equal(policy.validZone("America/New_York"), true);
assert.equal(policy.validZone("Europe/London"), true);
assert.equal(policy.validZone("Asia/Tokyo"), true);

const initial = policy.initialDocument();
const added = policy.toggle(initial.zones, "America/New_York");
assert.equal(added.ok, true);
assert.equal(added.added, true);
assert.deepEqual(copy(added.document.zones), ["America/New_York"]);
assert.deepEqual(copy(initial.zones), [], "toggle cannot mutate current doc");
assert.equal(policy.contains(added.document.zones, "America/New_York"), true);
const removed = policy.toggle(added.document.zones, "America/New_York");
assert.equal(removed.added, false);
assert.deepEqual(copy(removed.document.zones), []);
const roundtrip = policy.parse(JSON.stringify(added.document));
assert.equal(roundtrip.ok, true);
assert.deepEqual(copy(roundtrip.document), copy(added.document));

const eight = [
  "UTC", "America/New_York", "Europe/London", "Asia/Tokyo",
  "Europe/Paris", "Asia/Seoul", "Australia/Sydney", "Asia/Singapore"
];
let stored = [];
for (const zone of eight) {
  const result = policy.toggle(stored, zone);
  assert.equal(result.ok, true);
  stored = copy(result.document.zones);
}
assert.equal(stored.length, 8);
assert.equal(policy.toggle(stored, "America/Chicago").reason, "FAVORITES_FULL");
assert.equal(policy.toggle(stored, "UTC").added, false,
             "a full favorite list must still permit removal");
assert.equal(policy.parse(JSON.stringify({version: 1, zones: eight})).ok, true);

for (const invalid of [
    "{oops", "null", "[]",
    JSON.stringify({version: 2, zones: []}),
    JSON.stringify({version: 1, zones: ["UTC", "UTC"]}),
    JSON.stringify({version: 1, zones: ["../malicious"]}),
    JSON.stringify({version: 1, zones: eight.concat(["America/Chicago"])}),
    JSON.stringify({version: 1, zones: "UTC"}),
]) {
  assert.equal(policy.parse(invalid).ok, false, invalid);
}
assert.equal(policy.contains(["UTC"], "../bad"), false);
console.log("WORLD_FAVORITES_POLICY_PASS");
