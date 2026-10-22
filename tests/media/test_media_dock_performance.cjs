#!/usr/bin/env node
"use strict";
// Execute the actual receiveCavaFrame function with isolated QML-like data.
// This proves identical/silent frames do not publish new levels arrays.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const crypto = require("node:crypto");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(path.join(root, "modules/Mediaplayer.qml"), "utf8");
const config = fs.readFileSync(path.join(root, "modules/mediaplayer-cava.conf"), "utf8");
const trebleSvg = fs.readFileSync(path.join(root, "assets/media/treble-clef.svg"), "utf8");
const treblePng = fs.readFileSync(path.join(root, "assets/media/treble-clef.png"));
const trebleCyan = fs.readFileSync(path.join(root, "assets/media/treble-clef-cyan.png"));
const trebleOrange = fs.readFileSync(path.join(root, "assets/media/treble-clef-orange.png"));

function harness() {
    const match = source.match(/    function receiveCavaFrame\(frame\) \{([\s\S]*?)\n    \}\n\n    Process \{/);
    assert.ok(match, "CAVA frame handler should remain isolated and testable");
    // Optional UI-lag diagnostics are disabled by default; model that QML
    // property explicitly so normal CAVA frame tests exercise the production
    // fast path even after the probe was introduced.
    const context = vm.createContext({
        barCount: 16,
        levels: Array(16).fill(0),
        bgLagProbeEnabled: false
    });
    const receive = vm.runInContext("(function(frame) {" + match[1] + "\n})", context);
    return {context, receive};
}

test("sample only separate static glyphs, never the animated VU spectrum", () => {
    assert.match(source, /contentGlowEnabled:\s*false/);
    assert.match(source, /contentGlowSource:\s*null/);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:musicMark|mediaArtwork|spectrum|cavaBar)/);
    assert.match(source, /id:\s*leadingStars/);
    assert.match(source, /id:\s*trebleClef/);
    assert.match(source, /id:\s*trailingStar/);
    assert.match(source, /id:\s*mediaArtwork/);
    assert.match(source, /id:\s*spectrum/);
});

test("magenta dock halo and CAVA-colored static music mark stay independent", () => {
    assert.match(source, /normalDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /normalContentGlowColor:\s*accentColor/);
    assert.match(source, /hoverContentGlowColor:\s*accentColor/);
    assert.match(source, /contentGlowEnabled:\s*false/);
    assert.match(source, /contentGlowSource:\s*null/);

    const musicMark = source.match(/Row \{\s*id:\s*musicMark([\s\S]*?)\n\s*\}\n\n\s*Item \{\s*id:\s*spectrum/);
    assert.ok(musicMark, "static music-mark cluster is still the one glow source");
    const mark = musicMark[1];
    assert.match(mark, /spacing:\s*0/);
    assert.match(mark, /id:\s*leadingStars/);
    assert.match(mark, /id:\s*trailingStar/);
    assert.equal((mark.match(/GohuText \{/g) || []).length, 2,
        "original decorative text remains, while the treble clef is vector art");
    assert.equal((mark.match(/Image \{/g) || []).length, 1);
    assert.match(mark, /id:\s*trebleClef\s*width:\s*15\s*height:\s*34/);
    assert.match(mark, /source:\s*mediaDock\.mpdPlaying\s*\?\s*Qt\.resolvedUrl\("\.\.\/assets\/media\/treble-clef-orange\.png"\)\s*:\s*Qt\.resolvedUrl\("\.\.\/assets\/media\/treble-clef-cyan\.png"\)/);
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

    // Pre-rendered variants match the *exact* palette colors, with the
    // original alpha silhouette. Hashes pin the visually verified outputs,
    // avoiding per-frame tint shaders or font-dependent glyph fallback.
    for (const [name, png, sha256] of [
        ["cyan", trebleCyan, "3e7a63956306b12ea714390968c70c03671c6099b2b45b98fc9ad91197b3f014"],
        ["orange", trebleOrange, "72aab7636233a5a6574295e781f00b4eaf103b3d15bb9bb9a14e643a59a00494"]
    ]) {
        assert.equal(png.subarray(0, 8).toString("hex"), "89504e470d0a1a0a", name + " PNG header");
        assert.equal(png.readUInt32BE(16), 45, name + " width");
        assert.equal(png.readUInt32BE(20), 102, name + " height");
        assert.equal(png[25], 6, name + " needs RGBA transparency");
        assert.equal(crypto.createHash("sha256").update(png).digest("hex"), sha256, name + " palette art");
    }



    // The animated bars keep their original accent and are never sampled.
    assert.match(source, /readonly property color accentColor:\s*mpdPlaying \? Colors\.orange : Colors\.cyan/);
    assert.match(source, /color:\s*mediaDock\.accentColor/);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:spectrum|mediaArtwork)/);
});

test("magenta full-width wash, three independent static art glows, per-bar CAVA halos", () => {
    // The full-width rear/front chassis glow is the Media-specific magenta variant.
    for (const mode of ["normal", "hover", "pressed"]) {
        assert.match(source, new RegExp(mode + "DockGlowColor:\\s*Colors\\.magenta"));
        assert.match(source, new RegExp(mode + "ContentGlowColor:\\s*accentColor"));
    }

    // Each static glyph has one source-attached accent halo. No cluster-wide
    // rectangular cyan strip and no sampled animation shadow.
    const glows = [
        ["leadingStarsGlow", "leadingStars"],
        ["trebleClefGlow", "trebleClef"],
        ["trailingStarGlow", "trailingStar"]
    ];
    assert.equal((source.match(/SafeDropShadow \{/g) || []).length, 3,
        "only the three static music glyphs should be sampled");
    for (const [glowId, sourceId] of glows) {
        const match = source.match(new RegExp(
            "SafeDropShadow \\{\\s*id:\\s*" + glowId + "([\\s\\S]*?)\\n    \\}"
        ));
        assert.ok(match, glowId + " must have its own effect");
        const body = match[1];
        assert.match(body, new RegExp("safeSource:\\s*" + sourceId));
        assert.match(body, new RegExp(
            "x:\\s*mediaArtwork\\.x\\s*\\+\\s*musicMark\\.x\\s*\\+\\s*" + sourceId + "\\.x"
        ));
        assert.match(body, new RegExp(
            "y:\\s*mediaArtwork\\.y\\s*\\+\\s*musicMark\\.y\\s*\\+\\s*" + sourceId + "\\.y"
        ));
        assert.match(body, new RegExp("width:\\s*" + sourceId + "\\.width"));
        assert.match(body, new RegExp("height:\\s*" + sourceId + "\\.height"));
        assert.match(body, /horizontalOffset:\s*0/);
        assert.match(body, /verticalOffset:\s*0/);
        assert.match(body, /radius:\s*mediaDock\.contentGlowRadius\s*\+\s*4/);
        assert.match(body, /samples:\s*mediaDock\.contentGlowSamples\s*\+\s*6/);
        assert.match(body, /opacity:\s*Math\.min\(1\.0,\s*mediaDock\.contentGlowOpacity\s*\+\s*0\.18\)/);
        assert.match(body, /color:\s*mediaDock\.accentColor/);
        assert.match(body, /transparentBorder:\s*true/);
        assert.match(body, /z:\s*0/);
        assert.doesNotMatch(body, /cavaBar|levels|frame|Repeater|ShaderEffect/,
            "no effect can sample the animated spectrum");
    }

    // Artwork renders above its glow sources. CAVA owns only its existing
    // geometry-only per-bar halos, never a combined drop-shadow texture.
    assert.match(source, /Row \{\s*id:\s*mediaArtwork\s*anchors\.centerIn:\s*parent\s*spacing:\s*9\s*z:\s*1/);
    assert.doesNotMatch(source, /id:\s*(?:musicMarkUnderlay|mediaArtworkUnderlay)/);
    assert.doesNotMatch(source, /RectangularShadow \{/);
    assert.match(source, /contentGlowEnabled:\s*false/);
    assert.match(source, /contentGlowSource:\s*null/);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:musicMark|mediaArtwork|spectrum|cavaBar)/);
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
    assert.match(bar, /opacity:\s*0\.22/);
    assert.match(bar, /opacity:\s*0\.40/);
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
