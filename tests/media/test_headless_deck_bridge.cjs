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
    assert.match(deck, /headless\.loadRadio\(item\.ref\.id\)/);
    assert.match(deck, /headless\.loadMedia\(item\.ref\)/);
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
    assert.match(bridge, /issue\("load", \["--uri", ref\.id, "--source", ref\.source\]\)/);
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
    assert.match(deck, /headless\.loadRadio\(item\.ref\.id\)/);
    assert.match(deck, /headless\.loadMedia\(item\.ref\)/);
    assert.match(deck, /function selectHighlighted\(\)/);
    assert.match(bridge, /ref\.source !== "direct-stream"/);
    assert.match(ui, /label: bay\.deckHost\.catalogSource === "youtube"/);
    assert.match(ui, /bay\.controller\.selection\.source === "direct-stream"/);
    assert.doesNotMatch(deck, /id:\s*grooveMouse/);
});

test("analog controls follow slider, horizontal dial, actions, tune dial order", () => {
    const ui = fs.readFileSync(path.join(base, "widgets/MediaDeckBrowserControls.qml"), "utf8");
    const parts = [
        "id: resultSlider", "id: navigationDial",
        "id: mediaActionColumn", "id: tuningDial"
    ];
    const offsets = parts.map(id => ui.indexOf(id));
    assert.ok(offsets.every(offset => offset !== -1));
    assert.ok(offsets.every((offset, i) => i === 0 || offset > offsets[i - 1]));
    assert.match(ui, /id:\s*resultSlider[\s\S]*?width:\s*40/);
    assert.match(ui, /id:\s*navigationDial[\s\S]*?scale:\s*0\.77/);
    assert.match(ui, /id:\s*tuningDial[\s\S]*?scale:\s*1\.0/);
    assert.match(ui, /navigationRig\.width - 40 - 110 - 150/);
});

test("SEARCH and source button positions are swapped, input uses magenta and orange caret", () => {
    const ui = fs.readFileSync(path.join(base, "widgets/MediaDeckBrowserControls.qml"), "utf8");
    assert.match(ui, /id:\s*searchKey[\s\S]*?anchors \{ left: parent\.left/);
    assert.match(ui, /id:\s*sourceKey[\s\S]*?anchors \{ right: parent\.right/);
    assert.match(ui, /left: searchKey\.right; right: sourceKey\.left/);
    assert.match(ui, /id:\s*queryBezel[\s\S]*?border\.color:\s*Colors\.magenta/);
    assert.match(ui, /id:\s*searchInput[\s\S]*?color:\s*Colors\.magenta/);
    assert.match(ui, /cursorDelegate:\s*Rectangle\s*\{[\s\S]*?color:\s*Colors\.orange/);
    assert.match(ui, /GohuText\s*\{[\s\S]*?GROOVE SALAD \/ PRESET[\s\S]*?color:\s*Colors\.magenta/);
});

test("browser action controls retain ordinary ActionButton variants", () => {
    const ui = fs.readFileSync(path.join(base, "widgets/MediaDeckBrowserControls.qml"), "utf8");
    assert.equal((ui.match(/ActionButton\s*\{/g) || []).length, 6);
    assert.doesNotMatch(ui, /selected:\s*bay\.deckHost\.navigationZone/);
    assert.doesNotMatch(ui, /destructive:\s*true|variant:\s*"special"/);
    assert.match(ui, /id:\s*sourceKey[\s\S]*?onClicked:\s*bay\.deckHost\.toggleCatalogSource/);
    assert.match(ui, /id:\s*searchKey[\s\S]*?onClicked:\s*bay\.deckHost\.searchLibrary/);
});

test("radio directory supports paging and station-specific guarded loading", () => {
    const ui = fs.readFileSync(path.join(base, "widgets/MediaDeckBrowserControls.qml"), "utf8");
    assert.match(deck, /catalogSource === "radio-browser"/);
    assert.match(deck, /function nextRadioPage\(\)/);
    assert.match(deck, /headless\.searchMedia\("radio-browser", browserControls\.queryText, nextBrowseCursor\)/);
    assert.match(deck, /headless\.loadRadio\(item\.ref\.id\)/);
    assert.match(deck, /headless\.loadMedia\(item\.ref\)/);
    assert.match(deck, /headless\.browse\.nextCursor/);
    assert.match(ui, /label: "NEXT 50"/);
    assert.match(ui, /onClicked: bay\.deckHost\.nextRadioPage\(\)/);
    assert.match(ui, /label: bay\.deckHost\.catalogSource === "youtube"/);
    assert.match(bridge, /source !== "radio-browser"/);
    assert.match(bridge, /ref\.source !== "radio-browser"/);
    assert.match(bridge, /issue\("load", \["--uri", ref\.id, "--source", ref\.source\]\)/);
});


test("Weather RADIO opts into shared Hi-Fi client scope without new playback owner", () => {
    const radio = fs.readFileSync(path.join(base, "widgets/weather/StationRadio.qml"), "utf8");
    const weather = fs.readFileSync(path.join(base, "widgets/weather/WeatherStationW.qml"), "utf8");
    assert.match(bridge, /property string radioClient:\s*"default"/);
    assert.match(bridge, /radioClient === "default"[\s\S]*?issue\("snapshot", \[\]\)/);
    assert.match(bridge, /issue\("snapshot", \["--client", radioClient\]\)/);
    assert.match(bridge, /if \(source === "radio-browser" && radioClient !== "default"\)[\s\S]*?args\.push\("--client", radioClient\)/);
    assert.match(bridge, /if \(ref\.source === "radio-browser" && radioClient !== "default"\)[\s\S]*?args\.push\("--client", radioClient\)/);
    assert.match(bridge, /return issue\("load", \["--client", radioClient\]\)/);
    assert.match(bridge, /"load", \["--uri", ref\.id, "--source", ref\.source,[\s\S]*?"--client", radioClient\]/);
    assert.match(bridge, /interval:\s*bridge\.pollingInterval/);
    assert.match(radio, /MediaServices\.HeadlessMediaController\s*\{[\s\S]*?radioClient:\s*"weather-radio"/);
    assert.match(radio, /polling:\s*stationRadio\.stationOpen && stationRadio\.visible/);
    assert.match(radio, /function broadcastTag\(item\)/);
    assert.match(radio, /color:\s*Colors\.magenta/);
    assert.match(radio, /tag:news/);
    assert.match(radio, /tag:talk/);
    assert.match(radio, /country:US/);
    assert.match(radio, /function selectHighlighted\(\)/);
    assert.match(radio, /function loadSelection\(\)/);
    assert.match(radio, /function enterHighlighted\(\)/);
    assert.match(radio, /function playbackAction\(action\)/);
    assert.match(radio, /lastLoadRequestedId !== ""/);
    assert.match(radio, /stationRadio\.canTransport/);
    assert.doesNotMatch(radio, /StationDiscoveryService|Qt\.openUrlExternally|--autoplay|mpc |systemctl/);
    assert.match(weather, /id: radioViewComponent[\s\S]*?StationRadio\s*\{/);
    assert.doesNotMatch(weather, /domain:\s*"radio"/);
    assert.match(weather, /id: mapViewComponent[\s\S]*?domain:\s*"map"/);
    assert.match(weather, /id: newsViewComponent[\s\S]*?domain:\s*"news"/);
});
