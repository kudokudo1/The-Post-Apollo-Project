"use strict";

// M28-U // Draft-only CLASSIC-free navigation rehearsal.
// Source-level admission proof, not Fedora/Sway/Kitty or operator acceptance.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");
const station = read("widgets/weather/WeatherStationW.qml");
const defaultSource = read("widgets/weather/StationSubjectDefaultPolicy.js");
const navigationSource = read("widgets/weather/StationSubjectNavigationPolicy.js");
const previewSource = read("widgets/weather/StationSubjectNavigationPreviewPolicy.js");
const surface = read("widgets/weather/StationWorkspaceSurface.qml");
const navigator = read("widgets/weather/StationSubjectNavigator.qml");
const policy = vm.createContext({});
vm.runInContext(defaultSource.replace(/^\.pragma library\s*$/m, ""), policy);
const routes = vm.createContext({});
for (const source of [navigationSource, previewSource])
  vm.runInContext(source.replace(/^\.pragma library\s*$/m, ""), routes);

test("M28-U candidate is explicitly reversible and all 103 M0 controls have native destinations", () => {
  assert.equal(policy.CLASSIC_RETIREMENT_PREVIEW, true);
  assert.equal(policy.SUBJECTS_FIRST_PILOT, true);
  assert.equal(policy.onOpen(true), true);
  assert.equal(policy.onClose(true), false);
  assert.equal(Object.keys(routes.PANELS).length, 103);
  assert.equal(Object.keys(routes.WIRED_IN_SUBJECTS).length, 103);
  assert.deepEqual(
    Object.keys(routes.PANELS).filter(id => !Object.prototype.hasOwnProperty.call(routes.WIRED_IN_SUBJECTS, id)),
    []
  );
  for (const family of ["weather", "cosmos", "earth", "media", "magick", "tools"]) {
    assert.equal(routes.remainingSourcePagesForPath(family, routes.PANELS).length, 0, family);
  }
});

test("the CLASSIC rail and deep INDEX bridges are inaccessible in the preview", () => {
  assert.match(station, /id: subjectBrowserToggle[\s\S]*?visible: !SubjectDefaultPolicy\.CLASSIC_RETIREMENT_PREVIEW/);
  assert.match(station, /function switchToClassic\(\)\s*\{[\s\S]*?if \(SubjectDefaultPolicy\.CLASSIC_RETIREMENT_PREVIEW\)\s*return false;/);
  assert.match(station, /function openLegacyFromSubject\(pageId\)\s*\{[\s\S]*?if \(SubjectDefaultPolicy\.CLASSIC_RETIREMENT_PREVIEW\)\s*return false;/);
  assert.match(station, /function open\(\)\s*\{[\s\S]*?if \(SubjectDefaultPolicy\.CLASSIC_RETIREMENT_PREVIEW\s*&& terminalView\.terminalState !== "IDLE"\)\s*return;/);
  assert.match(station, /subjectNavigationOpen = SubjectDefaultPolicy\.onOpen\(subjectsFirstPilotEnabled\)/);
  assert.match(station, /onLegacyPageRequested: function\(pageId\)\s*\{\s*weatherStation\.openLegacyFromSubject\(pageId\);/);
  assert.match(navigator, /model: browser\.nativeDestinations/);
});

test("all original presentation engines remain real SUBJECTS dependencies", () => {
  for (const engine of ["StationHome", "StationGround", "StationSky", "StationSpace",
    "StationDiscovery", "StationNewsHub", "StationRadio"]) {
    assert.match(
      surface + read("widgets/weather/StationWeatherSubjectPane.qml")
      + read("widgets/weather/StationCosmosSubjectPane.qml")
      + read("widgets/weather/StationEarthSubjectPane.qml")
      + read("widgets/weather/StationMediaSubjectPane.qml"),
      new RegExp(engine + "\\s*\\{"), engine
    );
  }
  for (const p of [
    ["widgets/weather/StationWeatherSubjectPanelPolicy.js", "weather/ground/full"],
    ["widgets/weather/StationCosmosSubjectPanelPolicy.js", "cosmos/space-weather/full"],
    ["widgets/weather/StationEarthSubjectPanelPolicy.js", "earth/maps/full"],
    ["widgets/weather/StationMediaSubjectPanelPolicy.js", "media/news/full"],
    ["widgets/weather/StationMediaSubjectPanelPolicy.js", "media/radio/full"]
  ]) assert.ok(read(p[0]).includes(p[1]), p[1]);
});

test("single root data writers and Kitty actor remain intact", () => {
  for (const owner of [
    "WeatherServices.CelestialVisualService",
    "WeatherServices.WeatherHomeFavoritesStore",
    "WeatherServices.WeatherHistoryService",
    "WeatherServices.SeismicService",
    "WeatherServices.NowcoastLightningService",
    "WeatherServices.NwpsRiverService"
  ]) assert.equal(station.split(owner + " {").length - 1, 1, owner);
  assert.equal((station.match(/StationTerminal\s*\{/g) || []).length, 1);
  assert.match(station, /terminalHoleX: modeRail\.width \+ terminalView\.visibleBayX/);
  assert.match(station, /stationRailWidth: modeRail\.width/);
  assert.match(surface, /StationHome\s*\{/);
  assert.match(surface, /StationMediaSubjectPane\s*\{/);
  assert.match(read("widgets/weather/StationChannelScreen.qml"),
    /readonly property bool playbackAvailable: false/);
});