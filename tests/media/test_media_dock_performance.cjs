#!/usr/bin/env node
"use strict";
// Execute the actual receiveCavaFrame function with isolated QML-like data.
// This proves identical/silent frames do not publish new levels arrays.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(path.join(root, "modules/Mediaplayer.qml"), "utf8");
const config = fs.readFileSync(path.join(root, "modules/mediaplayer-cava.conf"), "utf8");

function harness() {
    const match = source.match(/    function receiveCavaFrame\(frame\) \{([\s\S]*?)\n    \}\n\n    Process \{/);
    assert.ok(match, "CAVA frame handler should remain isolated and testable");
    const context = vm.createContext({barCount: 16, levels: Array(16).fill(0)});
    const receive = vm.runInContext("(function(frame) {" + match[1] + "\n})", context);
    return {context, receive};
}

test("sample static music icon, not the animated VU spectrum", () => {
    assert.match(source, /contentGlowSource:\s*musicMark/);
    assert.doesNotMatch(source, /contentGlowSource:\s*mediaArtwork/);
    assert.match(source, /id:\s*musicMark/);
    assert.match(source, /id:\s*mediaArtwork/);
    assert.match(source, /id:\s*spectrum/);
});

test("magenta idle chassis and treble clef do not recolor or resample CAVA", () => {
    assert.match(source, /normalDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /normalContentGlowColor:\s*Colors\.magenta/);
    assert.match(source, /hoverContentGlowColor:\s*Colors\.magenta/);
    assert.match(source, /contentGlowSource:\s*musicMark/);

    const musicMark = source.match(/GohuText \{\s*id:\s*musicMark([\s\S]*?)\n\s*\}/);
    assert.ok(musicMark, "music mark remains a single text item");
    assert.match(musicMark[1], /textFormat:\s*Text\.StyledText/);
    // The ornaments retain the dock's state-aware foreground; only the
    // treble clef is a fixed magenta foreground.
    assert.match(musicMark[1],
        /mediaDock\.foregroundColor[\s\S]*‧₊˚ [\s\S]*Colors\.magenta[\s\S]*𝄞[\s\S]*mediaDock\.foregroundColor[\s\S]*˖/);

    // The animated bars keep their original accent and are never sampled.
    assert.match(source, /readonly property color accentColor:\s*mpdPlaying \? Colors\.orange : Colors\.cyan/);
    assert.match(source, /color:\s*mediaDock\.accentColor/);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:spectrum|mediaArtwork)/);
});

test("CAVA preserves 16-bar output at a bounded 15 FPS", () => {
    assert.match(config, /^bars\s*=\s*16$/m);
    assert.match(config, /^framerate\s*=\s*15$/m);
    assert.match(config, /^method\s*=\s*raw$/m);
    assert.match(config, /^data_format\s*=\s*ascii$/m);
    assert.match(source, /command:\s*\["cava", "-p", Quickshell\.shellPath\("modules\/mediaplayer-cava\.conf"\)\]/);
    assert.equal((source.match(/id:\s*cavaProcess\b/g) || []).length, 1);
});

test("silent frames and repeated levels cannot trigger rebinds or animations", () => {
    const {context, receive} = harness();
    const initial = context.levels;
    receive(Array(16).fill("0").join(";") + ";");
    assert.equal(context.levels, initial, "silent stream must preserve array identity");
    const song = Array(16).fill("4").join(";") + ";";
    receive(song);
    const published = context.levels;
    assert.notEqual(published, initial);
    assert.equal(published.length, 16);
    assert.ok(Array.from(published).every(n => n === 4));
    receive(song);
    assert.equal(context.levels, published, "repeat must not publish new levels");
    receive(Array(16).fill("0").join(";"));
    assert.notEqual(context.levels, published, "silence transition must still update");
    const zero = context.levels;
    receive(Array(16).fill("0").join(";"));
    assert.equal(context.levels, zero, "subsequent silence must stay quiet");
});

test("bad frames cannot reset or replace the current visualizer reading", () => {
    const {context, receive} = harness();
    receive(Array(16).fill("2").join(";"));
    const valid = context.levels;
    for (const invalid of ["", "1;2;3", Array(16).fill("NaN").join(";"),
                           Array(16).fill("bad").join(";")]) {
        receive(invalid);
        assert.equal(context.levels, valid);
    }
});
