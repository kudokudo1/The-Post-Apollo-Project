"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = file => fs.readFileSync(path.join(root, file), "utf8");
const navSource = read("widgets/weather/StationSubjectNavigationPolicy.js");
const cosmosSource = read("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const sky = read("widgets/weather/StationSky.qml");
const space = read("widgets/weather/StationSpace.qml");
const pane = read("widgets/weather/StationCosmosSubjectPane.qml");
const browser = read("widgets/weather/StationSubjectNavigator.qml");
const station = read("widgets/weather/WeatherStationW.qml");
const weatherPolicy = read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const nav = vm.createContext({});
const cosmos = vm.createContext({});
const weather = vm.createContext({});
vm.runInContext(navSource.replace(/^\.pragma library\s*$/m, ""), nav);
vm.runInContext(cosmosSource.replace(/^\.pragma library\s*$/m, ""), cosmos);
vm.runInContext(weatherPolicy.replace(/^\.pragma library\s*$/m, ""), weather);
const plain = obj => JSON.parse(JSON.stringify(obj));

test("COSMOS retains the 20 scoped routes plus two complete original SKY/SPACE views", () => {
  assert.equal(cosmos.FORMAT, "post-apollo.weather.cosmos-panels.c1.v1");
  const keys = Object.keys(cosmos.ROUTES);
  assert.equal(keys.length, 22);
  assert.equal(new Set(keys).size, 22);
  assert.deepEqual(keys.filter(k=>cosmos.ROUTES[k].full===true).sort(),
    ["cosmos/sky/full","cosmos/space-weather/full"]);
  for (const route of keys) {
    const info = nav.findRoute(route);
    assert.ok(info, route);
    assert.equal(info.subject, "cosmos");
    assert.ok(["overview","sky","space"].includes(cosmos.kindForRoute(route)), route);
  }
  assert.equal(cosmos.kindForRoute("cosmos"), "");
  assert.equal(cosmos.kindForRoute("cosmos/space-weather"), "");
  assert.equal(cosmos.kindForRoute("cosmos/sun/not-real"), "");
  assert.equal(cosmos.kindForRoute("weather/overview"), "");
  assert.equal(cosmos.kindForRoute("magick/astrology/charts"), "");
});

test("the COSMOS overview shows SKY astronomy and SPACE geomagnetic context together", () => {
  assert.equal(cosmos.kindForRoute("cosmos/overview"),"overview");
  for(const section of ["header","astronomy","moon","twilight"])
    assert.ok(cosmos.visibleFor("sky","cosmos/overview",section),section);
  for(const section of ["header","solar","scales","aurora"])
    assert.ok(cosmos.visibleFor("space","cosmos/overview",section),section);
  assert.equal(cosmos.visibleFor("sky","cosmos/overview","hourly"),false);
  assert.equal(cosmos.visibleFor("sky","cosmos/overview","current"),false);
  assert.equal(cosmos.visibleFor("space","cosmos/overview","xray"),false);
  assert.equal(cosmos.needsSource("cosmos/overview","moon"),true);
  assert.equal(cosmos.needsSource("cosmos/overview","scales"),true);
  assert.equal(cosmos.needsSource("cosmos/overview","aurora"),true);
  assert.equal(cosmos.needsSource("cosmos/overview","eclipses"),false);
  assert.match(pane,/id: astronomyBay/);
  assert.match(pane,/StationSky\s*\{/);
  assert.match(pane,/StationSpace\s*\{/);
  assert.match(pane,/anchors\.top: astronomyBay\.bottom/);
  assert.match(pane,/height: Math\.max\(0, \(cosmosOverview\.height - 8\) \/ 2\)/);
});

test("Sun, Moon, planets, stars and events reuse the actual SKY modules", () => {
  const map = {
    "cosmos/sun/position":"astronomy",
    "cosmos/sun/twilight":"twilight",
    "cosmos/sun/photo-light":"twilight",
    "cosmos/moon/ephemeris":"moon",
    "cosmos/moon/position":"celestial-fix",
    "cosmos/planets-stars/celestial-fix":"celestial-fix",
    "cosmos/planets-stars/planet-clock":"planet-clock",
    "cosmos/planets-stars/constellations":"celestial-fix",
    "cosmos/events/eclipses":"eclipses",
    "cosmos/events/meteors":"meteor",
    "cosmos/events/iss":"iss"
  };
  assert.equal(Object.keys(map).length,11);
  for(const [route, section] of Object.entries(map)) {
    assert.equal(cosmos.kindForRoute(route),"sky");
    assert.ok(cosmos.visibleFor("sky",route,section),route);
    assert.equal(cosmos.visibleFor("space",route,"solar"),false);
  }
  for(const key of ["hourly","daily","current","atmosphere"])
    assert.equal(cosmos.visibleFor("sky","cosmos/events/iss",key),false);
  assert.match(sky,/SubjectPanelPolicy\.visibleFor\("sky",subjectRoute,section\)/);
  assert.match(sky,/CosmosPanelPolicy\.visibleFor\("sky",subjectRoute,section\)/);
  assert.match(sky,/text: "☁  SKY"/);
  assert.match(sky,/text: "✦  COSMOS"/);
  assert.match(sky,/visible: sky\.subjectRoute\.indexOf\("cosmos\/"\) === 0/);
  assert.match(sky,/text: "☁  WEATHER"/);
});

test("SPACE routes partition existing SWPC instruments without changing their original labels", () => {
  const expected = {
    "cosmos/space-weather/overview":["solar","scales","field","aurora"],
    "cosmos/space-weather/solar-wind":["solar","relation","field"],
    "cosmos/space-weather/geomagnetic":["solar","scales","kp-history"],
    "cosmos/space-weather/aurora":["aurora"],
    "cosmos/space-weather/solar-activity":["suvi","xray","flares"],
    "cosmos/space-weather/forecasts":["kp-forecast","watch"],
    "cosmos/space-weather/bulletins":["warnings","bulletins"],
    "cosmos/space-weather/history":["relation","cycle","kp-history"]
  };
  assert.equal(Object.keys(expected).length,8);
  for(const [route, sections] of Object.entries(expected)) {
    assert.equal(cosmos.kindForRoute(route),"space");
    for(const section of sections)
      assert.ok(cosmos.visibleFor("space",route,section),route+" "+section);
    assert.equal(cosmos.visibleFor("sky",route,"moon"),false);
  }
  assert.equal((space.match(/space\.sectionVisible\("([^"]+)"\)/g)||[]).length,31);
  for(const name of [
    "SOLAR // GEOMAGNETIC","NOAA SCALES // CURRENT SNAPSHOT",
    "SOLAR IMAGER // NOAA SWPC SUVI","AURORA // 30-90 MIN FORECAST",
    "GEOMAGNETIC // NOAA KP FORECAST","SPACE WEATHER // NOAA BULLETINS"
  ]) assert.ok(space.includes(name),name);
  assert.match(space,/text: "✦  SPACE"/);
  assert.match(space,/text: "✦  COSMOS"/);
});

test("each SKY and SPACE fetcher is route-gated and WEATHER cannot trigger COSMOS polls", () => {
  const skyIds = {moon:"UsnoMoonService",eclipses:"NasaEclipseService",celnav:"UsnoCelnavService",
                  iss:"IssPassService",planets:"UsnoPlanetRiseSetService",meteor:"IauMeteorShowerService"};
  const spaceIds = {aurora:"AuroraService",flares:"SolarFlareService",xray:"XrayFluxService",
                    alerts:"SwpcAlertService",cycle:"SolarCycleService",
                    scales:"NoaaScalesService",kpForecast:"KpForecastService"};
  for(const [source,component] of Object.entries(skyIds)) {
    assert.ok(sky.includes("WeatherServices."+component+" {"),component);
    assert.ok(sky.includes('CosmosPanelPolicy.needsSource(sky.subjectRoute,"'+source+'")'),source);
  }
  for(const [source,component] of Object.entries(spaceIds)) {
    assert.ok(space.includes("WeatherServices."+component+" {"),component);
    assert.ok(space.includes('CosmosPanelPolicy.needsSource(space.subjectRoute,"'+source+'")'),source);
  }
  for(const name of [...Object.keys(skyIds),...Object.keys(spaceIds)]) {
    assert.equal(cosmos.needsSource("weather/forecasts/hourly",name),false,name);
    assert.equal(cosmos.needsSource("magick/astrology/charts",name),false,name);
    assert.equal(cosmos.needsSource("cosmos/unknown",name),false,name);
    assert.equal(cosmos.needsSource("",name),true,"CLASSIC "+name);
  }
  assert.equal(cosmos.needsSource("cosmos/events/iss","iss"),true);
  assert.equal(cosmos.needsSource("cosmos/events/iss","moon"),false);
  assert.equal(cosmos.needsSource("cosmos/space-weather/forecasts","kpForecast"),true);
  assert.equal(cosmos.needsSource("cosmos/space-weather/forecasts","alerts"),true);
  assert.equal(cosmos.needsSource("cosmos/space-weather/bulletins","alerts"),true);
  assert.equal(cosmos.needsSource("cosmos/space-weather/solar-activity","flares"),true);
});

test("CLASSIC still shows every original SKY/SPACE section and all original fetchers", () => {
  for(const section of ["header","astronomy","twilight","moon","iss","daily"])
    assert.equal(cosmos.visibleFor("sky","",section),true,section);
  for(const section of ["header","solar","scales","cycle","watch","bulletins","footer"])
    assert.equal(cosmos.visibleFor("space","",section),true,section);
  assert.match(sky,/property string subjectRoute: ""/);
  assert.match(space,/property string subjectRoute: ""/);
  assert.match(space,/CosmosPanelPolicy\.visibleFor\("space", subjectRoute, section\)/);
  assert.match(sky,/SubjectPanelPolicy\.needsSource\(sky\.subjectRoute,"astronomy"\)/);
  assert.match(space,/active: space\.visible/);
  for(const p of Object.keys(weather.ROUTES))
    assert.equal(cosmos.kindForRoute(p),"",p);
  assert.equal(weather.kindForRoute("cosmos/overview"),"");
});

test("one shared SpaceService flows through station/browser/COSMOS while Weather remains intact", () => {
  assert.match(station,/spaceService: weatherStation\.spaceService/);
  assert.match(browser,/property var spaceService: null/);
  assert.match(browser,/spaceService: browser\.spaceService/);
  assert.match(pane,/spaceService: cosmosPane\.spaceService/);
  assert.match(pane,/liveHistoryStore: cosmosPane\.liveHistoryStore/);
  assert.match(pane,/weatherService: cosmosPane\.weatherService/);
  assert.match(pane,/active: cosmosPane\.visible && cosmosPane\.kind !== ""/);
  assert.match(browser,/StationCosmosSubjectPane\s*\{/);
  assert.match(browser,/visible: browser\.visible && browser\.liveCosmosKind !== ""/);
  assert.match(browser,/StationWeatherSubjectPane\s*\{/);
  assert.match(browser,/visible: browser\.visible && browser\.liveWeatherKind !== ""/);
  assert.match(station,/property bool subjectNavigationOpen: false/);
  assert.match(station,/SubjectSourceBadge\.badgeFor\(/);
  assert.match(station,/subjectNavigator\.indexOpen/);
  assert.match(station,/StationTerminal\s*\{/);
  assert.match(browser,/function showNewsMentionsOnEarth\(payload\)/);
});

test("COSMOS does not create independent collectors, storage writers or MAGICK calculations", () => {
  for(const forbidden of ["WeatherServices.","FileView {","Process {","XMLHttpRequest","swaymsg","curl ","eventArchiveStore","dossierArchiveStore"])
    assert.ok(!pane.includes(forbidden),"COSMOS pane owns forbidden source or writer: "+forbidden);
  for(const forbidden of ["FileView {","Process {","XMLHttpRequest","Qt.callLater","swaymsg","curl "])
    assert.ok(!cosmosSource.includes(forbidden),"COSMOS policy owns forbidden effect: "+forbidden);
  assert.equal(cosmos.kindForRoute("magick/lunar-solar/moon"),"");
});
