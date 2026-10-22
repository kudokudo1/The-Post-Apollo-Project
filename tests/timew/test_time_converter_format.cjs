#!/usr/bin/env node
"use strict";

// Isolated pure presentation contract for CALC input/output format settings.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const filename = path.join(__dirname, "../../services/time/TimeConverterFormat.js");
const body = fs.readFileSync(filename, "utf8").replace(/^\.pragma library\s*/m, "");
const f = vm.createContext({});
vm.runInContext(body, f, {filename: "TimeConverterFormat.js"});

for (const [entered, is24, canonical] of [
    ["13:19", true, "13:19"],
    ["1:19", true, "01:19"],
    ["00:00", true, "00:00"],
    ["23:59", true, "23:59"],
    ["01:19 PM", false, "13:19"],
    ["01:19//PM", false, "13:19"],
    ["1:19 pm", false, "13:19"],
    ["12:00 AM", false, "00:00"],
    ["12:00 PM", false, "12:00"],
    ["12:59//AM", false, "00:59"],
    ["11:59 PM", false, "23:59"],
]) {
    const result = f.parseInput(entered, is24);
    assert.equal(result.valid, true, entered);
    assert.equal(result.canonical, canonical, entered);
}
for (const [entered, is24] of [
    ["24:00", true], ["12:60", true], ["99:11", true],
    ["01:19 PM", true], ["01:19", false], ["00:01 AM", false],
    ["13:01 PM", false], ["12:99 PM", false],
    ["13:19//PM", false], ["1:19//", false], ["", false],
    [null, false], ["12:00", "true"]
]) {
    const parsed = f.parseInput(entered, is24);
    assert.equal(parsed.valid, false, String(entered));
}
for (let hour = 0; hour < 24; hour++) {
    for (const minutes of ["00","15","30","59"]) {
        const canonical = String(hour).padStart(2, "0") + ":" + minutes;
        const shown12 = f.convertInput(canonical, true, false);
        assert.equal(shown12.valid, true);
        assert.equal(f.parseInput(shown12.text, false).canonical, canonical);
        const shown24 = f.convertInput(shown12.text, false, true);
        assert.equal(shown24.text, canonical);
    }
}
const wrong = f.convertInput("25:99", true, false);
assert.equal(wrong.valid, false);
assert.equal(wrong.text, "25:99"); // no silent data loss

const examples = [
    ["2026-10-22 13:19:00 EDT (-0400)",
     "2026-10-22 13:19:00//PM EDT (-0400)",
     "2026-10-22 01:19:00//PM EDT (-0400)"],
    ["2026-10-22 00:00:00 UTC (+0000)",
     "2026-10-22 00:00:00//AM UTC (+0000)",
     "2026-10-22 12:00:00//AM UTC (+0000)"],
    ["2026-10-22 12:00:00 UTC (+0000)",
     "2026-10-22 12:00:00//PM UTC (+0000)",
     "2026-10-22 12:00:00//PM UTC (+0000)"],
    ["2026-11-01 01:30:00 EDT (-0400)",
     "2026-11-01 01:30:00//AM EDT (-0400)",
     "2026-11-01 01:30:00//AM EDT (-0400)"],
    ["2026-11-01 01:30:00 EST (-0500)",
     "2026-11-01 01:30:00//AM EST (-0500)",
     "2026-11-01 01:30:00//AM EST (-0500)"],
];
for (const [canonical, hour24, hour12] of examples) {
    assert.equal(f.formatResult(canonical, true), hour24);
    assert.equal(f.formatResult(canonical, false), hour12);
    assert.equal(f.formatResult(canonical, false), hour12);
    assert.equal(canonical.includes("//"), false, "do not mutate raw");
}
assert.equal(f.formatResult("weird output", false), "weird output");
assert.equal(f.formatResult(null, false), "");
assert.equal(f.formatResult("2026-10-22 99:99:99 XYZ (+0000)", false),
             "2026-10-22 99:99:99 XYZ (+0000)");
console.log("TIMEW CALC INDEPENDENT HOUR FORMAT: PASS");
