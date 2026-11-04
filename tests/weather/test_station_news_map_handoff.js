#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "../..");
const read = rel => fs.readFileSync(path.join(root, rel), "utf8");

const viewer = read("widgets/weather/StationViewerHost.qml");
const discovery = read("widgets/weather/StationDiscovery.qml");
const hub = read("widgets/weather/StationNewsHub.qml");
const station = read("widgets/weather/WeatherStationW.qml");

// Viewer only exposes the handoff after a successful location lookup.
assert.match(viewer, /signal showOnMapRequested\(\)/);
assert.match(viewer, /label: "SHOW ON MAP"/);
assert.match(
    viewer,
    /available: stationViewer\.locationReady[\s\S]*?stationViewer\.locationRows\.length > 0/
);
assert.match(viewer, /onClicked: stationViewer\.showOnMapRequested\(\)/);

// NEWS snapshots the GKG rows before the NEWS loader can be destroyed.
assert.match(discovery, /signal newsMapRequested\(var payload\)/);
assert.match(discovery, /function requestNewsMapHandoff\(\)/);
assert.match(
    discovery,
    /JSON\.parse\([\s\S]*?JSON\.stringify\(articleLocationService\.rows\)/
);
assert.match(discovery, /"articleTitle": String\(selectedNews\.title/);
assert.match(discovery, /"gkgSliceUtc": String\(articleLocationService\.sliceUtc/);
assert.match(discovery, /"locations": copiedRows/);
assert.match(
    discovery,
    /onShowOnMapRequested:[\s\S]*?stationDiscovery\.requestNewsMapHandoff\(\)/
);

// The reports hub forwards the payload without owning cross-mode state.
assert.match(hub, /signal newsMapRequested\(var payload\)/);
assert.match(
    hub,
    /onNewsMapRequested: function\(payload\)[\s\S]*?stationNewsHub\.newsMapRequested\(payload\)/
);

// SUBJECTS Navigator owns the transient NEWS -> EARTH overlay.
const navigator = read("widgets/weather/StationSubjectNavigator.qml");
const earthPane = read("widgets/weather/StationEarthSubjectPane.qml");
assert.match(navigator,/property var newsMentionOverlay: null/);
assert.match(navigator,/function showNewsMentionsOnEarth\(payload\)/);
assert.match(navigator,/MapProjection\.plottable\(payload\.locations\)/);
assert.match(navigator,/chooseRoute\("earth\/maps\/overview"\)/);
assert.match(navigator,/newsMentionOverlay = incoming/);
assert.match(navigator,/function clearNewsMentions\(\)/);
assert.match(earthPane,/newsMentionOverlay: earthPane\.newsMentionOverlay/);
assert.ok(!station.includes("newsMapOverlay"));
assert.ok(!station.includes("currentView"));

// MAP treats GKG mentions as a separate visual/semantic layer.
assert.match(discovery, /property var newsMentionOverlay: null/);
assert.match(discovery, /readonly property var mapNewsMentionRows:/);
assert.match(discovery, /MapProjection\.plottable\(/);
assert.match(discovery, /function focusNewsMentions\(\)/);
assert.match(discovery, /MapProjection\.fitRows\(mapNewsMentionRows, 1\.35\)/);
assert.match(discovery, /model: stationDiscovery\.mapNewsMentionRows/);
assert.match(discovery, /color: Colors\.magenta/);
// The original map marker and the compact EARTH mention list now share
// one inspector action instead of duplicating its selection mutation.
assert.match(discovery, /stationDiscovery\.inspectNewsMention\(modelData\)/);
assert.match(discovery, /function inspectNewsMention\(row\)/);
assert.match(discovery, /selectedMapNewsMention = row/);
assert.match(discovery, /NEWS MENTION INSPECTOR \/\/ GDELT GKG/);
assert.match(discovery, /MENTIONED LOCATION \/\/ NOT VERIFIED EVENT LOCATION/);
assert.match(discovery, /NEWS → MAP LOCATION HANDOFF", state:"CONNECTED"/);

// The handoff remains local. It must not add another fetch owner.
const handoffArea = discovery.slice(
    discovery.indexOf("function requestNewsMapHandoff()"),
    discovery.indexOf("function fetchVisibleHotspots()")
);
assert.doesNotMatch(
    handoffArea,
    /Process\s*\{|Timer\s*\{|curl|XMLHttpRequest|Qt\.openUrlExternally/
);

const workflow = read(".github/workflows/weather-teardown-contracts.yml");
assert.match(
    workflow,
    /node tests\/weather\/test_station_news_map_handoff\.js/
);

console.log("Weather NEWS mentioned-location MAP handoff: PASS");
