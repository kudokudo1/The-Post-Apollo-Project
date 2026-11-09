#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalHorizontalChassisPolicy.js"), "utf8");
const c = vm.createContext({});
vm.runInContext(source, c);

const widths = [744, 984, 1224, 1464];
for (let i = 0; i < widths.length; i++) {
    assert.equal(c.panelWidth(i, 2560, 6, 14), widths[i]);
    assert.equal(c.levelIndex(i), i);
}
assert.equal(c.levelIndex(-100), 0);
assert.equal(c.levelIndex(99), 3);
assert.equal(c.levelIndex("bad"), 0);
assert.equal(c.panelWidth(-8, 2560, 6, 14), 744);
assert.equal(c.panelWidth(100, 2560, 6, 14), 1464);
assert.equal(c.step(0, 1, 2560, 6, 14), 1);
assert.equal(c.step(1, 1, 2560, 6, 14), 2);
assert.equal(c.step(2, 1, 2560, 6, 14), 3);
assert.equal(c.step(3, 1, 2560, 6, 14), 3);
assert.equal(c.step(3, -1, 2560, 6, 14), 2);
assert.equal(c.step(0, -1, 2560, 6, 14), 0);
assert.equal(c.canStep(0, -1, 2560, 6, 14), false);
assert.equal(c.canStep(0, 1, 2560, 6, 14), true);
assert.equal(c.canStep(3, 1, 2560, 6, 14), false);

// Only width changes; visible left edge has 6px left margin and 14px
// reserved right glow gutter, so the mapped surface stays on this output.
for (const screenWidth of [760, 800, 1024, 1360, 1920, 2560]) {
    const budget = screenWidth - 6 - 14;
    for (let i = 0; i < widths.length; i++) {
        const width = c.panelWidth(i, screenWidth, 6, 14);
        assert(width <= budget, "Overflows screen " + screenWidth);
        assert(width >= 1, "Invalid surface width");
        if (i)
            assert(width >= c.panelWidth(i - 1, screenWidth, 6, 14));
    }
}
assert.equal(c.panelWidth(3, 1360, 6, 14), 1340);
assert.equal(c.panelWidth(3, 1024, 6, 14), 1004);
assert.equal(c.panelWidth(0, 800, 6, 14), 744);
// Beyond the display cap, the next arrow is disabled rather than a dead click.
assert.equal(c.canStep(1, 1, 1024, 6, 14), true);
assert.equal(c.canStep(2, 1, 1024, 6, 14), false);
assert.equal(c.step(3, -1, 800, 6, 14), 0);
assert.equal(c.canStep(0, 1, 760, 6, 14), false);
assert.equal(c.panelWidth(0, NaN, 6, 14), 744);
assert.equal(c.panelWidth(0, 320, 6, 14), 300);
console.log("HOSPITAL HORIZONTAL CHASSIS // PASS // four width levels, output clamp and no-op arrows");
