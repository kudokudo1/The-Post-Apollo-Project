#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(path.join(root, "components/WeatherMoonGeometry.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const moon = {};
vm.runInNewContext(source, moon);

const pairs = [
    ["waxing-crescent", "waning-crescent"],
    ["first-quarter", "last-quarter"],
    ["waxing-gibbous", "waning-gibbous"]
];
function area(p) {
    let sum = 0;
    for (let i = 0; i < p.length; i++) {
        const [x, y] = p[i];
        const [nx, ny] = p[(i + 1) % p.length];
        sum += x * ny - nx * y;
    }
    return Math.abs(sum) / 2;
}
let previous = 0;
for (const [waxing, waning] of pairs) {
    const right = moon.contour(waxing), left = moon.contour(waning);
    assert.ok(right.length > 50);
    assert.equal(right.length, left.length);
    for (let i = 0; i < right.length; i++) {
        assert.ok(Math.abs(right[i][0] + left[i][0] - 40) < 0.00001);
        assert.ok(Math.abs(right[i][1] - left[i][1]) < 0.00001);
    }
    const rightArea = area(right), leftArea = area(left);
    assert.ok(Math.abs(rightArea - leftArea) < 0.00001);
    assert.ok(rightArea > previous, waxing + " has no distinct lit area");
    previous = rightArea;
    assert.ok(/^M /.test(moon.litPath(waxing)) && moon.litPath(waning).endsWith(" Z"));
}
assert.equal(moon.contour("new").length, 0);
assert.equal(moon.contour("full").length, 0);
assert.equal(moon.litPath("unknown"), "");
const qml = fs.readFileSync(path.join(root, "components/WeatherCelestialGlyph.qml"), "utf8");
assert.match(qml, /import "WeatherMoonGeometry\.js" as MoonGeometry/);
assert.match(qml, /PathSvg\s*\{\s*path:\s*MoonGeometry\.litPath\(glyph\.moonPhase\)/);
assert.doesNotMatch(qml, /direction:\s*glyph\.waxing/);
console.log("Moon geometry 8-phase symmetric contour contracts: PASS");
