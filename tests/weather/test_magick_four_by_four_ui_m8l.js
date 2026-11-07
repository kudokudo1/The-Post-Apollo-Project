"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");
const context = vm.createContext({});
vm.runInContext(read("widgets/weather/StationMagickTransitMatrixPolicy.js")
    .replace(/^\.pragma library\s*/, ""), context);
const Matrix = context;

function natal() {
    return {
        format: "post-apollo.weather.magick-natal-chart.m8a.v1",
        epoch_utc: "2000-03-21T15:20:00Z",
        origin: "topocentric", frame: "true-ecliptic-of-date",
        position_model: "apparent", zodiac: "tropical",
        house_system: "whole-sign",
        observer: {latitude_deg: 38.9, longitude_deg: -76.8, elevation_m: 0},
        provenance: {engine: "skyfield", ephemeris_sha256: "a".repeat(64)},
        positions: Matrix.TARGETS.map((id, i) => ({
            id, naif_id: Matrix.NAIF[id],
            longitude_deg: i === 0 ? 10 : (i * 33 + 14) % 360
        }))
    };
}
const natals = ["sun", "moon", "mercury", "venus"];
const moving = ["moon", "mercury", "venus", "mars_barycenter"];
const parsed = o => JSON.parse(JSON.stringify(o));

test("4x4 request accepted only inside original Python-equivalent budget", () => {
    const req = Matrix.request(natal(), "2026-11-07", 1,
        natals, moving, [0, 60, 90], 60);
    assert.ok(req);
    assert.equal(req.natal_bodies.length * req.transit_bodies.length, 16);
    assert.equal(req.end_utc, "2026-11-08T00:00:00Z");
    assert.deepEqual(parsed(req.aspects_deg), [0, 60, 90]);
    assert.ok(Matrix.request(natal(), "2026-11-07", 1,
        natals, moving, [0, 60], 30));
    assert.equal(Matrix.request(natal(), "2026-11-07", 7,
        natals, moving, [0, 60], 60), null);
    assert.ok(Matrix.request(natal(), "2026-11-07", 7,
        natals.slice(0, 3), moving, [60], 60));
    assert.ok(Matrix.request(natal(), "2026-11-07", 31,
        ["sun"], ["moon"], [60], 60));
    assert.equal(Matrix.request(natal(), "2026-11-07", 1,
        natals.concat(["jupiter_barycenter"]), moving, [60], 60), null);
});

test("budget counts pair and 15-minute station grid points exactly", () => {
    const one = Matrix.budget(1, 4, 4, 60);
    assert.equal(one.valid, true);
    assert.equal(one.pairs, 16);
    assert.equal(one.pairSamples, 400);
    assert.equal(one.stationSamples, 388);
    assert.equal(one.pairLimit, 2200);
    assert.equal(one.stationLimit, 3000);
    const seven = Matrix.budget(7, 4, 4, 60);
    assert.equal(seven.valid, false);
    assert.equal(seven.reason, "PAIR SAMPLE LIMIT");
    assert.equal(seven.pairSamples, 2704);
    assert.equal(seven.stationSamples, 2692);
    const five = Matrix.budget(7, 3, 4, 60);
    assert.equal(five.pairSamples, 2028);
    assert.equal(five.stationSamples, 2692);
    assert.equal(five.valid, true);
    const long = Matrix.budget(14, 1, 4, 60);
    assert.equal(long.valid, false);
    assert.equal(long.reason, "STATION SAMPLE LIMIT");
    assert.equal(Matrix.budget(14, 1, 4, 30).valid, false);
    assert.equal(Matrix.budget(1, 5, 4, 60).valid, false);
    assert.equal(Matrix.budget(1, 4, 0, 60).valid, false);
    assert.equal(Matrix.budget(1, 4, 4, 15).valid, false);
});

test("FIT is explicit, selects largest supported not-later span", () => {
    assert.equal(Matrix.fittingSpan(7, 4, 4, 60), 1);
    assert.equal(Matrix.fittingSpan(14, 4, 4, 60), 1);
    assert.equal(Matrix.fittingSpan(31, 4, 4, 60), 1);
    assert.equal(Matrix.fittingSpan(7, 3, 4, 60), 7);
    assert.equal(Matrix.fittingSpan(14, 3, 4, 60), 7);
    assert.equal(Matrix.fittingSpan(31, 1, 1, 60), 31);
    assert.equal(Matrix.fittingSpan(31, 4, 4, 30), 1);
    assert.equal(Matrix.fittingSpan(7, 5, 4, 60), 0);
    assert.equal(Matrix.fittingSpan(20, 1, 1, 60), 0);
});

test("Qt navigation uses clear budget and old results are not modified", () => {
    const ui = read("widgets/weather/StationMagickTransitMatrixPane.qml");
    const py = read("scripts/weather/celestial_transit_matrix.py");
    const svc = read("services/weather/CelestialTransitMatrixService.qml");
    assert.match(ui, /property var workload:Matrix\.budget\(/);
    assert.match(ui, /property int suggestedSpan:Matrix\.fittingSpan\(/);
    assert.match(ui, /current\.length<4/);
    assert.match(ui, /natalBodies\.length<4/);
    assert.match(ui, /transitBodies\.length<4/);
    assert.match(ui, /id:budgetRow/);
    assert.match(ui, /pairSamples/);
    assert.match(ui, /stationSamples/);
    assert.match(ui, /label:atlas\.workload\.valid\?"IN BUDGET"/);
    assert.match(ui, /onClicked:atlas\.spanDays=atlas\.suggestedSpan/);
    assert.match(ui, /anchors\.top:budgetRow\.bottom/);
    assert.match(ui, /model:atlas\.natalBodies/);
    assert.match(ui, /model:atlas\.transitBodies/);
    assert.match(ui, /Matrix\.nearestMinute|eventRequested\(event\.utc/);
    assert.match(py, /MAX_NATAL = 4/);
    assert.match(py, /MAX_MOVING = 4/);
    assert.match(py, /MAX_PAIR_SAMPLES = 2200/);
    assert.match(py, /MAX_TOTAL_STATION_GRID = 3000/);
    assert.match(py, /MAX_EVENTS = 150/);
    assert.match(py, /MAX_OUTPUT_BYTES = 120000/);
    assert.match(py, /find_stations\(/);
    assert.match(svc, /stdinEnabled:true/);
    assert.match(svc, /onActiveChanged:if\(!active\)clearState\(\)/);
    for(const forbidden of ["XMLHttpRequest", "FileView {", "localStorage",
        "Qt.openUrlExternally", "writeFile(", "console.log("]) {
        assert.ok(!ui.includes(forbidden));
    }
});
