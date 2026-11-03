"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const sourceTree = read("widgets/weather/StationSubjectNavigationPolicy.js");
const preview = read("widgets/weather/StationSubjectNavigationPreviewPolicy.js");
const weatherPolicy = read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const pane = read("widgets/weather/StationWeatherSubjectPane.qml");
const home = read("widgets/weather/StationHome.qml");
const ground = read("widgets/weather/StationGround.qml");
const sky = read("widgets/weather/StationSky.qml");
const discovery = read("widgets/weather/StationDiscovery.qml");
const navigator = read("widgets/weather/StationSubjectNavigator.qml");
const context = vm.createContext({});
const weather = vm.createContext({});
vm.runInContext(sourceTree.replace(/^\.pragma library\s*$/m, ""), context);
vm.runInContext(preview.replace(/^\.pragma library\s*$/m, ""), context);
vm.runInContext(weatherPolicy.replace(/^\.pragma library\s*$/m, ""), weather);
const plain = x => JSON.parse(JSON.stringify(x));

// Exact original source-control IDs and the *existing* filtered section which
// actually supplies them. A route's existence alone does not qualify it.
const reviewed = [
  ["home-official-alert", "weather/hazards/alerts", "ground", "alerts"],
  ["home-current-weather", "weather/overview", "home", "snapshot"],
  ["home-next-hours", "weather/forecasts/hourly", "sky", "hourly"],
  ["home-air-quality", "weather/conditions/air", "ground", "air-pm"],
  ["home-historical-forecast", "weather/history/historical-forecast", "home", "history"],
  ["home-auto-relevant", "weather/overview", "home", "relevant"],
  ["ground-official-alerts", "weather/hazards/alerts", "ground", "alerts"],
  ["ground-coastal-relationship", "weather/history/relationships/coastal", "ground", "coastal-rel"],
  ["ground-marine-relationships", "weather/history/relationships/marine", "ground", "marine-rel"],
  ["ground-river-nwps", "weather/water/rivers/gauges", "ground", "rivers"],
  ["ground-river-nearby", "weather/water/rivers/nearby", "ground", "rivers"],
  ["ground-river-flood-context", "weather/water/rivers/flood", "ground", "rivers"],
  ["ground-river-stageflow", "weather/water/rivers/hydrograph", "ground", "rivers"],
  ["ground-marine-ndbc", "weather/water/marine", "ground", "marine"],
  ["ground-coast-coops", "weather/water/coast", "ground", "coast"],
  ["ground-lightning-nowcoast", "weather/hazards/lightning", "ground", "lightning"],
  ["ground-heat-fire-weather", "weather/hazards/heat-fire", "ground", "heat-fire"],
  ["ground-air-particulates", "weather/conditions/air", "ground", "air-pm"],
  ["ground-gases", "weather/conditions/air", "ground", "air-gases"],
  ["ground-pollen-peak", "weather/conditions/pollen", "ground", "air-gases"],
  ["ground-pollen-species", "weather/conditions/pollen", "ground", "pollen"],
  ["ground-air-12-hour", "weather/forecasts/air", "ground", "air-forecast"],
  ["sky-current-conditions", "weather/conditions/current", "sky", "current"],
  ["sky-atmosphere", "weather/conditions/atmosphere", "sky", "atmosphere"],
  ["sky-hourly-forecast", "weather/forecasts/hourly", "sky", "hourly"],
  ["sky-hour-inspector", "weather/forecasts/hourly", "sky", "hourly"],
  ["sky-daily-forecast", "weather/forecasts/daily", "sky", "daily"],
  ["map-mrms-radar", "weather/maps/radar", "map", "radar"],
  ["map-rainviewer", "weather/maps/radar-fallback", "map", "rainviewer"],
  ["map-hms-smoke", "weather/maps/smoke", "map", "smoke"]
];

test("M28-F tags only exact source-backed WEATHER controls, no whole-page shortcut assumption", () => {
  assert.equal(reviewed.length, 30);
  assert.equal(new Set(reviewed.map(row => row[0])).size, 30);
  const classified = Object.entries(context.WIRED_IN_SUBJECTS)
    .filter(([id, milestone]) => milestone === "M28-F").map(([id]) => id).sort();
  assert.deepEqual(classified, reviewed.map(row => row[0]).sort());
  for (const [id, route, kind, section] of reviewed) {
    assert.equal(context.PANELS[id], route, id + " actual destination");
    const target = context.findRoute(route);
    assert.ok(target && !target.group && target.subject === "weather", id + " must point to leaf");
    assert.equal(weather.kindForRoute(route), kind, id + " page owner");
    assert.equal(weather.visibleFor(kind, route, section), true, id + " source section");
  }
});

test("marine and coastal legacy controls no longer land in the wrong AQI history view", () => {
  assert.equal(context.PANELS["ground-coastal-relationship"],
    "weather/history/relationships/coastal");
  assert.equal(context.PANELS["ground-marine-relationships"],
    "weather/history/relationships/marine");
  for (const [route,section,source] of [
    ["weather/history/relationships/coastal","coastal-rel","coastal"],
    ["weather/history/relationships/marine","marine-rel","marine"]
  ]) {
    assert.equal(weather.visibleFor("ground", route, section), true);
    assert.equal(weather.needsSource(route, source), true);
    assert.equal(weather.visibleFor("home", route, "relations"), false);
  }
  assert.match(ground,/title: "PRESSURE ↔ COASTAL WATER LEVEL"/);
  assert.match(ground,/title: "LIVE HISTORY \/\/ MARINE RELATIONSHIPS"/);
});

test("filtered WEATHER workspace mounts original HOME, GROUND, SKY and weather-only MAP", () => {
  assert.match(pane,/Loader\s*\{/);
  assert.match(pane,/active: weatherPane\.visible && weatherPane\.kind !== ""/);
  for (const name of ["StationHome", "StationGround", "StationSky", "StationDiscovery"])
    assert.equal((pane.match(new RegExp(name + "\\s*\\{", "g"))||[]).length, 1, name);
  assert.match(pane,/spaceService: null/);
  assert.match(pane,/weatherMapOnly: true/);
  assert.match(pane,/subjectRoute: weatherPane\.subjectRoute/);
  assert.match(pane,/weatherService: weatherPane\.weatherService/);
  assert.match(pane,/nwsAlertSource: weatherPane\.nwsAlertSource/);
  assert.match(pane,/historyService: weatherPane\.historyService/);
  assert.match(pane,/riverSource: weatherPane\.riverSource/);
  for (const forbidden of ["WeatherServices.","Process {","FileView {","StationTerminal {"])
    assert.ok(!pane.includes(forbidden), "no new owner: " + forbidden);
});

test("inherited original readouts and interactions remain in their exact filtered sections", () => {
  const tokens = [
    [home, "StationHomePolicy.rankRelevant(", "relevant card ranker"],
    [home, 'title: "SNAPSHOT // NOW"', "snapshot"],
    [home, 'title: "RECENT HISTORY // ARCHIVED MODEL"', "historic model"],
    [ground, 'title: "OFFICIAL ALERTS // NWS"', "official alerts"],
    [ground, 'title: "NEARBY COMPARE // SAME NWPS SNAPSHOT"', "nearby NWPS"],
    [ground, 'title: "FLOOD CONTEXT // IMPACTS + CRESTS"', "flood impacts"],
    [ground, 'title: "STAGEFLOW // OBSERVED + OFFICIAL FORECAST"', "hydrograph"],
    [ground, 'title: "MARINE // NOAA NDBC"', "buoy"],
    [ground, 'title: "COAST // NOAA CO-OPS"', "tides"],
    [ground, 'title: "LIGHTNING // NOAA NOWCOAST"', "lightning"],
    [ground, 'title: "HEAT + FIRE WEATHER // NWS CONTEXT"', "heat-fire"],
    [ground, 'title: "AIR // PARTICULATES"', "particulates"],
    [ground, 'title: "GASES // POLLEN"', "gases"],
    [ground, 'title: "POLLEN // SPECIES"', "species"],
    [ground, 'title: "AIR // NEXT 12 HOURS"', "air forecast"],
    [sky, 'title: "CURRENT // CONDITIONS"', "current conditions"],
    [sky, 'title: "ATMOSPHERE // OBSERVATION"', "atmosphere"],
    [sky, 'title: "HOURLY // INSPECT SELECTED FORECAST"', "hour inspector"],
    [sky, 'title: "FORECAST // DAILY"', "daily forecast"],
    [discovery, 'function weatherLayerEnabled(layer)', "weather map layer selector"]
  ];
  for (const [file, token, name] of tokens)
    assert.ok(file.includes(token), name + " original section missing");
  assert.match(sky,/inspectedHourIndex = -1/);
  assert.match(discovery,/weatherMapOnly \? \[\] : MapProjection\.plottable/);
});

test("INDEX offers concrete WEATHER routes, preserves unreviewed HOME and non-WEATHER pages", () => {
  const links=plain(context.nativeDestinationsForPath("weather",context.PANELS));
  assert.ok(links.length >= 12 && links.every(x => x.path.startsWith("weather/")));
  assert.equal(new Set(links.map(x => x.path)).size, links.length);
  for (const link of links)
    assert.ok(!context.findRoute(link.path).group, link.path);
  const marine=plain(context.nativeDestinationsForPath(
    "weather/history/relationships",context.PANELS));
  assert.deepEqual(marine.map(x=>x.path),[
    "weather/history/relationships/coastal",
    "weather/history/relationships/marine"
  ]);
  assert.ok(context.remainingSourcePagesForPath("weather",context.PANELS)
    .some(row=>row.id==="home"), "unreviewed HOME controls retain CLASSIC shortcut");
  for (const id of ["home-quick-conditions","home-aqi-humidity","home-aqi-wind",
                    "ground-usgs-seismic","sky-sun-moon","news-live"]) {
    assert.equal(context.WIRED_IN_SUBJECTS[id], undefined, id + " remains unreviewed");
  }
  assert.deepEqual(plain(context.remainingSourcePagesForPath("media/watch",context.PANELS)),
    plain(context.sourcePagesForPath("media/watch",context.PANELS)));
  assert.match(navigator,/model: browser\.nativeDestinations/);
  assert.match(navigator,/model: browser\.classicSources/);
  assert.match(navigator,/onClicked: browser\.legacyPageRequested\(modelData\.id\)/);
});

test("source-true cutover registry is guarded against missing/unknown destinations", () => {
  for (const bad of [null, "WEATHER", "../weather", "weather//maps", "weather?alerts"]) {
    assert.deepEqual(plain(context.nativeDestinationsForPath(bad,context.PANELS)), []);
    assert.deepEqual(plain(context.remainingSourcePagesForPath(bad,context.PANELS)), []);
  }
  const count=Object.keys(context.PANELS).length;
  assert.equal(count,103,"unexpected source control inventory change");
  assert.equal(Object.values(context.WIRED_IN_SUBJECTS)
    .filter(milestone => milestone === "M28-F").length, 30,
    "M28-F exact source-wiring milestone must remain unchanged");
  assert.ok(Object.keys(context.WIRED_IN_SUBJECTS).length >= 46,
    "later audited milestones may only add independent exact source controls");
});
