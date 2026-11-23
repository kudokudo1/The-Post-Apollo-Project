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

assert.match(toggle, /˖/);
assert.match(toggle, /⚕๋࣭/);
assert.match(toggle, /⭑/);
assert.match(toggle, /labelItem\.textFormat:\s*Text\.StyledText/);
assert.match(toggle, /selected:\s*diagnosticsOpen/);
assert.equal((toggle.match(/Colors\.white/g) || []).length, 2,
    "both decorated stars must be white");
assert.doesNotMatch(toggle, /label:\s*diagnosticsOpen\s*\?\s*"BACK"/);

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
