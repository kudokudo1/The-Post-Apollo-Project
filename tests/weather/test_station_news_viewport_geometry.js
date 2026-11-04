#!/usr/bin/env node
"use strict";
// Source-contract tests: assert authoritative QML measurements are used.
// These do not claim actual compositor coordinates or live browser rendering.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");

const station = read("widgets/weather/WeatherStationW.qml");
const hub = read("widgets/weather/StationNewsHub.qml");
const screen = read("widgets/weather/StationChannelScreen.qml");
const hostPolicy = read("MODEL/stage-director-weather-station-host-bridge-20261025.md");

assert.match(station, /^import Quickshell.Wayland$/m);
assert.equal(
    (station.match(/WlrLayershell\.namespace:/g) || []).length, 1,
    "the Weather layer must have one static, explicit namespace"
);
assert.match(station,
    /WlrLayershell\.namespace:\s*"post-apollo-weather-station"/);
assert.match(station, /WlrLayershell\.layer:\s*WlrLayer\.Overlay/);
// M28-V retires the inaccessible CLASSIC NEWS loader and its unused
// station-root player geometry. MEDIA retains the original local viewport,
// but no browser host is authorized or activated by this source cleanup.
const media = read("widgets/weather/StationMediaSubjectPane.qml");
assert.match(station,/StationSubjectNavigator\s*\{/);
assert.match(media,/StationNewsHub\s*\{/);
assert.ok(!station.includes("newsViewerViewportRect"));
assert.ok(!station.includes("newsViewerGeometryValid"));
assert.ok(!station.includes("newsSourceItem"));

assert.match(hub, /readonly property rect playerViewportRect:/);
assert.match(hub, /const screen = channelScreenLoader\.item;/);
assert.match(hub, /if \(!stationOpen \|\| !viewerOpen \|\| !screen\)/);
assert.match(hub, /screen\.mapToItem\(stationNewsHub, bay\.x, bay\.y\)/);
assert.match(hub, /id: channelScreenLoader/);
assert.match(hub, /active: stationNewsHub\.viewerOpen/);
assert.match(hub, /onCloseRequested: stationNewsHub\.closeViewer\(\)/);

assert.match(screen, /readonly property rect playerViewportRect:/);
assert.match(screen, /Qt\.rect\(playerBay\.x, playerBay\.y, playerBay\.width, playerBay\.height\)/);
assert.match(screen, /id: playerBay/);
assert.match(screen, /anchors\.top: titleStrip\.bottom/);
assert.match(screen, /anchors\.bottom: footerStrip\.top/);
assert.match(screen, /readonly property bool playbackAvailable: false/);
assert.match(hostPolicy, /Candidate identity is not authorization/);

// Do not add a second geometry poller or use fixed terminal-bay numbers.
// QML item ownership determines logical geometry; SwayPX supplies globals.
const joined = station + hub + screen;
assert.doesNotMatch(joined, /^import QtWebEngine$/m);
assert.doesNotMatch(joined, /source:\s*["']StationNewsWebView\.qml/);
assert.doesNotMatch(joined, /Qt\.openUrlExternally\(|startDetached\(/);
assert.doesNotMatch(
    hub + screen,
    /Qt\.rect\(190\s*,\s*132|Qt\.rect\(0\s*,\s*0\s*,\s*824\s*,\s*494/
);
console.log("Weather NEWS safe-mode native MEDIA viewport geometry: PASS");
