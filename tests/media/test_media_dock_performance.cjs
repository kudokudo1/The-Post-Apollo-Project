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
const shellSource = fs.readFileSync(path.join(root, "shell.qml"), "utf8");
const dockButtonSource = fs.readFileSync(path.join(root, "components/DockButton.qml"), "utf8");
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

test("left taskbar places Media before Tray without duplicating either instance", () => {
    const left = shellSource.split("// ===== LEFT MODULES", 2)[1]
        ?.split("// ===== CENTER MODULE", 2)[0];
    assert.ok(left, "left taskbar row must exist");
    const workspaces = left.indexOf("Workspaces {}");
    const media = left.indexOf("Mediaplayer {\n            id: sharedMediaDock\n        }");
    const tray = left.indexOf("Tray {}");
    const hospital = left.indexOf("// Hospital");
    assert.ok(workspaces >= 0 && workspaces < media && media < tray && tray < hospital,
        "expected Workspaces → Media Player → Tray → Hospital");
    assert.equal((left.match(/Mediaplayer \{/g) || []).length, 1);
    assert.equal((left.match(/Tray \{\}/g) || []).length, 1);
    assert.match(shellSource, /mediaControllerSource:\s*sharedMediaDock\.hubMediaController/);
    assert.match(shellSource, /mpdDockSource:\s*sharedMediaDock/);
});

test("left taskbar uses close 8px gaps except App Control to Workspaces", () => {
    const left = shellSource.split("// ===== LEFT MODULES", 2)[1]
        ?.split("// ===== CENTER MODULE", 2)[0];
    const right = shellSource.split("// ===== RIGHT MODULES", 2)[1];
    assert.ok(left, "leftModules must be present");
    assert.match(left, /Row \{\s*id:\s*leftModules[\s\S]*?spacing:\s*8/);
    assert.match(right, /spacing:\s*8/,
        "use the already-established compact right-module spacing");

    // QtQuick Row inserts spacing before and after a visible spacer Item.
    // This keeps exactly the old App Control→Workspaces 25px gap.
    const gap = left.match(/Item \{\s*id:\s*appControlWorkspaceGap\s*width:\s*(\d+)\s*height:\s*1\s*\}/);
    assert.ok(gap, "only the launcher/workspace boundary needs an extra gap");
    assert.equal(Number(gap[1]) + 2 * 8, 25);
    assert.equal((left.match(/id:\s*appControlWorkspaceGap\b/g) || []).length, 1);
    const launcher = left.indexOf("id: appControlWindow");
    const gapAt = left.indexOf("id: appControlWorkspaceGap");
    const workspace = left.indexOf("Workspaces {}");
    const media = left.indexOf("Mediaplayer {");
    const tray = left.indexOf("Tray {}");
    const hospital = left.indexOf("// Hospital");
    const finance = left.indexOf("// Finance");
    const git = left.indexOf("// Git");
    const tasks = left.indexOf("Tasks {\n                id: tasksButton");
    assert.ok([launcher, gapAt, workspace, media, tray, hospital, finance, git, tasks]
        .every((v, i, a) => v >= 0 && (!i || v > a[i - 1])),
        "spacer must appear only after App Control and all left-module order is preserved");
});

test("opening the Hi-Fi deck gives Media the canonical yellow fill without removing neon", () => {
    // The Media dock now adopts the canonical yellow open fill while
    // preserving its own magenta open-state icons and independent glows.
    assert.match(source, /open:\s*mediaRoot\.deckOpen/);
    assert.match(source, /openFillColor:\s*Colors\.yellow/);
    assert.match(dockButtonSource, /property color closedFillColor:\s*Colors\.black/,
        "closed Media retains the existing dark base");
    assert.match(dockButtonSource, /property color openFillColor:\s*Colors\.yellow/,
        "the shared DockButton default remains untouched");
    assert.match(dockButtonSource, /color:\s*open\s*\?\s*openFillColor\s*:\s*closedFillColor/);
    assert.match(source, /mediaRoot\.deckOpen = !mediaRoot\.deckOpen;/);

    // Only the Media fill changes. The magenta front wash, open-state rear
    // priority, and closed CAVA cyan/orange accent remain as before.
    assert.match(source, /normalDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /hoverDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /pressedDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /color:\s*mediaDock\.open\s*\?\s*mediaDock\.openGlowColor\s*:\s*mediaDock\.accentColor/);
    assert.match(source, /color:\s*mediaDock\.artworkAccentColor/);
    assert.match(source, /id:\s*leadingStarsAura/);
    assert.match(source, /id:\s*trailingStarAura/);
    assert.match(source, /id:\s*cavaAmbientWash/);
});

test("open state magenta-energizes every Media icon and CAVA visual without affecting MPD", () => {
    assert.match(source, /open:\s*mediaRoot\.deckOpen/);
    assert.match(source, /openFillColor:\s*Colors\.yellow/);
    assert.match(source, /readonly property color accentColor:\s*mpdPlaying \? Colors\.orange : Colors\.cyan/);
    assert.match(source, /readonly property color artworkAccentColor:\s*open \? Colors\.magenta : accentColor/);

    // Evaluate the QML binding's actual conditional: closed is driven by
    // playback, while open always wins even if MPD is playing.
    const match = source.match(/readonly property color artworkAccentColor:\s*([^\n]+)/);
    assert.ok(match);
    const expression = match[1];
    const visual = (open, playing) => vm.runInNewContext(expression, {
        open,
        accentColor: playing ? "#ED981A" : "#55CFCA",
        Colors: {magenta: "#C74EC7"}
    });
    assert.equal(visual(false, false), "#55CFCA");
    assert.equal(visual(false, true), "#ED981A");
    assert.equal(visual(true, false), "#C74EC7");
    assert.equal(visual(true, true), "#C74EC7");

    // The shared DockButton's open foreground turns both ornament texts
    // magenta without replacing the glyphs. Its front wash stays magenta.
    assert.match(dockButtonSource, /property color openForegroundColor:\s*Colors\.magenta/);
    assert.match(dockButtonSource, /readonly property color foregroundColor:\s*open\s*\?\s*openForegroundColor/);
    assert.equal((source.match(/color:\s*mediaDock\.foregroundColor/g) || []).length, 2);
    assert.match(source, /normalDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /hoverDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /pressedDockGlowColor:\s*Colors\.magenta/);

    // Each star underlight + source shadow, clef source shadow, CAVA ambient,
    // and both halos and cores on all 16 bars share the same open-priority
    // color without sampling the animated bars as a blur texture.
    // The treble clef now owns an additional independently accent-colored
    // aura, so open-state magenta covers ten rather than nine visual layers.
    assert.equal((source.match(/color:\s*mediaDock\.artworkAccentColor/g) || []).length, 10);
    assert.doesNotMatch(source, /^\s*color:\s*mediaDock\.accentColor\s*$/m);
    assert.equal((source.match(/SafeDropShadow \{/g) || []).length, 3);
    assert.equal((source.match(/RectangularShadow \{/g) || []).length, 5);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:spectrum|cavaBar|mediaArtwork)/);
    assert.match(source, /id:\s*cavaAmbientWash[\s\S]*?height:\s*mediaDock\.cavaAmbientTargetHeight/);
    assert.match(source, /if \(changed\)\s*levels = newLevels;/);
});

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

test("magenta front wash and CAVA-colored static music mark stay independent", () => {
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
    assert.match(mark, /source:\s*mediaDock\.open\s*\?\s*Qt\.resolvedUrl\("\.\.\/assets\/media\/treble-clef\.png"\)\s*:\s*mediaDock\.mpdPlaying\s*\?\s*Qt\.resolvedUrl\("\.\.\/assets\/media\/treble-clef-orange\.png"\)\s*:\s*Qt\.resolvedUrl\("\.\.\/assets\/media\/treble-clef-cyan\.png"\)/);
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
    assert.match(source, /color:\s*mediaDock\.artworkAccentColor/);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:spectrum|mediaArtwork)/);
});

test("Media's rear halo follows CAVA while DockButton's front wash stays magenta", () => {
    // Split the two planes locally; no shared DockButton code may change to
    // customize one module, especially while the alignment pilot is active.
    assert.match(source, /softGlowEnabled:\s*false/);
    const rearMatch = source.match(/RectangularShadow \{\s*id:\s*mediaRearHalo([\s\S]*?)\n    \}/);
    assert.ok(rearMatch, "Media owns a replacement rear halo behind the DockButton");
    const rear = rearMatch[1];
    assert.match(rear, /anchors\.fill:\s*mediaDock/);
    assert.match(rear, /spread:\s*mediaDock\.softGlowSpread/);
    assert.match(rear, /opacity:\s*mediaDock\.softGlowOpacity/);
    assert.match(rear, /color:\s*mediaDock\.open\s*\?\s*mediaDock\.openGlowColor\s*:\s*mediaDock\.accentColor/);
    assert.match(rear, /visible:\s*mediaDock\.visible/);
    assert.match(rear, /z:\s*-1/);
    assert.doesNotMatch(rear, /safeSource|levels|cavaBar|ShaderEffect|Behavior on height/,
        "rear chassis halo must not sample or animate with CAVA bars");
    assert.ok(source.indexOf("id: mediaRearHalo") < source.indexOf("DockButton {"),
        "the rear halo must be outside and behind the dock content plane");

    assert.match(source, /normalDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /hoverDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /pressedDockGlowColor:\s*Colors\.magenta/);
    assert.match(source, /readonly property color accentColor:\s*mpdPlaying \? Colors\.orange : Colors\.cyan/);

    // The shared component retains the default identity and numeric rules
    // for other modules; only this module disables its built-in rear halo.
    assert.match(dockButtonSource, /property bool softGlowEnabled:\s*true/);
    assert.match(dockButtonSource, /property bool wideGlowEnabled:\s*true/);
    assert.match(dockButtonSource, /readonly property color dockGlowColor:/);
    const rearIndex = dockButtonSource.indexOf("visible: dockButton.softGlowEnabled");
    const frontIndex = dockButtonSource.indexOf("visible: dockButton.wideGlowEnabled");
    assert.ok(rearIndex >= 0 && frontIndex > rearIndex);
    assert.match(dockButtonSource.slice(frontIndex), /color:\s*dockButton\.dockGlowColor/);
    assert.match(dockButtonSource, /property color openGlowColor:\s*Colors\.magenta/);
});

test("stars and treble clef each have a matching local accent aura", () => {
    // The three static glyph groups each need local, equal-strength underlight
    // in addition to their independent source-attached shadows.
    for (const [auraId, glyphId] of [
        ["leadingStarsAura", "leadingStars"],
        ["trebleClefAura", "trebleClef"],
        ["trailingStarAura", "trailingStar"]
    ]) {
        const match = source.match(new RegExp(
            "RectangularShadow \\{\\s*id:\\s*" + auraId + "([\\s\\S]*?)\\n    \\}"
        ));
        assert.ok(match, auraId + " must be a separate, static underlight");
        const body = match[1];
        assert.match(body, new RegExp(
            "x:\\s*mediaArtwork\\.x\\s*\\+\\s*musicMark\\.x\\s*\\+\\s*" + glyphId + "\\.x"
        ));
        assert.match(body, new RegExp(
            "y:\\s*mediaArtwork\\.y\\s*\\+\\s*musicMark\\.y\\s*\\+\\s*" + glyphId + "\\.y"
        ));
        assert.match(body, new RegExp(
            "width:\\s*Math\\.max\\(1,\\s*" + glyphId + "\\.width\\s*-\\s*2\\s*\\*\\s*mediaDock\\.softGlowSpread\\)"
        ));
        assert.match(body, new RegExp(
            "height:\\s*Math\\.max\\(1,\\s*" + glyphId + "\\.height\\s*-\\s*2\\s*\\*\\s*mediaDock\\.softGlowSpread\\)"
        ));
        assert.match(body, /radius:\s*height\s*\/\s*2/);
        assert.match(body, /blur:\s*mediaDock\.contentGlowRadius\s*\+\s*4/);
        assert.match(body, /spread:\s*0/);
        assert.match(body, /color:\s*mediaDock\.artworkAccentColor/);
        assert.match(body, /opacity:\s*mediaDock\.softGlowOpacity/);
        assert.match(body, /z:\s*0/);
        assert.doesNotMatch(body, /safeSource|cavaBar|levels|frame|Repeater|ShaderEffect|Behavior on/,
            "star underlights must not sample or follow CAVA bar frames");
    }
    assert.equal((source.match(/RectangularShadow \{/g) || []).length, 5);
    assert.equal((source.match(/SafeDropShadow \{/g) || []).length, 3);
    assert.match(source, /Row \{\s*id:\s*mediaArtwork\s*anchors\.centerIn:\s*parent\s*spacing:\s*9\s*z:\s*1/);
    assert.match(source, /id:\s*leadingStars[\s\S]*?text:\s*"‧₊˚ "[\s\S]*?color:\s*mediaDock\.foregroundColor/);
    assert.match(source, /id:\s*trailingStar[\s\S]*?text:\s*"˖"[\s\S]*?color:\s*mediaDock\.foregroundColor/);
    // The clef preserves its font-independent PNG and has one sampled
    // shadow plus one underlight, just like each ornament group.
    assert.match(source, /id:\s*trebleClef\s*width:\s*15\s*height:\s*34/);
    assert.match(source, /source:\s*mediaDock\.open\s*\?\s*Qt\.resolvedUrl\("\.\.\/assets\/media\/treble-clef\.png"\)/);
    assert.equal((source.match(/id:\s*trebleClefAura\b/g) || []).length, 1);
    assert.equal((source.match(/id:\s*trebleClefGlow\b/g) || []).length, 1);
    assert.doesNotMatch(source, /id:\s*(?:musicMarkUnderlay|mediaArtworkUnderlay)/);
});

test("magenta front wash, three independent static art glows, per-bar CAVA halos", () => {
    // Media keeps the built-in front wash magenta; rear halo is overridden separately.
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
        assert.match(body, /color:\s*mediaDock\.artworkAccentColor/);
        assert.match(body, /transparentBorder:\s*true/);
        assert.match(body, /z:\s*0/);
        assert.doesNotMatch(body, /cavaBar|levels|frame|Repeater|ShaderEffect/,
            "no effect can sample the animated spectrum");
    }

    // Artwork renders above its glow sources. CAVA owns only its existing
    // geometry-only per-bar halos, never a combined drop-shadow texture.
    assert.match(source, /Row \{\s*id:\s*mediaArtwork\s*anchors\.centerIn:\s*parent\s*spacing:\s*9\s*z:\s*1/);
    assert.doesNotMatch(source, /id:\s*(?:musicMarkUnderlay|mediaArtworkUnderlay)/);
    assert.equal((source.match(/RectangularShadow \{/g) || []).length, 5,
        "rear and CAVA washes plus three independently bounded glyph auras");
    assert.match(source, /contentGlowEnabled:\s*false/);
    assert.match(source, /contentGlowSource:\s*null/);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:musicMark|mediaArtwork|spectrum|cavaBar)/);
});

test("large faded CAVA-only ambient wash follows a padded spectrum envelope", () => {
    // This is an additional ambient layer, not a replacement for the 16
    // individual CAVA bar halos or the separate static ornament glows.
    const section = source.match(/Item \{\s*id:\s*spectrum([\s\S]*?)\n\s*Row \{\s*anchors\.fill:\s*parent\s*spacing:\s*2/);
    assert.ok(section, "the wash must belong to the CAVA spectrum, not the whole dock");
    const match = section[1].match(/RectangularShadow \{\s*id:\s*cavaAmbientWash([\s\S]*?)\n\s*\}/);
    assert.ok(match, "there must be one dedicated wide CAVA wash");
    const wash = match[1];

    assert.match(wash, /anchors\.horizontalCenter:\s*parent\.horizontalCenter/);
    assert.match(wash, /anchors\.bottom:\s*parent\.bottom/);
    assert.match(wash, /anchors\.bottomMargin:\s*-2/);
    assert.match(wash, /width:\s*Math\.max\(0,\s*spectrum\.width\s*\+\s*2\s*\*\s*\(mediaDock\.contentGlowRadius\s*\+\s*4\s*\+\s*mediaDock\.softGlowSpread\)\)/);
    assert.match(source,
        /id:\s*spectrum\s*width:\s*mediaDock\.barCount\s*\*\s*5\s*\+\s*\(mediaDock\.barCount\s*-\s*1\)\s*\*\s*2/);
    const washWidthExpression = wash.match(/width:\s*(Math\.max\(0,\s*spectrum\.width\s*\+\s*2\s*\*\s*\(mediaDock\.contentGlowRadius\s*\+\s*4\s*\+\s*mediaDock\.softGlowSpread\)\))/);
    assert.ok(washWidthExpression, "ambient wash should react to the spectrum width");
    const widthForBarCount = count => vm.runInNewContext(washWidthExpression[1], {
        Math,
        spectrum: {width: count * 5 + (count - 1) * 2},
        mediaDock: {softGlowSpread: 3, contentGlowRadius: 14}
    });
    assert.equal(widthForBarCount(16), 152, "the wash places both blur edges beyond the end bars");
    assert.equal(widthForBarCount(24), 208, "adding eight bars must extend the side glow automatically");
    assert.equal(widthForBarCount(24) - widthForBarCount(16), 8 * (5 + 2),
        "wash growth must match the spectrum growth without fixed pixel widths");
    assert.equal((widthForBarCount(16) - (16 * 5 + 15 * 2)) / 2, 14 + 4 + 3,
        "each blur shoulder extends equally past its nearest edge bar");
    assert.match(wash, /height:\s*mediaDock\.cavaAmbientTargetHeight/);
    assert.match(wash, /radius:\s*height\s*\/\s*2/);
    assert.match(wash, /blur:\s*mediaDock\.contentGlowRadius\s*\+\s*4/);
    assert.match(wash, /spread:\s*0/);
    assert.match(wash, /color:\s*mediaDock\.artworkAccentColor/);
    assert.match(wash, /opacity:\s*0\.22/);
    assert.match(wash, /z:\s*-1/);
    assert.match(wash, /Behavior on height\s*\{\s*NumberAnimation\s*\{\s*duration:\s*180\s*easing\.type:\s*Easing\.OutQuad/);
    assert.doesNotMatch(wash, /cavaBar|levels|frame|Repeater|safeSource|ShaderEffect|source:/,
        "the ambient wash must not sample moving CAVA frames");

    // The soft CAVA ambient wash must remain separate from the rear accent
    // halo and the intentionally magenta front wash.
    assert.equal((source.match(/RectangularShadow \{/g) || []).length, 5);
    assert.doesNotMatch(source, /id:\s*(?:musicMarkUnderlay|mediaArtworkUnderlay)/);
    for (const mode of ["normal", "hover", "pressed"]) {
        assert.match(source, new RegExp(mode + "DockGlowColor:\\s*Colors\\.magenta"));
    }
    assert.match(source, /contentGlowEnabled:\s*false/);
    assert.doesNotMatch(source, /contentGlowSource:\s*(?:spectrum|cavaBar|mediaArtwork)/);
});

test("ambient height averages the four strongest CAVA bars with padding and smoothing", () => {
    const expression = source.match(
        /readonly property real cavaAmbientTargetHeight:\s*\{([\s\S]*?)\n    \}/
    );
    assert.ok(expression, "ambient target height should be computed from published levels");
    const envelope = (levels) => vm.runInNewContext(
        "(function() {" + expression[1] + "\n})()", {levels}
    );

    const silence = Array(16).fill(0);
    assert.equal(envelope(silence), 14, "a visible wash should remain at silence");
    assert.equal(envelope(Array(16).fill(7)), 34, "tall bars cap at the loose envelope limit");
    assert.equal(envelope([7, ...Array(15).fill(0)]), 19,
        "one sharp peak should not drag the entire ambient wash up");
    assert.equal(envelope([7, 7, 7, 7, ...Array(12).fill(0)]), 34,
        "several high bars should lift the ambient wash");
    assert.ok(envelope(Array(16).fill(4)) > envelope(Array(16).fill(1)),
        "the wash should rise as the overall spectrum grows");
    assert.match(source, /height:\s*mediaDock\.cavaAmbientTargetHeight/);
    assert.match(source, /if \(changed\)\s*levels = newLevels;/,
        "the wash must reuse CAVA's existing deduplicated frame publication");
    assert.doesNotMatch(source, /safeSource:\s*(?:spectrum|cavaBar)/);
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
    assert.equal((bar.match(/color:\s*mediaDock\.artworkAccentColor/g) || []).length, 3,
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
