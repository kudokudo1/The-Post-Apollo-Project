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

// WeatherStationW owns the transient cross-loader snapshot.
assert.match(station, /property var newsMapOverlay: null/);
assert.match(
    station,
    /onNewsMapRequested: function\(payload\)[\s\S]*?newsMapOverlay[\s\S]*?JSON\.parse\(JSON\.stringify\(payload\)\)/
);
assert.match(
    station,
    /weatherStation\.currentView = "map"/
);
assert.match(
    station,
    /StationDiscovery\s*\{[\s\S]*?domain: "map"[\s\S]*?newsMentionOverlay: weatherStation\.newsMapOverlay/
);
assert.match(
    station,
    /onNewsMapClearRequested:[\s\S]*?weatherStation\.newsMapOverlay = null/
);

// MAP treats GKG mentions as a separate visual/semantic layer.
assert.match(discovery, /property var newsMentionOverlay: null/);
assert.match(discovery, /readonly property var mapNewsMentionRows:/);
assert.match(discovery, /MapProjection\.plottable\(/);
assert.match(discovery, /function focusNewsMentions\(\)/);
assert.match(discovery, /MapProjection\.fitRows\(mapNewsMentionRows, 1\.35\)/);
assert.match(discovery, /model: stationDiscovery\.mapNewsMentionRows/);
assert.match(discovery, /color: Colors\.magenta/);
assert.match(discovery, /selectedMapNewsMention = modelData/);
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
