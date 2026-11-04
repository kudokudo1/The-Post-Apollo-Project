"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=f=>fs.readFileSync(path.join(root,f),"utf8");
const nav=read("widgets/weather/StationSubjectNavigationPolicy.js");
const index=read("widgets/weather/StationSubjectNavigationPreviewPolicy.js");
const cosmosPolicy=read("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const pane=read("widgets/weather/StationCosmosSubjectPane.qml");
const timeline=read("widgets/weather/StationSpaceWeatherTimelinePane.qml");
const sky=read("widgets/weather/StationSky.qml");
const space=read("widgets/weather/StationSpace.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const env=vm.createContext({}),cosmos=vm.createContext({});
vm.runInContext(nav.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(index.replace(/^\.pragma library\s*$/m,""),env);
vm.runInContext(cosmosPolicy.replace(/^\.pragma library\s*$/m,""),cosmos);
const plain=x=>JSON.parse(JSON.stringify(x));

// This reviewed set is deliberately bounded to the original SKY/SPACE
// sections already mounted under COSMOS, not every destination in the tree.
const reviewed=[
  ["sky-sun-moon","cosmos/overview","sky","astronomy"],
  ["sky-iss-passes","cosmos/events/iss","sky","iss"],
  ["sky-moon-usno","cosmos/moon/ephemeris","sky","moon"],
  ["sky-eclipses","cosmos/events/eclipses","sky","eclipses"],
  ["sky-celestial-fix","cosmos/planets-stars/celestial-fix","sky","celestial-fix"],
  ["sky-planet-clock","cosmos/planets-stars/planet-clock","sky","planet-clock"],
  ["sky-meteor-showers","cosmos/events/meteors","sky","meteor"],
  ["sky-twilight","cosmos/sun/twilight","sky","twilight"],
  ["sky-photo-light","cosmos/sun/photo-light","sky","twilight"],
  ["sky-current-sun","cosmos/sun/position","sky","astronomy"],
  ["space-geomagnetic-core","cosmos/space-weather/overview","space","solar"],
  ["space-solar-context","cosmos/space-weather/history","space","relation"],
  ["space-noaa-scales","cosmos/space-weather/geomagnetic","space","scales"],
  ["space-solar-cycle","cosmos/space-weather/history","space","cycle"],
  ["space-kp-history","cosmos/space-weather/history","space","kp-history"],
  ["space-kp-forecast","cosmos/space-weather/forecasts","space","kp-forecast"],
  ["space-suvi-imager","cosmos/space-weather/solar-activity","space","suvi"],
  ["space-aurora","cosmos/space-weather/aurora","space","aurora"],
  ["space-xray-flux","cosmos/space-weather/solar-activity","space","xray"],
  ["space-goes-flares","cosmos/space-weather/solar-activity","space","flares"],
  ["space-watch-day","cosmos/space-weather/forecasts","space","watch"],
  ["space-warning-validity","cosmos/space-weather/bulletins","space","warnings"],
  ["space-bulletins","cosmos/space-weather/bulletins","space","bulletins"]
];

test("only 23 existing SKY and SPACE control families enter the COSMOS ledger",()=>{
  assert.equal(reviewed.length,23);
  const ids=reviewed.map(x=>x[0]);
  assert.equal(new Set(ids).size,23);
  const registry=Object.keys(env.WIRED_IN_SUBJECTS)
    .filter(id=>env.WIRED_IN_SUBJECTS[id]==="M28-G").sort();
  assert.deepEqual(registry,ids.slice().sort());
  for(const [id,route,page,section] of reviewed){
    assert.equal(env.PANELS[id],route,id+" original target");
    const leaf=env.findRoute(route);
    assert.ok(leaf && !leaf.group && leaf.subject==="cosmos",id+" valid leaf");
    assert.ok(cosmos.routeInfo(route),id+" real COSMOS panel");
    assert.equal(cosmos.visibleFor(page,route,section),true,id+" filtered section");
  }
  assert.equal(Object.keys(env.PANELS).length,103);
  assert.equal(Object.values(env.WIRED_IN_SUBJECTS)
    .filter(milestone=>milestone==="M28-G").length,23,
    "M28-G exact SKY/SPACE classification remains stable");
  assert.ok(Object.keys(env.WIRED_IN_SUBJECTS).length>=69,
    "later independently reviewed cutovers may add to the ledger");
});

test("SKY cosmos-only source gates stay separate from WEATHER forecasts",()=>{
  for(const [source,route] of [
    ["moon","cosmos/moon/ephemeris"],
    ["iss","cosmos/events/iss"],
    ["eclipses","cosmos/events/eclipses"],
    ["celnav","cosmos/planets-stars/celestial-fix"],
    ["planets","cosmos/planets-stars/planet-clock"],
    ["meteor","cosmos/events/meteors"]
  ]){
    assert.equal(cosmos.needsSource(route,source),true,source+" source enabled");
    assert.equal(cosmos.needsSource("weather/forecasts/hourly",source),false);
    assert.ok(sky.includes('CosmosPanelPolicy.needsSource(sky.subjectRoute,"'+source+'")'));
  }
  for(const label of [
    "ISS PASSES // SKYFIELD + SGP4",
    "MOON // USNO EPHEMERIS",
    "ECLIPSES // NASA GSFC",
    "SKY NOW // USNO CELESTIAL FIX"
  ])assert.ok(sky.includes(label),"original SKY instrument: "+label);
  assert.match(pane,/StationSky\s*\{/);
  assert.match(pane,/subjectRoute: cosmosPane\.subjectRoute/);
});

test("original SPACE data and source lifetime remain within COSMOS, including chart wrapper",()=>{
  for(const [source,route] of [
    ["cycle","cosmos/space-weather/history"],
    ["scales","cosmos/space-weather/geomagnetic"],
    ["kpForecast","cosmos/space-weather/forecasts"],
    ["aurora","cosmos/space-weather/aurora"],
    ["xray","cosmos/space-weather/solar-activity"],
    ["flares","cosmos/space-weather/solar-activity"],
    ["alerts","cosmos/space-weather/bulletins"]
  ]){
    assert.equal(cosmos.needsSource(route,source),true,source+" source enabled");
    assert.equal(cosmos.needsSource("weather/forecasts/hourly",source),false);
    assert.ok(space.includes('CosmosPanelPolicy.needsSource(space.subjectRoute,"'+source+'")'));
  }
  for(const label of [
    "SOLAR // GEOMAGNETIC",
    "SOLAR CYCLE // NOAA MONTHLY PREDICTION",
    "GEOMAGNETIC // KP 72-HOUR HISTORY",
    "GEOMAGNETIC // NOAA KP FORECAST",
    "SOLAR IMAGER // NOAA SWPC SUVI",
    "AURORA // 30-90 MIN FORECAST",
    "SPACE WEATHER // NOAA BULLETINS"
  ])assert.ok(space.includes(label),"original SPACE instrument: "+label);
  assert.match(pane,/StationSpaceWeatherTimelinePane\s*\{/);
  assert.match(timeline,/StationInteractiveHistoryChart\s*\{/);
  assert.match(timeline,/StationSpace\s*\{/);
  assert.match(timeline,/subjectRoute: timeline\.subjectRoute/);
  assert.match(pane,/spaceService: cosmosPane\.spaceService/);
  assert.match(pane,/liveHistoryStore: cosmosPane\.liveHistoryStore/);
  assert.match(station,/spaceService: weatherStation\.spaceService/);
  for(const bad of ["WeatherServices.","FileView {","Process {","XMLHttpRequest"])
    assert.ok(!pane.includes(bad),"no extra COSMOS owner: "+bad);
});

test("deep INDEX uses concrete COSMOS leaf links and still preserves unresolved TOOLS provenance",()=>{
  const links=plain(env.nativeDestinationsForPath("cosmos",env.PANELS));
  assert.ok(links.length>=14);
  assert.equal(new Set(links.map(x=>x.path)).size,links.length);
  assert.ok(links.every(x=>x.path.startsWith("cosmos/") && !env.findRoute(x.path).group));
  assert.deepEqual(plain(env.nativeDestinationsForPath("cosmos/space-weather/history",env.PANELS)),
    [{path:"cosmos/space-weather/history",panels:3,milestones:["M28-G"]}]);
  assert.ok(env.sourcePagesForPath("cosmos",env.PANELS)
    .some(x=>x.id==="home"),"M0 original HOME SPACE provenance remains visible");
  assert.deepEqual(plain(env.remainingSourcePagesForPath("cosmos",env.PANELS)),[],
    "M28-K HOME SPACE quick card now has exact native HOME section");
  assert.deepEqual(plain(env.remainingSourcePagesForPath("tools/sources/provenance",env.PANELS)),[],
    "M28-I original SPACE field clocks now have their own source-backed TOOLS view");
  assert.match(navigator,/model: browser\.nativeDestinations/);
  assert.ok(!navigator.includes("classicSources"));
  assert.ok(!navigator.includes("legacyPageRequested"));
  assert.deepEqual(plain(env.nativeDestinationsForPath("not-a-route",env.PANELS)),[]);
});

test("COSMOS is observation and prediction, not a certified MAGICK ephemeris",()=>{
  for(const id of ["ground-source","station-source-badge","map-source-rack"])
    assert.equal(env.WIRED_IN_SUBJECTS[id],"M28-L",
      id+" later SOURCE milestone, not an astrology ephemeris");
  assert.equal(cosmos.kindForRoute("magick/astrology/retrogrades"),"");
  assert.equal(cosmos.kindForRoute("weather/conditions/current"),"");
  assert.match(sky,/OPTICAL VISIBILITY NOT EVALUATED/);
  assert.match(sky,/LOCAL VISIBILITY NOT YET CALCULATED/);
});
