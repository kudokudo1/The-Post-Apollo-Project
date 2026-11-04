"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root, p), "utf8");
const navSource = read("widgets/weather/StationSubjectNavigationPolicy.js");
const policySource = read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const home = read("widgets/weather/StationHome.qml");
const discovery = read("widgets/weather/StationDiscovery.qml");
const ground = read("widgets/weather/StationGround.qml");
const sky = read("widgets/weather/StationSky.qml");
const pane = read("widgets/weather/StationWeatherSubjectPane.qml");
const surface = read("widgets/weather/StationWorkspaceSurface.qml");
const nav = read("widgets/weather/StationSubjectNavigator.qml");
const station = read("widgets/weather/WeatherStationW.qml");
const env = vm.createContext({});
vm.runInContext(navSource.replace(/^\.pragma library\s*$/m, ""), env);
vm.runInContext(policySource.replace(/^\.pragma library\s*$/m, ""), env);
const plain = x => JSON.parse(JSON.stringify(x));

test("M2b preserves its original 30 routes plus M28-Q full GROUND visual destination", () => {
  const routes = Object.keys(env.ROUTES);
  assert.equal(routes.length,31);
  assert.equal(new Set(routes).size,31);
  assert.equal(routes.filter(x=>x!=="weather/ground/full").length,30,
    "original M2b 30-route milestone remains intact");
  for (const name of routes) {
    const info = env.findRoute(name);
    assert.ok(info,"missing tree route "+name);
    assert.equal(info.subject,"weather");
    assert.ok(["ground","sky","home","map"].includes(env.kindForRoute(name)),name);
  }
  for (const p of ["cosmos/moon","earth/geology/earthquakes","media/news/reports","magick/astrology/charts"])
    assert.equal(env.kindForRoute(p),"",p);
});

test("WEATHER overview and history display selected original HOME instruments", () => {
  assert.equal(env.kindForRoute("weather/overview"),"home");
  assert.equal(env.kindForRoute("weather/history/historical-forecast"),"home");
  assert.equal(env.kindForRoute("weather/history/relationships"),"home");
  const groups = [...home.matchAll(/home\.sectionVisible\("([^"]+)"\)/g)].map(x=>x[1]);
  // W2b adds two guarded PINNED/STORE STATUS sections within RELEVANT;
  // no extra source panel or collector is introduced.
  assert.equal(groups.length,17);
  for (const section of groups)
    assert.equal(env.visibleFor("home","",section),true,"classic "+section);
  for (const section of ["header","alerts","snapshot","relevant"])
    assert.ok(env.visibleFor("home","weather/overview",section),section);
  for (const section of ["relations","history","quick","health","runtime"])
    assert.ok(!env.visibleFor("home","weather/overview",section),"overview leaks "+section);
  assert.ok(env.visibleFor("home","weather/history/historical-forecast","history"));
  assert.ok(!env.visibleFor("home","weather/history/historical-forecast","snapshot"));
  assert.ok(env.visibleFor("home","weather/history/relationships/aqi","relations"));
  assert.ok(!env.visibleFor("home","weather/history/relationships/aqi","history"));
  assert.match(home,/text: "⌂  HOME"/);
  assert.match(home,/text: "⌂  WEATHER"/);
  assert.match(home,/visible: home\.subjectRoute === ""/);
});

test("M27-A reuses the existing adaptive HOME watch and keeps the original CLASSIC panels", () => {
  assert.ok(env.visibleFor("home","weather/overview","relevant"));
  assert.ok(!env.visibleFor("home","weather/history/historical-forecast","relevant"));
  assert.ok(!env.visibleFor("home","weather/conditions/current","relevant"));
  assert.ok(!env.visibleFor("sky","weather/overview","relevant"));
  assert.match(home,/StationHomePolicy\.rankRelevant\(/);
  assert.match(home,/watchItems\s*=\s*next/);
  assert.match(home,/model:\s*home\.watchItems/);
  assert.match(home,/visible:\s*home\.sectionVisible\("relevant"\)/);
  assert.match(home,/if \(subjectRoute === "" && workspaceSection !== ""\)/);
  assert.match(pane,/spaceService:\s*null/);
  // No new duplicate ranker, fetcher, storage writer or file was added.
  for (const t of ["Process {","FileView {","XMLHttpRequest","fetch(","swaymsg"])
    assert.ok(!policySource.includes(t),"policy must stay passive "+t);
  for (const s of ["relevant","quick","health","history","runtime"])
    assert.ok(env.visibleFor("home","",s),"CLASSIC HOME "+s);
});

test("all relationship inspectors are collected within WEATHER > HISTORY", () => {
  const paths = plain(env.childrenOf("weather/history/relationships").map(x=>x.path));
  assert.deepEqual(paths,[
    "weather/history/relationships/aqi",
    "weather/history/relationships/marine",
    "weather/history/relationships/coastal",
    "weather/history/relationships/rivers"
  ]);
  assert.equal(env.kindForRoute("weather/history/relationships/marine"),"ground");
  assert.ok(env.visibleFor("ground","weather/history/relationships/marine","marine-rel"));
  assert.ok(!env.visibleFor("ground","weather/history/relationships/marine","seismic"));
  assert.ok(env.visibleFor("ground","weather/history/relationships/coastal","coastal-rel"));
  assert.ok(env.visibleFor("ground","weather/history/relationships/rivers","rivers"));
  assert.equal(env.needsSource("weather/history/relationships/marine","marine"),true);
  assert.equal(env.needsSource("weather/history/relationships/coastal","coastal"),true);
  assert.equal(env.needsSource("weather/history/relationships/rivers","river"),true);
});

test("existing river instrument stays intact under deep river routes and flood hazards", () => {
  for(const p of [
    "weather/water/rivers/gauges","weather/water/rivers/nearby",
    "weather/water/rivers/flood","weather/water/rivers/hydrograph",
    "weather/hazards/flood"
  ]) {
    assert.equal(env.kindForRoute(p),"ground");
    assert.ok(env.visibleFor("ground",p,"rivers"));
    assert.ok(env.needsSource(p,"river"));
  }
  assert.equal(env.needsSource("weather/maps/lightning","lightning"),true);
  assert.ok(env.visibleFor("ground","weather/maps/lightning","lightning"));
  assert.ok(!env.visibleFor("ground","weather/maps/lightning","seismic"));
});

test("M29-A river deep routes focus their own existing data blocks", () => {
  const routes = {
    "weather/water/rivers/gauges":"gauges",
    "weather/water/rivers/nearby":"nearby",
    "weather/water/rivers/flood":"flood",
    "weather/water/rivers/hydrograph":"hydrograph"
  };
  for (const [route, focus] of Object.entries(routes)) {
    assert.ok(env.findRoute(route),route + " navigation route");
    assert.equal(env.kindForRoute(route),"ground");
    assert.equal(env.visibleFor("ground",route,"rivers"),true);
    assert.equal(env.needsSource(route,"river"),true);
    assert.equal(env.riverFocusForRoute(route),focus);
    assert.equal(env.riverTitleFor(route),"RIVER // NOAA NWPS // "+focus.toUpperCase());
    for (const group of ["nearby","flood","hydrograph"])
      assert.equal(env.riverGroupVisible(route,group),focus===group,
        route+" / "+group);
  }
  for (const route of [
    "", "weather/water/rivers", "weather/ground/full",
    "weather/hazards/flood", "weather/history/relationships/rivers"
  ]) {
    assert.equal(env.riverFocusForRoute(route),"all",route);
    assert.equal(env.riverTitleFor(route),"RIVER // NOAA NWPS",route);
    for (const group of ["nearby","flood","hydrograph"])
      assert.equal(env.riverGroupVisible(route,group),true,
        "original combined "+route+" / "+group);
  }
  assert.equal(env.riverGroupVisible("weather/water/rivers/nearby","unknown"),false);
  assert.equal(env.needsSource("media/news/full","river"),false);
  // The focused pages gate only existing visuals, not the shared NWPS
  // fetch, gauge identity, observed/forecast origin or safety warnings.
  for (const token of [
    'title: SubjectPanelPolicy.riverTitleFor(ground.subjectRoute)',
    'ground.subjectRoute,"nearby")',
    'ground.subjectRoute,"flood")',
    'ground.subjectRoute,"hydrograph")',
    'ONLY ONE NWPS GAUGE RETURNED // NO NEARBY COMPARISON AVAILABLE',
    'NEARBY COMPARE // SAME NWPS SNAPSHOT',
    'FLOOD CONTEXT // IMPACTS + CRESTS',
    'STAGEFLOW // OBSERVED + OFFICIAL FORECAST',
    'STAGE IS RELATIVE TO THE GAUGE DATUM'
  ]) assert.ok(ground.includes(token),token);
  assert.equal(ground.split('signal routeRequested(string path)').length-1,1);
  const riverButtons=ground.slice(
    ground.indexOf('// The four deep RIVERS routes'),
    ground.indexOf('Column {\n            visible: ground.sectionVisible("rivers")')
  );
  assert.equal((riverButtons.match(/path:"weather\/water\/rivers/g)||[]).length,5);
  assert.match(riverButtons,/onTriggered: ground\.routeRequested\(modelData\.path\)/);
  assert.match(ground,/onSubjectRouteChanged:[\s\S]*?groundScroll\.contentY = 0/);
  assert.match(pane,/onRouteRequested: function\(path\) \{ weatherPane\.routeRequested\(path\); \}/);
  assert.match(surface,/onRouteRequested: function\(path\) \{ surface\.routeRequested\(path\); \}/);
  assert.match(nav,/onRouteRequested: function\(path\) \{ browser\.chooseRoute\(path\); \}/);
  assert.equal((station.match(/WeatherServices\.NwpsRiverService\s*\{/g)||[]).length,1);
});

test("historical model collector is shared and activated only for its explicit subject route", () => {
  assert.equal(env.needsSource("weather/history/historical-forecast","history"),true);
  for(const p of ["weather/overview","weather/maps","weather/history/relationships","weather/water/rivers"])
    assert.equal(env.needsSource(p,"history"),false,p);
  assert.match(station,/WeatherServices\.WeatherHistoryService/);
  assert.match(station,/subjectNavigator\.currentPath, "history"/);
  assert.match(station,/subjectNavigator\.liveHomeKind !== ""/);
  assert.match(pane,/historyService: weatherPane\.historyService/);
  assert.match(nav,/historyService: browser\.historyService/);
  assert.match(station,/historyService: weatherHistoryService/);
  assert.match(pane,/spaceService: null/);
});

test("WEATHER maps reuse the one CLASSIC map engine with distinct weather layers", () => {
  for(const p of ["weather/maps","weather/maps/radar","weather/maps/radar-fallback","weather/maps/smoke"])
    assert.equal(env.kindForRoute(p),"map");
  assert.match(pane,/StationDiscovery\s*\{/);
  assert.match(pane,/weatherMapOnly: true/);
  assert.match(pane,/weatherMapRoute: weatherPane\.subjectRoute/);
  assert.match(discovery,/property bool weatherMapOnly: false/);
  assert.match(discovery,/function weatherLayerEnabled\(layer\)/);
  for(const title of [
    'SPATIAL PLOT // GDACS + USGS QUAKES + EONET + FIRMS + NEWS',
    'RADAR // NOAA/NWS MRMS BASE REFLECTIVITY + 4H HISTORY',
    'RADAR FALLBACK // RAINVIEWER PAST RADAR',
    'SMOKE PLUMES // NOAA HMS'
  ]) assert.ok(discovery.includes(title),"classic map section missing "+title);
  assert.match(discovery,/WHEEL ZOOM \/\/ DRAG PAN \/\/ MANUAL RADAR \+ SMOKE/);
  assert.match(discovery,/WEATHER \/\/ RADAR \+ SMOKE GEOGRAPHY/);
});

test("WEATHER map does not fetch or plot non-weather events", () => {
  assert.match(discovery,/weatherMapOnly \? \[\] : MapProjection\.plottable\(source/);
  assert.match(discovery,/weatherMapOnly \? \[\] : MapProjection\.plottable\(/);
  assert.match(discovery,/!weatherMapOnly && mapShowEarthquakes/);
  assert.match(discovery,/!weatherMapOnly && mapShowGdacs/);
  assert.match(discovery,/&& !stationDiscovery\.weatherMapOnly/);
  assert.match(discovery,/model: firmsService\.ready \? firmsService\.hotspots : \[\]/);
  assert.match(discovery,/visible: !stationDiscovery\.weatherMapOnly/);
  // Full source-row lists are now partitioned by DOMAIN:
  // WEATHER map has none; EARTH's original map renderer keeps full source
  // controls via its migrated route without a duplicate CLASSIC loader.
  assert.match(discovery,/model: stationDiscovery.domain === "map"\s*&& !stationDiscovery.earthMapOnly && source.ready\s*\? stationDiscovery.visibleRows : \[\]/);
  assert.match(discovery,/model: stationDiscovery.domain === "map"\s*&& stationDiscovery.earthMapOnly\s*&& stationDiscovery.earthLayerEnabled\("eonet"\)\s*&& source.ready\s*\? stationDiscovery.mapCompanionEonetRows : \[\]/);
  assert.match(discovery,/weatherLayerEnabled\("smoke"\)/);
  assert.match(discovery,/weatherLayerEnabled\("radar"\)/);
  assert.match(discovery,/weatherLayerEnabled\("radar-fallback"\)/);
  for(const title of [
    "FIRE HOTSPOTS // NASA FIRMS",
    "SOURCE RACK // WHAT IS CONNECTED",
    "SPATIAL PLOT // GDACS + USGS QUAKES + EONET + FIRMS + NEWS"
  ]) assert.ok(discovery.includes(title),"CLASSIC content must survive "+title);
});

test("M2b stays read-only across datasets, user records, and other subjects", () => {
  assert.match(station,/subjectNavigationOpen: false/);
  assert.match(pane,/active: weatherPane\.visible && weatherPane\.kind !== ""/);
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(nav,/function showNewsMentionsOnEarth\(payload\)/);
  assert.ok(!pane.includes("WeatherServices."));
  assert.ok(!pane.includes("eventArchiveStore:"));
  assert.ok(!pane.includes("dossierArchiveStore:"));
  for(const token of ["Process {","FileView {","XMLHttpRequest","swaymsg","curl "])
    assert.ok(!policySource.includes(token),"unexpected code in policy "+token);
  assert.equal(env.kindForRoute("weather/maps/lightning"),"ground");
});
