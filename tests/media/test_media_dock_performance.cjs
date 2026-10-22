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
const trebleSvg = fs.readFileSync(path.join(root, "assets/media/treble-clef.svg"), "utf8");
const treblePng = fs.readFileSync(path.join(root, "assets/media/treble-clef.png"));

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

    const musicMark = source.match(/Row \{\s*id:\s*musicMark([\s\S]*?)\n\s*\}\n\n\s*Item \{\s*id:\s*spectrum/);
    assert.ok(musicMark, "static music-mark cluster is still the one glow source");
    const mark = musicMark[1];
    assert.match(mark, /spacing:\s*0/);
    assert.equal((mark.match(/GohuText \{/g) || []).length, 2,
        "original decorative text remains, while the treble clef is vector art");
    assert.equal((mark.match(/Image \{/g) || []).length, 1);
    assert.match(mark, /id:\s*trebleClef\s*width:\s*15\s*height:\s*34/);
    assert.match(mark, /source:\s*Qt\.resolvedUrl\("\.\.\/assets\/media\/treble-clef\.png"\)/);
    assert.match(mark, /sourceSize:\s*Qt\.size\(45,\s*102\)/);
    assert.match(mark, /onStatusChanged:[\s\S]*?Image\.Error/);
    assert.match(mark, /textFormat:\s*Text\.PlainText\s*text:\s*"‧₊˚ "/);
    assert.match(mark, /textFormat:\s*Text\.PlainText\s*text:\s*"˖"/);
    assert.equal((mark.match(/anchors\.verticalCenter:\s*trebleClef\.verticalCenter/g) || []).length, 2);
    assert.equal((mark.match(/color:\s*mediaDock\.foregroundColor/g) || []).length, 2);
    assert.doesNotMatch(mark, /Text\.StyledText|<font |text:\s*"𝄞"/);

    // The vector exists in the repository, visibly contains geometry rather
    // than a font-dependent <text> node, and uses the palette's magenta.
    assert.match(trebleSvg, /<svg[^>]*viewBox="0 0 611 1732"/);
    assert.match(trebleSvg, /fill="#C74EC7"/);
    assert.match(trebleSvg, /<path[^>]+d="M314 801/);
    assert.doesNotMatch(trebleSvg, /<text\b/);
    // PNG is the runtime source, so no user-installed music font or Qt SVG
    // image plug-in is required. Keep the vector as the editable original.
    assert.equal(treblePng.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
    assert.equal(treblePng.readUInt32BE(16), 45);
    assert.equal(treblePng.readUInt32BE(20), 102);
    assert.equal(treblePng[25], 6, "runtime icon must retain an alpha channel");


    // The animated bars keep their original accent and are never sampled.
    assert.match(source, /readonly property color accentColor:\s*mpdPlaying \? Colors\.orange : Colors\.cyan/);
    assert.match(source, /color:\s*mediaDock\.accentColor/);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:spectrum|mediaArtwork)/);
});

test("CAVA neon tracks the animated bar using geometry only", () => {
    const match = source.match(/Item \{\s*width:\s*5\s*height:\s*spectrum\.height([\s\S]*?)\n\s*\}\n\s*\}\n\s*\}\n\s*\}\n\s*\}/);
    assert.ok(match, "expected a bounded bar item inside the 16-bar Repeater");
    const bar = match[1];
    assert.match(bar, /id:\s*cavaBar/);
    assert.match(bar, /height:\s*cavaBar\.height\s*\+\s*6/);
    assert.match(bar, /height:\s*cavaBar\.height\s*\+\s*2/);
    assert.match(bar, /width:\s*parent\.width\s*\+\s*8/);
    assert.match(bar, /width:\s*parent\.width\s*\+\s*4/);
    assert.equal((bar.match(/color:\s*mediaDock\.accentColor/g) || []).length, 3,
        "both glow layers and the bar must follow the same cyan/orange accent");
    assert.equal((bar.match(/Behavior on height/g) || []).length, 1,
        "only the actual bar animates; halos follow bindings");
    assert.doesNotMatch(bar, /DropShadow|RectangularShadow|ShaderEffect|layer\.enabled/);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:spectrum|mediaArtwork|cavaBar)/);
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
