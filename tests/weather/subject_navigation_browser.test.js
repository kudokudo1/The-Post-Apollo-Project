"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const navSource = fs.readFileSync(path.join(root, "widgets/weather/StationSubjectNavigationPolicy.js"), "utf8");
const previewSource = fs.readFileSync(path.join(root, "widgets/weather/StationSubjectNavigationPreviewPolicy.js"), "utf8");
const uiSource = fs.readFileSync(path.join(root, "widgets/weather/StationSubjectNavigator.qml"), "utf8");
const railSource = fs.readFileSync(path.join(root, "widgets/weather/StationSubjectRail.qml"), "utf8");
const stationSource = fs.readFileSync(path.join(root, "widgets/weather/WeatherStationW.qml"), "utf8");

const env = vm.createContext({});
vm.runInContext(navSource.replace(/^\.pragma library\s*$/m,""), env, {filename:"StationSubjectNavigationPolicy.js"});
vm.runInContext(previewSource.replace(/^\.pragma library\s*$/m,""), env, {filename:"StationSubjectNavigationPreviewPolicy.js"});
const plain = value => JSON.parse(JSON.stringify(value));

test("M0 remains a six-subject hierarchy with actual nested routes", () => {
  assert.deepEqual(plain(env.SUBJECTS.map(s => s.id)),
    ["weather","cosmos","earth","media","magick","tools"]);
  assert.equal(env.findRoute("weather/water/rivers/hydrograph").depth, 3);
  assert.equal(env.findRoute("cosmos/space-weather/aurora").subject, "cosmos");
  assert.equal(env.findRoute("magick/astrology/retrogrades").status, "SPEC_ONLY");
});

test("source browser distinguishes original legacy pages from new routes", () => {
  assert.deepEqual(plain(env.sourcePagesForPath("weather", env.PANELS).map(x => x.id)),
    ["home","ground","sky","map"]);
  assert.deepEqual(plain(env.sourcePagesForPath("cosmos", env.PANELS).map(x => x.id)),
    ["home","sky","space"]);
  assert.deepEqual(plain(env.sourcePagesForPath("earth", env.PANELS).map(x => x.id)),
    ["ground","map"]);
  assert.deepEqual(plain(env.sourcePagesForPath("media", env.PANELS).map(x => x.id)),
    ["map","news","radio"]);
  assert.deepEqual(plain(env.sourcePagesForPath("magick", env.PANELS)), []);
  assert.deepEqual(plain(env.sourcePagesForPath("tools/terminal", env.PANELS).map(x => x.id)),
    ["terminal"]);
});

test("specific mixed panels expose correct classic page without cross-subject claims", () => {
  assert.deepEqual(plain(env.sourcePagesForPath("weather/forecasts/hourly", env.PANELS).map(x => x.id)),
    ["home","sky"]);
  assert.deepEqual(plain(env.sourcePagesForPath("weather/water/rivers", env.PANELS).map(x => x.id)),
    ["ground"]);
  assert.deepEqual(plain(env.sourcePagesForPath("cosmos/moon/ephemeris", env.PANELS).map(x => x.id)),
    ["sky"]);
  assert.deepEqual(plain(env.sourcePagesForPath("earth/geology/earthquakes", env.PANELS).map(x => x.id)),
    ["ground","map"]);
  assert.deepEqual(plain(env.sourcePagesForPath("media/news/locations", env.PANELS).map(x => x.id)),
    ["map"]);
  assert.deepEqual(plain(env.sourcePagesForPath("weather/maps/radar", env.PANELS).map(x => x.id)),
    ["map"]);
});

test("source page normalization is explicit and rejects malformed paths", () => {
  assert.equal(env.legacyPageForPanel("ground-river-nwps"), "ground");
  assert.equal(env.legacyPageForPanel("station-event-store"), "");
  assert.equal(env.legacyPageForPanel(null), "");
  for (const value of [null,{},[], "weather//maps", "../weather","weather?q=1","WEATHER"])
    assert.deepEqual(plain(env.sourcePagesForPath(value, env.PANELS)), []);
  assert.deepEqual(plain(env.sourcePagesForPath("weather", null)), []);
});

test("browser is opt-in, names preview status, and explicitly links CLASSIC", () => {
  assert.match(stationSource,/property bool subjectNavigationOpen: false/);
  assert.match(stationSource,/StationSubjectNavigator\s*\{/);
  assert.match(stationSource,/visible: weatherStation\.subjectNavigationOpen/);
  assert.match(stationSource,/onLegacyPageRequested: function\(pageId\)/);
  assert.match(stationSource,/function openLegacyFromSubject\(pageId\)/);
  assert.match(stationSource,/if \(subjectNavigationOpen\)\s*\{\s*subjectNavigator\.cycleSubjects/);
  assert.match(stationSource,/subjectNavigator\.moveCursor\(direction\)/);
  assert.match(stationSource,/subjectNavigator\.activateCursor\(\)/);
  assert.match(stationSource,/SubjectSourceBadge\.badgeFor\(/);
  assert.match(stationSource,/subjectNavigator\.indexOpen/);
  assert.ok(stationSource.includes("StationSubjectRail {"));
  assert.equal(stationSource.split("ModeButton {").length - 1, 1);
  assert.equal(railSource.split("ModeButton {").length - 1, 1);
  assert.match(uiSource,/SPEC-ONLY SUBJECTS/);
  assert.match(uiSource,/CLASSIC PAGES REMAIN CANONICAL/);
});

test("existing source owners, legacy mode ids and terminal lifecycle stay present", () => {
  for (const oldId of ["home","ground","sky","space","map","news","radio","terminal"])
    assert.match(stationSource, new RegExp('\\\"id\\\": \\\"' + oldId + '\\\"'));
  for (const sourceId of ["WeatherServices.WeatherHistoryService",
                          "WeatherServices.SeismicService",
                          "WeatherServices.NowcoastLightningService",
                          "WeatherServices.NwpsRiverService",
                          "StationTerminal {",
                          "onNewsMapRequested: function(payload)"])
    assert.ok(stationSource.includes(sourceId), sourceId);
  assert.match(stationSource,/terminalView\.terminalState !== "IDLE"/);
  assert.match(stationSource,/if \(currentView === "terminal"\)/);
  assert.match(stationSource,/if \(!menuOpen \|\| subjectNavigationOpen/);
  assert.match(stationSource,/onCurrentViewChanged:\s*\{\s*subjectNavigationOpen = false;/);
});

test("browser has no independent network/process or file IO", () => {
  for (const marker of ["Process {","FileView {","Curl","HttpRequest","new XMLHttpRequest",
                        "swaymsg","Qt.callLater","Quickshell.Io"]) {
    assert.ok(!uiSource.includes(marker), "browser contains forbidden IO: " + marker);
    assert.ok(!previewSource.includes(marker), "preview policy contains forbidden IO: " + marker);
  }
});
