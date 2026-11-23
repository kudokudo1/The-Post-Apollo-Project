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
const resync = from("components/ReloadButton.qml");
const finance = from("widgets/FinanceW.qml");
const weather = from("widgets/weather/WeatherStationW.qml");
const financePopup = finance.slice(finance.indexOf("id: financeDiagnosticsPane"));
const weatherPopup = weather.slice(weather.indexOf("id: providerDiagnosticsPane"));

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

// The screenshot exposed the old Unicode combining marks: they inherited the
// medical icon's orange/yellow instead of being white. The new component uses
// separate WHITE Text for every ornament and a plain medical staff.
assert.match(toggle, /id:\s*diagnosticsArtwork[\s\S]*?anchors\.centerIn:\s*parent/);
function glyphBody(id) {
    const start = toggle.indexOf("id: " + id);
    assert.ok(start >= 0, "missing actual glyph: " + id);
    const end = toggle.indexOf("\n        }", start);
    assert.ok(end > start);
    return toggle.slice(start, end);
}
const left = glyphBody("diagnosticsLeftStar");
const medical = glyphBody("diagnosticsMedicalSymbol");
const upper = glyphBody("diagnosticsUpperStar");
const right = glyphBody("diagnosticsRightStar");
assert.match(left, /text:\s*"˖"/);
assert.match(medical, /text:\s*"⚕"/);
assert.match(upper, /text:\s*"✦"/);
assert.match(right, /text:\s*"⭑"/);
for (const part of [left, upper, right]) {
    assert.match(part, /color:\s*diagnosticButton\.diagnosticsOpen\s*\?\s*Colors\.magenta\s*:\s*Colors\.white/);
    assert.match(part, /textFormat:\s*Text\.PlainText/);
    assert.doesNotMatch(part, /diagnosticButton\.foregroundColor|accentColor/);
}
assert.match(medical, /color:\s*diagnosticButton\.foregroundColor/);
assert.doesNotMatch(toggle, /text:\s*"⚕๋࣭"/);
assert.equal((toggle.match(/color:\s*diagnosticButton\.diagnosticsOpen\s*\?\s*Colors\.magenta\s*:\s*Colors\.white/g) || []).length, 3,
    "all three ornaments turn magenta when the panel is open and remain white when closed");
assert.match(toggle, /contentGlowSource:\s*diagnosticsMedicalSymbol/);
assert.match(toggle, /label:\s*""/);
assert.match(toggle, /selected:\s*diagnosticsOpen/);
assert.match(toggle, /width:\s*38/);
assert.match(toggle, /height:\s*32/);
assert.match(toggle, /anchors\.rightMargin:\s*-6/);
assert.doesNotMatch(toggle, /id:\s*diagnosticsSymbols|spacing:\s*-2|Text\.StyledText/);

// Follow TimeW's observed RESYNC button, not ResizeButton. Check the real
// color expressions on ALL planes, and separately keep ×/arrow glow strength.
assert.match(resync, /property color semanticColor:\s*Colors\.yellow/);
assert.match(resync, /property color hoverSurfaceColor:\s*Colors\.orange/);
assert.match(toggle, /property color semanticColor:\s*Colors\.yellow/);
assert.match(toggle, /property color hoverSurfaceColor:\s*Colors\.orange/);
for (const key of [
    "accentColor", "idleFillColor","hoverFillColor","pressedFillColor",
    "keyboardSelectedFillColor",
    "idleForegroundColor","hoverForegroundColor","pressedForegroundColor",
    "keyboardSelectedForegroundColor",
    "idleBorderColor","hoverBorderColor","pressedBorderColor",
    "keyboardSelectedBorderColor",
    "idleContentGlowColor","hoverContentGlowColor","pressedContentGlowColor",
    "keyboardSelectedContentGlowColor",
    "idleSoftGlowColor","hoverSoftGlowColor","pressedSoftGlowColor",
    "keyboardSelectedSoftGlowColor",
    "idleWideGlowColor","hoverWideGlowColor","pressedWideGlowColor",
    "keyboardSelectedWideGlowColor"
]) {
    const expression = new RegExp("^\\s*" + key + ":\\s*([^\\n]+)", "m");
    const expected = resync.match(expression);
    const actual = toggle.match(expression);
    assert.ok(expected && actual, "missing TimeW RESYNC recipe " + key);
    assert.equal(actual[1].trim(),expected[1].trim(),
        "diagnostics differs from RESYNC at " + key);
}

// OPEN follows the ordinary activated-button rule. The background is
// yellow while the medical symbol, three stars, border and ALL glows are
// magenta; idle/hover/press still match the existing TimeW RESYNC control.
for (const [key,expected] of [
    ["selectedFillColor","Colors.yellow"],
    ["selectedForegroundColor","Colors.magenta"],
    ["selectedBorderColor","Colors.magenta"],
    ["selectedContentGlowColor","Colors.magenta"],
    ["selectedSoftGlowColor","Colors.magenta"],
    ["selectedWideGlowColor","Colors.magenta"]
]) {
    const expression = new RegExp("^\\s*" + key + ":\\s*([^\\n]+)", "m");
    const actual = toggle.match(expression);
    assert.ok(actual,key + " missing");
    assert.equal(actual[1].trim(),expected,key + " open-state mismatch");
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
assert.match(popup, /boxTopInset:\s*7/);
assert.match(popup, /boxBottomInset:\s*12/);
assert.match(popup, /rightInset:\s*8/);
assert.match(popup, /railSpaceReserved\s*\?\s*44\s*:\s*24/);
assert.match(popup, /property bool railSpaceReserved:\s*false/);
assert.match(popup, /onContentHeightChanged:\s*Qt\.callLater/);
assert.match(popup, /id:\s*diagnosticsPinnedHeader/);
assert.match(popup, /id:\s*diagnosticsPinnedDivider/);
assert.match(popup, /anchors\.top:\s*diagnosticsPinnedHeader\.bottom/);
const headerIndex = popup.indexOf("id: diagnosticsPinnedHeader");
const scrollIndex = popup.indexOf("id: diagnosticsScroll");
const closeIndex = popup.indexOf("id: diagnosticsCloseButton");
assert.ok(headerIndex >= 0 && closeIndex > headerIndex
       && closeIndex < scrollIndex,
    "title and CloseButton must stay above/outside the scrolling body");

// Execute the actual gutter decision using synthetic content heights.
// With no overflow, no 44px gutter can remain.
const fnStart = popup.indexOf("    function updateRailSpace() {");
const fnEnd = popup.indexOf("\n    signal closeRequested()",fnStart);
assert.ok(fnStart>=0 && fnEnd>fnStart);
const actualGutterFunction = popup.slice(fnStart,fnEnd).trim();
const pane = {railSpaceReserved:false};
const sampleScroll = {contentHeight:100,height:200};
const sampleRail = {scrollThreshold:1};
const paneContext = vm.createContext({
    diagnosticsScroll:sampleScroll, diagnosticsRail:sampleRail,
    get railSpaceReserved() { return pane.railSpaceReserved; },
    set railSpaceReserved(value) { pane.railSpaceReserved = value; }
});
const updateGutter = vm.runInContext("(" + actualGutterFunction + ")",paneContext);
updateGutter();
assert.equal(pane.railSpaceReserved,false);
sampleScroll.contentHeight=260;
updateGutter();
assert.equal(pane.railSpaceReserved,true,"overflow reserves the star rail area");
sampleScroll.contentHeight=200;
updateGutter();
assert.equal(pane.railSpaceReserved,false,"gutter clears when scrollbar disappears");
assert.match(popup, /visible:\s*scrollable/);

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
for (const [s,button] of [
    [financePopup,"financeDiagnosticsButton"],
    [weatherPopup,"providerDiagnosticsButton"]
]) {
    assert.match(s,new RegExp(button + "\\.mapToItem\\(parent,"));
    assert.match(s,/readonly property point dropFromButton/);
    assert.match(s,/dropFromButton\.x/);
    assert.match(s,/dropFromButton\.y/);
    assert.doesNotMatch(s.slice(0,500),/anchors\.top:\s*parent\.top/);
}

console.log("Shared diagnostics: exact glow, modal layering, inset star rail and wheel containment PASS");
