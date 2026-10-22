#!/usr/bin/env node
// Static safety contracts for the QML headless-controller bridge.
// Runtime Quickshell and a real MPD service still require on-device testing.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const base = path.resolve(__dirname, "../..");
const deck = fs.readFileSync(path.join(base, "widgets/MediaDeckW.qml"), "utf8");
const bridge = fs.readFileSync(path.join(base, "services/media/HeadlessMediaController.qml"), "utf8");

test("deck uses persistent CLI bridge, never detached mpc for MPD", () => {
    assert.match(deck, /HeadlessMediaController\s*\{\s*id:\s*headless/);
    assert.match(deck, /headless\.transport\(action\)/);
    assert.doesNotMatch(deck, /Quickshell\.execDetached/);
    assert.doesNotMatch(deck, /\[\s*["']mpc["']/);
});

test("MPRIS transport is kept explicitly separate", () => {
    assert.match(deck, /if\s*\(transportMode\s*===\s*"mpris"\)/);
    assert.match(deck, /mediaAdapter\.run\(action\)/);
    assert.match(deck, /transportMode:\s*"mpd"/);
});

test("radio station load is explicit and does not autoplay", () => {
    assert.match(deck, /headless\.loadRadio\(radioStreamUrl\)/);
    assert.match(deck, /catalogSource === "direct-stream"/);
    assert.doesNotMatch(deck, /onClicked:\s*headless\.loadRadio/);
    assert.match(bridge, /issue\("load",\s*\["--source",\s*"direct-stream",\s*"--uri",\s*url\]\)/);
    assert.doesNotMatch(bridge, /--autoplay/);
    assert.match(deck, /LOAD DOES NOT AUTOPLAY/);
    assert.match(bridge, /Quickshell\.shellPath\("scripts\/media\/media_controller_cli\.py"\)/);
});

test("controller response determines UI status, not command launch", () => {
    assert.match(bridge, /JSON\.parse\(String\(raw\s*\|\|\s*""\)\)/);
    assert.match(bridge, /if\s*\(!payload\.ok\)/);
    assert.match(bridge, /snapshot\s*=\s*payload\.result/);
    assert.match(bridge, /ownsPlayback:/);
    assert.match(deck, /headless\.ownsPlayback/);
});

test("UI polling follows deck visibility; backend survives closure", () => {
    assert.match(deck, /polling:\s*deck\.menuOpen\s*&&\s*deck\.transportMode\s*===\s*"mpd"/);
    assert.match(bridge, /running:\s*bridge\.polling/);
    assert.doesNotMatch(bridge, /systemctl|pkill|killall|set-volume|wpctl|pactl|cava|\.stop\(\)/i);
});

test("live streams disallow seek/next and transport requires ownership", () => {
    assert.match(deck, /!headless\.loaded\.item\.live/);
    assert.match(deck, /headless\.ownsPlayback/);
    assert.match(deck, /enabled:\s*transportKey\.canControl/);
    assert.match(deck, /!headless\.busy/);
});

test("original browser audio experiment remains isolated to MPRIS", () => {
    assert.match(deck, /transportMode\s*!==\s*"mpris"/);
    assert.match(deck, /enabled:\s*deck\.transportMode\s*===\s*"mpris"/);
    assert.match(deck, /audioProbe\.refresh\(\)/);
});

test("background snapshot polling never flashes or disables radio cassette controls", () => {
    assert.match(bridge, /readonly property bool busy:\s*commandProcess\.running\s*&&\s*pendingAction\s*!==\s*"snapshot"/);
    assert.match(bridge, /onTriggered:\s*bridge\.refresh\(\)/);
    assert.match(bridge, /issue\("snapshot",\s*\[\]\)/);
    // The cassette bay is now display-only. Polling still never disables it.
    assert.match(deck, /id:\s*grooveCassette/);
    assert.doesNotMatch(deck, /id:\s*grooveMouse/);
    assert.match(deck, /height:\s*38/);
});

test("search and explicit staged selection are controller-only operations", () => {
    assert.match(bridge, /function searchMedia\(source, query, cursor\)/);
    assert.match(bridge, /return issue\("search", args\)/);
    assert.match(bridge, /function selectMedia\(ref\)/);
    assert.match(bridge, /return args !== null && issue\("select", args\)/);
    assert.match(bridge, /function loadSelectedMedia\(\)/);
    assert.match(bridge, /return issue\("load", \[\]\)/);
    assert.doesNotMatch(bridge, /--autoplay/);
});

test("catalog responses update browsing without clobbering loaded media", () => {
    assert.match(bridge, /pendingAction === "search" && payload\.result\.browse/);
    assert.match(bridge, /Object\.assign\(\{\}, snapshot \|\| \{\},/);
    assert.match(bridge, /browse: payload\.result\.browse/);
    assert.match(bridge, /selection: payload\.result\.selection/);
    assert.match(bridge, /pendingAction === "inspect" && payload\.result\.item/);
    assert.match(bridge, /readonly property var loaded:/);
    assert.match(bridge, /snapshot = payload\.result;/);
});

test("control bay provides two differently sized knobs, slider and explicit actions", () => {
    const ui = fs.readFileSync(path.join(base, "widgets/MediaDeckBrowserControls.qml"), "utf8");
    assert.match(deck, /MediaDeckBrowserControls\s*\{/);
    assert.match(ui, /id:\s*navigationDial/);
    assert.match(ui, /scale:\s*0\.77/);
    assert.match(ui, /id:\s*resultSlider/);
    assert.match(ui, /indexRequested|onIndexRequested/);
    assert.match(ui, /id:\s*tuningDial/);
    assert.match(ui, /scale:\s*1\.0/);
    assert.match(ui, /label:\s*"SELECT"/);
    assert.match(ui, /label:\s*"ENTER"/);
    assert.match(ui, /label:\s*"LOAD"/);
    assert.match(ui, /label:\s*"SEARCH"/);
    assert.match(ui, /onClicked:\s*bay\.deckHost\.selectHighlighted\(\)/);
    assert.match(ui, /onClicked:\s*bay\.deckHost\.loadStaged\(\)/);
    assert.match(ui, /onClicked:\s*bay\.deckHost\.enterHighlighted\(\)/);
    assert.doesNotMatch(ui, /issue\("play"/);
});

test("search is in the control bay and display results remain read-only", () => {
    assert.match(deck, /function searchLibrary\(\)/);
    assert.match(deck, /headless\.searchMedia\(catalogSource, query\)/);
    assert.match(deck, /readonly property var browseItems:/);
    assert.match(deck, /Flickable\s*\{/);
    assert.match(deck, /resultViewport/);
    assert.match(deck, /function tuneToGroup\(index\)/);
    assert.match(deck, /function highlightRow\(index\)/);
    assert.match(deck, /function enterHighlighted\(\)/);
    assert.match(bridge, /function loadMedia\(ref\)/);
    assert.match(bridge, /issue\("load", \["--uri", ref\.id, "--source", "local-mpd"\]\)/);
    assert.doesNotMatch(deck, /WlrKeyboardFocus\.Exclusive/);
});

test("Shift selection remains fail-closed; bare grave is reserved", () => {
    assert.match(deck, /standaloneShiftVerified:\s*false/);
    assert.match(deck, /shiftCandidate = standaloneShiftVerified/);
    assert.match(deck, /!browserControls\.searchEditing/);
    assert.match(deck, /event\.modifiers !== Qt\.NoModifier/);
    assert.match(deck, /event\.key === Qt\.Key_Return/);
    assert.doesNotMatch(deck, /Qt\.Key_QuoteLeft|Qt\.Key_AsciiTilde/);
});

test("radio cassette is display-only; its SELECT and LOAD are on the bay", () => {
    const ui = fs.readFileSync(path.join(base, "widgets/MediaDeckBrowserControls.qml"), "utf8");
    assert.match(deck, /catalogSource === "direct-stream"/);
    assert.match(deck, /headless\.loadRadio\(radioStreamUrl\)/);
    assert.match(deck, /function selectHighlighted\(\)/);
    assert.match(bridge, /ref\.source !== "direct-stream"/);
    assert.match(ui, /label: bay\.deckHost\.catalogSource === "youtube"/);
    assert.match(ui, /bay\.controller\.selection\.source === "direct-stream"/);
    assert.doesNotMatch(deck, /id:\s*grooveMouse/);
});
