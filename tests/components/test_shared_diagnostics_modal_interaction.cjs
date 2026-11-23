#!/usr/bin/env node
"use strict";
// Execute the actual popup wheel handler and inspect the shared geometry
// and glow contracts. No compositor, data service, or local files are changed.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const from = p => fs.readFileSync(path.resolve(__dirname, "../../", p), "utf8");

const popup = from("components/DiagnosticsServicePopup.qml");
const toggle = from("components/DiagnosticsDockButton.qml");
const close = from("components/CloseButton.qml");
const resize = from("components/ResizeButton.qml");
const finance = from("widgets/FinanceW.qml");
const weather = from("widgets/weather/WeatherStationW.qml");

// All sampled glow intensities come from the shared × and arrow grammar,
// not another independent cosmetic tuning table.
for (const key of [
    "contentGlowRadius", "contentGlowSamples",
    "contentGlowIdleOpacity", "contentGlowHoverOpacity",
    "contentGlowPressedOpacity", "contentGlowSelectedOpacity",
    "contentGlowKeyboardSelectedOpacity",
    "softGlowSpread", "softGlowIdleOpacity",
    "softGlowHoverOpacity", "softGlowPressedOpacity",
    "softGlowSelectedOpacity", "softGlowKeyboardSelectedOpacity",
    "wideGlowSpread", "wideGlowIdleOpacity",
    "wideGlowHoverOpacity", "wideGlowPressedOpacity",
    "wideGlowSelectedOpacity", "wideGlowKeyboardSelectedOpacity"
]) {
    const pattern = new RegExp("^\\s*" + key + ":\\s*([^\\n]+)", "m");
    const base = close.match(pattern);
    const arrow = resize.match(pattern);
    const diagnostic = toggle.match(pattern);
    assert.ok(base && arrow && diagnostic, "glow property missing: " + key);
    assert.equal(diagnostic[1].trim(), base[1].trim(),
        "diagnostic glow differs from canonical × for " + key);
    assert.equal(diagnostic[1].trim(), arrow[1].trim(),
        "diagnostic glow differs from shared arrow for " + key);
}

// The composite shares a centered Row but paints each glyph separately.
// White stars must never inherit the medical glyph's hover or pressed color.
assert.match(toggle, /id:\s*diagnosticsArtwork[\s\S]*?anchors\.centerIn:\s*parent/);
assert.match(toggle, /id:\s*diagnosticsSymbols[\s\S]*?spacing:\s*-2/);
function glyphBody(id) {
    const start = toggle.indexOf("id: " + id);
    assert.ok(start >= 0, "missing composite glyph " + id);
    const end = toggle.indexOf("\n            }", start);
    assert.ok(end > start);
    return toggle.slice(start, end);
}
const left = glyphBody("diagnosticsLeftStar");
const medical = glyphBody("diagnosticsMedicalSymbol");
const right = glyphBody("diagnosticsRightStar");
assert.match(left, /text:\s*"˖"/);
assert.match(medical, /text:\s*"⚕๋࣭"/);
assert.match(right, /text:\s*"⭑"/);
for (const part of [left,right]) {
    assert.match(part, /color:\s*Colors\.white/);
    assert.doesNotMatch(part, /diagnosticButton\.foregroundColor|accentColor/);
}
assert.match(medical, /color:\s*diagnosticButton\.foregroundColor/);
assert.match(toggle, /contentGlowSource:\s*diagnosticsMedicalSymbol/);
assert.match(toggle, /label:\s*""/);
assert.doesNotMatch(toggle, /Text\.StyledText|<font/);
assert.match(toggle, /selected:\s*diagnosticsOpen/);
assert.equal((toggle.match(/color:\s*Colors\.white/g) || []).length, 2,
    "both decorative stars keep white paint in all button states");

// Downward ResizeButton's semantic accent is orange. Its yellow hover
// surface must not be paired with an invisible yellow medical glyph.
// Check actual source color recipes, not only numeric glow intensity.
assert.match(resize, /property color decreaseAccentColor:\s*Colors\.orange/);
assert.match(toggle, /accentColor:\s*Colors\.orange/);
for (const key of [
    "idleFillColor","hoverFillColor","pressedFillColor","selectedFillColor",
    "idleForegroundColor","hoverForegroundColor","pressedForegroundColor",
    "selectedForegroundColor","idleBorderColor","hoverBorderColor",
    "pressedBorderColor","selectedBorderColor","idleContentGlowColor",
    "hoverContentGlowColor","pressedContentGlowColor",
    "selectedContentGlowColor","idleSoftGlowColor","hoverSoftGlowColor",
    "pressedSoftGlowColor","selectedSoftGlowColor","idleWideGlowColor",
    "hoverWideGlowColor","pressedWideGlowColor","selectedWideGlowColor"
]) {
    const re = new RegExp("^\\s*" + key + ":\\s*([^\\n]+)", "m");
    const expected = resize.match(re);
    const actual = toggle.match(re);
    assert.ok(expected && actual, "missing down-arrow color recipe " + key);
    assert.equal(actual[1].trim(),expected[1].trim(),
        "diagnostics does not match down-arrow state " + key);
}

assert.match(popup, /id:\s*diagnosticsPointerShield/);
assert.match(popup, /id:\s*diagnosticsWheelContainment/);
assert.match(popup, /blocking:\s*true/);
assert.match(popup, /color:\s*"#110319"/);
assert.match(popup, /opacity:\s*1\.0/);
assert.match(popup, /CloseButton\s*\{[\s\S]*?onCloseRequested:\s*diagnosticsPane\.closeRequested\(\)/);
assert.doesNotMatch(popup, /ActionButton\s*\{/);
assert.match(popup, /mountingParent:\s*diagnosticsPane/);
assert.match(popup, /geometryHost:\s*diagnosticsPane/);
assert.match(popup, /geometryMode:\s*"box"/);
assert.match(popup, /boxTopInset:\s*68/);
assert.match(popup, /boxBottomInset:\s*12/);
assert.match(popup, /rightInset:\s*8/);
assert.match(popup, /diagnosticsScroll\.width\s*-\s*44/);

// Extract and EXECUTE the real wheel callback, not a restatement.
// It must scroll within its own content and accept all deltas even when
// already at either end, so Budget and Weather below cannot scroll.
const marker = "id: diagnosticsWheelContainment";
const fromMarker = popup.slice(popup.indexOf(marker));
const handlerMarker = "onWheel: function(wheel) {";
const offset = fromMarker.indexOf(handlerMarker);
assert.ok(offset >= 0);
const open = fromMarker.indexOf("{", offset);
let depth = 0, closeAt = -1;
for (let i = open; i < fromMarker.length; i++) {
    if (fromMarker[i] === "{") depth++;
    else if (fromMarker[i] === "}") {
        depth--;
        if (depth === 0) { closeAt = i; break; }
    }
}
assert.ok(closeAt > open, "wheel callback has a complete body");
const callback = "function(wheel) " + fromMarker.slice(open, closeAt + 1);

function dispatch(current, height, contentHeight, pixelY, angleY) {
    const diagnosticsScroll = { contentY:current, height, contentHeight };
    const context = vm.createContext({ diagnosticsScroll, Math });
    const realCallback = vm.runInContext("(" + callback + ")", context);
    const wheel = {pixelDelta:{y:pixelY}, angleDelta:{y:angleY},
        accepted:false};
    realCallback(wheel);
    return {at:diagnosticsScroll.contentY,accepted:wheel.accepted};
}
assert.deepEqual(dispatch(90,100,400,0,-120), {at:132,accepted:true},
    "wheel down moves the popup only");
assert.deepEqual(dispatch(0,100,400,0,120), {at:0,accepted:true},
    "wheel at top is swallowed");
assert.deepEqual(dispatch(300,100,400,0,-120), {at:300,accepted:true},
    "wheel at bottom is swallowed");
assert.deepEqual(dispatch(50,100,400,25,0), {at:25,accepted:true},
    "pixel deltas are handled without reaching the host");
assert.deepEqual(dispatch(0,100,100,0,-120), {at:0,accepted:true},
    "wheel on a non-scrolling inspector remains contained");

for (const [source, backing, overlay, backdropZ, overlayZ] of [
    [finance, "financeDiagnosticsBackdrop", "financeDiagnosticsPane",89,90],
    [weather,"providerDiagnosticsBackdrop","providerDiagnosticsPane",49,50]
]) {
    const parent = source.indexOf("id: " + backing);
    const pane = source.indexOf("id: " + overlay);
    assert.ok(parent >= 0 && pane > parent,
        "modal backdrop appears before its top-level inspector");
    assert.match(source.slice(parent, parent + 320),
        new RegExp("z:\\s*" + backdropZ));
    assert.match(source.slice(pane, pane + 200),
        new RegExp("z:\\s*" + overlayZ));
    const shield = source.slice(parent, pane);
    assert.match(shield, /MouseArea\s*\{/);
    assert.match(shield, /acceptedButtons:\s*Qt\.AllButtons/);
    assert.match(shield, /onWheel:\s*function\(wheel\)\s*\{\s*wheel\.accepted\s*=\s*true/);
}
console.log("Shared diagnostics: exact glow, modal layering, inset star rail and wheel containment PASS");
