#!/usr/bin/env node
"use strict";
// TASKS portrait geometry: three steps, one bounded mapped surface, no store changes.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const policy = fs.readFileSync(path.join(root, "widgets/TasksChassisPolicy.js"), "utf8");
const code = policy.replace(/^\s*\.pragma library\s*$/m, "");
const api = {};
vm.runInNewContext(code, api, { filename: "TasksChassisPolicy.js" });
assert.equal(api.normalize("invalid"), "compact");
assert.equal(api.step("compact", -1), "compact");
assert.equal(api.step("compact", 1), "expanded");
assert.equal(api.step("expanded", 1), "large");
assert.equal(api.step("large", 1), "large");
assert.equal(api.step("large", -1), "expanded");
assert.equal(api.step("invalid", 1), "expanded");

function frame(level, width = 2560, height = 1440) {
    return api.frame(level, width, height, 12, 9, 12);
}
assert.deepEqual(JSON.parse(JSON.stringify(frame("compact"))), { width: 432, height: 790 });
assert.deepEqual(JSON.parse(JSON.stringify(frame("expanded"))), { width: 560, height: 1020 });
assert.deepEqual(JSON.parse(JSON.stringify(frame("large"))), { width: 760, height: 1345 });

for (const width of [480, 768, 1360, 1920, 2560]) {
    for (const height of [480, 600, 768, 900, 1080, 1440]) {
        let prior = null;
        for (const level of ["compact", "expanded", "large"]) {
            const size = frame(level, width, height);
            assert.ok(size.width > 0 && size.height > 0);
            assert.ok(size.width + 24 <= width, level + " width overflow");
            assert.ok(size.height + 21 <= height, level + " height overflow");
            assert.ok(size.width / size.height <= 0.58, level + " no portrait ratio");
            if (prior) {
                assert.ok(size.width >= prior.width && size.height >= prior.height,
                          level + " must not shrink");
            }
            prior = size;
            const totalWidth = size.width + 24;
            const totalHeight = size.height + 21;
            for (const dockCenter of [-100, 40, width / 2, width + 100]) {
                const left = api.leftMargin(dockCenter, width, totalWidth);
                assert.ok(left >= 0 && left + totalWidth <= width);
            }
            for (const top of [-100, 60, height + 100]) {
                const offset = api.topMargin(top, height, totalHeight, 12);
                assert.ok(offset >= 0 && offset + totalHeight <= height);
            }
        }
    }
}
console.log("TASKS portrait chassis policy: PASS");
