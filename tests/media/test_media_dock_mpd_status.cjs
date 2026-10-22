#!/usr/bin/env node
"use strict";
// Test the actual QML JS parser, not a reimplementation of it.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const filename = path.resolve(__dirname, "../../services/media/MediaDockMpdStatus.js");
const source = fs.readFileSync(filename, "utf8").replace(/^\.pragma library\s*/m, "");
const parser = vm.createContext({});
vm.runInContext(source, parser, {filename});

function result(raw) {
    const decoded = parser.parseStatus(raw);
    return decoded === null ? null : JSON.parse(JSON.stringify(decoded));
}

test("active MPD state and title are decoded from full mpc output", () => {
    const status = "Artist - Track\n[playing] #1/25   0:21/3:45 (9%)\nvolume: 75%   repeat: off   random: off";
    assert.deepEqual(result(status), {state: "playing", title: "Artist - Track"});
    assert.deepEqual(result("Artist - Track\n[paused] #1/25\nvolume: 50%"), {
        state: "paused", title: "Artist - Track"
    });
    assert.deepEqual(result("[stopped] #1/25\nvolume: n/a"), {
        state: "stopped", title: ""
    });
});

test("legitimate empty MPD queue reports stopped, not offline", () => {
    assert.deepEqual(result("volume: 70%   repeat: off   random: off"), {
        state: "stopped", title: ""
    });
});

test("failed reads are not playback observations and cannot advance freshness", () => {
    for (const sample of ["", "  ", "mpc: Connection refused", "MPD error: timeout",
                          "failed to read stream", "random: off", null, undefined]) {
        assert.equal(result(sample), null, String(sample));
    }
});

test("stale or unrelated input cannot fabricate playing state", () => {
    assert.equal(result("Artist - Track\n[buffering] #1/1"), null);
    assert.equal(result("something [playing] wrapped in text"), null);
    assert.equal(result("state=playing"), null);
});
