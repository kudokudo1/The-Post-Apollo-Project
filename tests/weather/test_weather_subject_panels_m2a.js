"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");
const policySource = read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const routeSource = read("widgets/weather/StationSubjectNavigationPolicy.js");
const ground = read("widgets/weather/StationGround.qml");
const sky = read("widgets/weather/StationSky.qml");
const pane = read("widgets/weather/StationWeatherSubjectPane.qml");
const nav = read("widgets/weather/StationSubjectNavigator.qml");
const station = read("widgets/weather/WeatherStationW.qml");
const env = vm.createContext({});
vm.runInContext(routeSource.replace(/^\.pragma library\s*$/m, ""), env);
vm.runInContext(policySource.replace(/^\.pragma library\s*$/m, ""), env);
const plain = value => JSON.parse(JSON.stringify(value));

test("13 real WEATHER routes belong to the existing M0 subject hierarchy", () => {
  const keys = Object.keys(env.ROUTES);
  assert.equal(keys.length, 13);
  for (const key of keys) {
    const route = env.findRoute(key);
    assert.ok(route, key);
    assert.equal(route.subject, "weather");
    assert.equal(route.group, key === "weather/water/rivers", key);
    const page = env.kindForRoute(key);
    assert.ok(page === "sky" || page === "ground", key);
    assert.ok(env.visibleFor(page,key,"header"),key);
    assert.match(env.titleFor(key), /^WEATHER \/\//);
  }
  assert.equal(env.kindForRoute("weather/overview"), "");
  assert.equal(env.kindForRoute("weather/maps/radar"), "");
  assert.equal(env.kindForRoute("weather/water/rivers/gauges"), "");
  assert.equal(env.kindForRoute("magick/astrology/charts"), "");
});

test("section filtering keeps exact CLASSIC presentation by default", () => {
  for (const [name,source] of [["ground",ground],["sky",sky]]) {
    assert.match(source,/property string subjectRoute: ""/);
    assert.match(source,/function sectionVisible\(section\)/);
    const keys = [...source.matchAll(/sectionVisible\("([^"]+)"\)/g)].map(x => x[1]);
    assert.equal(keys.length,name === "ground" ? 32 : 27);
    for (const key of keys)
      assert.equal(env.visibleFor(name,"",key),true,name+"/"+key);
  }
  assert.equal(env.needsSource("","marine"),true);
  assert.equal(env.needsSource("","coastal"),true);
  assert.equal(env.needsSource("","astronomy"),true);
  assert.equal(env.needsSource("","river"),true);
  assert.equal(env.needsSource("","lightning"),true);
});

test("selected WEATHER routes show only their own sections", () => {
  assert.equal(env.visibleFor("sky","weather/conditions/current","current"),true);
  assert.equal(env.visibleFor("sky","weather/conditions/current","astronomy"),false);
  assert.equal(env.visibleFor("sky","weather/forecasts/hourly","hourly"),true);
  assert.equal(env.visibleFor("sky","weather/forecasts/hourly","daily"),false);
  assert.equal(env.visibleFor("ground","weather/conditions/air","air-pm"),true);
  assert.equal(env.visibleFor("ground","weather/conditions/air","air-gases"),true);
  assert.equal(env.visibleFor("ground","weather/conditions/air","seismic"),false);
  assert.equal(env.visibleFor("ground","weather/conditions/pollen","pollen"),true);
  assert.equal(env.visibleFor("ground","weather/water/rivers","rivers"),true);
  assert.equal(env.visibleFor("ground","weather/water/marine","marine"),true);
  assert.equal(env.visibleFor("ground","weather/water/marine","coast"),false);
  assert.equal(env.visibleFor("ground","weather/hazards/lightning","lightning"),true);
  assert.equal(env.visibleFor("ground","weather/hazards/lightning","heat-fire"),false);
  assert.equal(env.visibleFor("ground","weather/hazards/heat-fire","heat-fire"),true);
  assert.equal(env.visibleFor("ground","weather/hazards/alerts","alerts"),true);
  assert.equal(env.visibleFor("ground","weather/forecasts/air","air-forecast"),true);
});

test("provider activation matches only relevant routes and preserves old collectors", () => {
  for (const key of Object.keys(env.ROUTES)) {
    assert.equal(env.needsSource(key,"astronomy"),false,key);
    assert.equal(env.needsSource(key,"river"),key === "weather/water/rivers");
    assert.equal(env.needsSource(key,"lightning"),key === "weather/hazards/lightning");
    assert.equal(env.needsSource(key,"marine"),key === "weather/water/marine");
    assert.equal(env.needsSource(key,"coastal"),key === "weather/water/coast");
  }
  assert.equal((sky.match(/SubjectPanelPolicy\.needsSource\(sky\.subjectRoute,"astronomy"\)/g)||[]).length,6);
  for (const s of ["marine","coastal"])
    assert.ok(ground.includes('SubjectPanelPolicy.needsSource(ground.subjectRoute,"'+s+'")'));
  for (const s of ["river","lightning"])
    assert.ok(station.includes('subjectNavigator.currentPath, "'+s+'"'));
  assert.match(station,/!weatherStation\.subjectNavigationOpen\s*&& \(weatherStation\.currentView === "ground"/);
  assert.match(station,/active: weatherStation\.menuOpen\s*&& !weatherStation\.subjectNavigationOpen\s*&& weatherStation\.currentView === "home"/);
  assert.ok(!pane.includes("WeatherServices."));
});

test("one live subject pane uses the already-wired shared sources", () => {
  for (const token of [
    "StationGround {","StationSky {","subjectRoute: weatherPane.subjectRoute",
    "weatherService: weatherPane.weatherService",
    "nwsAlertSource: weatherPane.nwsAlertSource",
    "seismicSource: weatherPane.seismicSource",
    "lightningSource: weatherPane.lightningSource",
    "riverSource: weatherPane.riverSource",
    "persistentCacheStore: weatherPane.persistentCacheStore",
    "liveHistoryStore: weatherPane.liveHistoryStore",
    'active: weatherPane.visible && weatherPane.kind !== ""'
  ]) assert.ok(pane.includes(token),token);
  for (const token of [
    "StationWeatherSubjectPane {",
    "visible: browser.visible && browser.liveWeatherKind !==",
    "subjectRoute: browser.currentPath",
    "weatherService: browser.weatherService",
    "nwsAlertSource: browser.nwsAlertSource",
    "riverSource: browser.riverSource",
    'visible: browser.liveWeatherKind === ""'
  ]) assert.ok(nav.includes(token),token);
  for (const token of [
    "weatherService: weatherStation.weatherService",
    "nwsAlertSource: weatherStation.nwsAlertSource",
    "seismicSource: seismicService",
    "lightningSource: lightningService",
    "riverSource: riverService",
    "persistentCacheStore: weatherStation.persistentCacheStore",
    "liveHistoryStore: weatherStation.liveHistoryStore",
    'property bool subjectNavigationOpen: false'
  ]) assert.ok(station.includes(token),token);
});

test("no premature MAP or MAGICK activation and no new persistence writer", () => {
  assert.deepEqual(plain(Object.keys(env.ROUTES).filter(x=>!x.startsWith("weather/"))),[]);
  assert.equal(env.kindForRoute("earth/geology/earthquakes"),"");
  for (const t of ["Process {","FileView {","Qt.callLater","fetch(","XMLHttpRequest","swaymsg"])
    assert.ok(!policySource.includes(t),"policy "+t);
  assert.ok(!pane.includes("eventArchiveStore"));
  assert.ok(!pane.includes("dossierArchiveStore"));
  assert.match(station,/weatherStation\.currentView === "map"/);
  assert.match(nav,/SPEC-ONLY SUBJECTS/);
});

test("route header reveals correct scope without claiming live provider success", () => {
  assert.match(ground,/subjectRoute === ""/);
  assert.match(ground,/: "⌁  WEATHER"/);
  assert.match(sky,/subjectRoute === ""/);
  assert.match(sky,/: "☁  WEATHER"/);
  assert.match(station,/return "WEATHER \/\/ PANEL"/);
  assert.match(station,/return "INDEX \/\/ PREVIEW"/);
  assert.match(nav,/WEATHER \/\/ EXISTING SOURCE PANELS \/\/ SAME COLLECTORS/);
});
