"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const code = fs.readFileSync(path.join(root,
    "services/input/KeyboardLockPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const p = {};
vm.runInNewContext(code, p);
assert.deepEqual(JSON.parse(JSON.stringify(p.initialDocument())),
    {version: 1, num: "system", caps: "system"});
for (const mode of ["system", "on", "off"])
    assert.equal(p.validMode(mode), true);
for (const mode of ["remember", "enabled", true, "", 1])
    assert.equal(p.validMode(mode), false);
let doc = p.initialDocument();
doc = p.withMode(doc, "num", "on").document;
doc = p.withMode(doc, "caps", "off").document;
assert.equal(doc.num, "on");
assert.equal(doc.caps, "off");
assert.equal(p.parse(JSON.stringify(doc)).ok, true);
for (const raw of ["{}", "bad", "[]", '{"version":2,"num":"on","caps":"off"}',
    '{"version":1,"num":"remember","caps":"on"}']) {
    assert.equal(p.parse(raw).ok, false);
}
for (const [lock, mode] of [["unknown", "on"], ["caps", "toggle"]])
    assert.equal(p.withMode(doc, lock, mode).ok, false);
console.log("KEYBOARD_LOCK_POLICY_PASS");
