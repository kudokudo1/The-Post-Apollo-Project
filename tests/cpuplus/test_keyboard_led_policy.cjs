"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const filename = path.join(__dirname, "../../services/input/KeyboardLedPolicy.js");
const source = fs.readFileSync(filename, "utf8").replace(/^\.pragma library\s*/m, "");
const p = {};
vm.runInNewContext(source, p);
function plain(v) { return JSON.parse(JSON.stringify(v)); }
let d = p.initialDocument();
assert.deepEqual(plain(d), {version: 1, enabled: false,
    num: {value: "unknown", observedAtMs: 0},
    caps: {value: "unknown", observedAtMs: 0}});
assert.equal(p.withObserved(d, "num", "on", 100).ok, false);
d = p.withEnabled(d, true).document;
let sample = p.withObserved(d, "num", "on", 100);
assert.equal(sample.ok, true);
assert.equal(sample.changed, true);
d = sample.document;
assert.equal(d.caps.value, "unknown");
sample = p.withObserved(d, "num", "on", 200);
assert.equal(sample.ok, true);
assert.equal(sample.changed, false);
assert.equal(sample.document.num.observedAtMs, 100);
assert.equal(p.withObserved(d, "num", "off", 99).ok, false);
d = p.withObserved(d, "caps", "off", 300).document;
assert.equal(p.parse(JSON.stringify(d)).ok, true);
for (const raw of ["{}", "bad", "[]",
  '{"version":1,"enabled":true,"num":{"value":"on","observedAtMs":0},"caps":{"value":"unknown","observedAtMs":0}}',
  '{"version":1,"enabled":"yes","num":{"value":"unknown","observedAtMs":0},"caps":{"value":"unknown","observedAtMs":0}}']) {
    assert.equal(p.parse(raw).ok, false);
}
assert.equal(p.withObserved(d, "num", "unknown", 400).ok, false);
assert.equal(p.withObserved(d, "num", "on", NaN).ok, false);
console.log("LED_POLICY_PASS // LAST_OBSERVED_NEVER_LIVE");
