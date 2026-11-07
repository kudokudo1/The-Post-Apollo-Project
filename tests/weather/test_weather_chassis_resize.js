"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");
const ctx = vm.createContext({});
vm.runInContext(read("widgets/weather/StationChassisSizePolicy.js")
    .replace(".pragma library", ""), ctx);
const station = read("widgets/weather/WeatherStationW.qml");

test("Weather chassis has exactly four manually stepped levels", () => {
    const names = ["compact", "medium", "large", "fullscreen"];
    assert.deepEqual(Array.from(ctx.levels), names);
    for (let i = 0; i < names.length; i++) {
        assert.equal(ctx.step(names[i], 1), names[Math.min(i + 1, 3)]);
        assert.equal(ctx.step(names[i], -1), names[Math.max(i - 1, 0)]);
    }
    assert.equal(ctx.step("unexpected", -1), "compact");
});
test("original 1000x700 compact frame stays exact", () => {
    const f = (mode, right) => ({...ctx.frame(mode, 2560, 1440, 9, 8, right)});
    assert.deepEqual(f("compact", 20), {width: 1000, height: 700});
    assert.deepEqual(f("medium", 20), {width: 1200, height: 850});
    assert.deepEqual(f("large", 20), {width: 1500, height: 1030});
    assert.deepEqual(f("fullscreen", 0), {width: 2560, height: 1423});
});
test("smaller outputs clamp all steps safely", () => {
    for (const level of Array.from(ctx.levels)) {
        const r = ctx.frame(level, 1360, 768, 9, 8,
                            level === "fullscreen" ? 0 : 20);
        assert.ok(r.width >= 1 && r.width <= 1360);
        assert.ok(r.height >= 1 && r.height <= 751);
    }
    assert.deepEqual({...ctx.frame("compact", 500, 300, 9, 8, 20)},
                     {width: 480, height: 283});
});
test("header arrows resize the one existing panel and preserve Kitty cutout geometry", () => {
    const required = [
        'property string chassisLevel: "compact"',
        'chassisLevel = ChassisSize.step(chassisLevel, 1)',
        'chassisLevel = ChassisSize.step(chassisLevel, -1)',
        'label: "↓"', 'label: "↑"',
        'onLeftClicked: weatherStation.collapseChassis()',
        'onLeftClicked: weatherStation.expandChassis()',
        'implicitWidth: menuOpen ? frameWidth : 0',
        'implicitHeight: menuOpen ? frameHeight : 0',
        'width: weatherStation.menuOpen ? weatherStation.frameWidth : 0',
        'height: weatherStation.menuOpen ? weatherStation.frameHeight : 0',
        'width: weatherStation.frameWidth',
        'height: weatherStation.frameHeight',
        'stationRightMargin: weatherStation.chassisRightMargin',
        'stationWidth: stationBackground.width',
        'stationHeight: stationBackground.height',
        'id: terminalChassisCutout',
        'id: subjectNavigator',
        'id: terminalView'
    ];
    for (const text of required) assert.ok(station.includes(text), text);
});
