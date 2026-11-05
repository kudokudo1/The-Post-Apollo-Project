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
const dashboard = read("widgets/weather/StationCosmosOverviewPane.qml");
const workspaceSource = read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const solarWind = read("widgets/weather/StationCosmosSolarWindPane.qml");
const browser = read("widgets/weather/StationSubjectNavigator.qml");
const station = read("widgets/weather/WeatherStationW.qml");
const weatherPolicy = read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const nav = vm.createContext({});
const cosmos = vm.createContext({});
const weather = vm.createContext({});
const workspace = vm.createContext({});
vm.runInContext(navSource.replace(/^\.pragma library\s*$/m, ""), nav);
vm.runInContext(cosmosSource.replace(/^\.pragma library\s*$/m, ""), cosmos);
vm.runInContext(weatherPolicy.replace(/^\.pragma library\s*$/m, ""), weather);
vm.runInContext(workspaceSource.replace(/^\.pragma library\s*$/m, ""), workspace);
const plain = obj => JSON.parse(JSON.stringify(obj));

test("COSMOS retains the 21 scoped routes plus two complete original SKY/SPACE views", () => {
  assert.equal(cosmos.FORMAT, "post-apollo.weather.cosmos-panels.c1.v1");
  const keys = Object.keys(cosmos.ROUTES);
  assert.equal(keys.length, 23);
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
  for(const section of ["header","solar"])
    assert.ok(cosmos.visibleFor("space","cosmos/overview",section),section);
  for(const section of ["scales","aurora","xray","bulletins"])
    assert.equal(cosmos.visibleFor("space","cosmos/overview",section),false);
  assert.equal(cosmos.visibleFor("sky","cosmos/overview","hourly"),false);
  assert.equal(cosmos.visibleFor("sky","cosmos/overview","current"),false);
  assert.equal(cosmos.visibleFor("space","cosmos/overview","xray"),false);
  assert.equal(cosmos.needsSource("cosmos/overview","moon"),true);
  assert.equal(cosmos.needsSource("cosmos/overview","scales"),false);
  assert.equal(cosmos.needsSource("cosmos/overview","aurora"),false);
  assert.equal(cosmos.needsSource("cosmos/overview","eclipses"),false);
  assert.match(pane,/id: overviewComponent[\s\S]*StationCosmosOverviewPane\s*\{/);
  assert.match(pane,/StationSky\s*\{/); // Original detail page remains
  assert.match(pane,/StationSpace\s*\{/); // Original full SPACE remains
  assert.match(pane,/onRouteRequested: function\(path\)/);
  assert.match(dashboard,/sourceOnly: true/);
  assert.match(dashboard,/StationCosmosVisualInstruments\s*\{/);
  assert.match(dashboard,/compactMode: true/);
  assert.doesNotMatch(dashboard,/Flickable\s*\{|ScrollView\s*\{|StationSpace\s*\{|Process\s*\{|Timer\s*\{/);
});

test("Sun, Moon, planets, stars and events reuse the actual SKY modules", () => {
  const map = {
    "cosmos/sun/position":"astronomy",
    "cosmos/sun/twilight":"twilight",
    "cosmos/sun/photo-light":"twilight",
    "cosmos/moon/ephemeris":"moon",
    "cosmos/moon/position":"moon-position",
    "cosmos/planets-stars/celestial-fix":"celestial-fix",
    "cosmos/planets-stars/planet-clock":"planet-clock",
    "cosmos/planets-stars/constellations":"celestial-fix",
    "cosmos/events/eclipses":"eclipses",
    "cosmos/events/meteors":"meteor",
    "cosmos/events/overview":"meteor",
    "cosmos/events/iss":"iss"
  };
  assert.equal(Object.keys(map).length,12);
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


test("C2 COSMOS overview shows interactive sky graphics and compact core SPACE readings",()=>{
  assert.match(dashboard,/id: consoleHeader/);
  assert.match(dashboard,/id: skyInstrumentFrame/);
  assert.match(dashboard,/id: spaceMetricRow/);
  assert.match(dashboard,/height: 48/);
  assert.match(dashboard,/anchors.margins: 6/);
  assert.match(dashboard,/anchors.margins: 1/);
  assert.match(dashboard,/MouseArea\s*\{/);
  assert.match(dashboard,/cursorShape: Qt.PointingHandCursor/);

  assert.match(dashboard,/height: Math\.max\(0,dashboard\.height-consoleHeader\.height/);
  assert.match(dashboard,/anchors\.fill: parent/);
  assert.match(dashboard,/moonEphemeris: sourceSky\.moonObservation/);
  assert.match(dashboard,/currentSolarPosition: sourceSky\.currentSolarPosition/);
  assert.match(dashboard,/solarCivilOffsetMinutes: sourceSky\.moonCivilOffsetMinutes/);
  assert.match(dashboard,/moonReady: !!sourceSky\.moonObservation/);
  for(const field of [
    "kpReady","solarWindReady","magneticFieldReady","solarFluxReady",
    "solarWindSpeed","magneticFieldBz","solarFlux"
  ]) assert.ok(dashboard.includes(field),field);
  for(const route of [
    "cosmos/sun/position","cosmos/moon/ephemeris",
    "cosmos/space-weather/overview","cosmos/space-weather/full",
    "cosmos/space-weather/geomagnetic",
    "cosmos/space-weather/solar-wind",
    "cosmos/space-weather/solar-activity"
  ]) {
    assert.ok(nav.findRoute(route),route);
    assert.ok(dashboard.includes('"'+route+'"'),"missing detail action "+route);
  }
  assert.match(dashboard,/onClicked: overview\.routeRequested\(modelData\.path\)/);
  assert.match(browser,/id: cosmosLivePane\s*onRouteRequested: function\(path\)\s*\{\s*browser\.chooseRoute\(path\)/);
  assert.match(dashboard,/RuntimePolicy\.displayRow\(sourceId/);
  assert.match(dashboard,/receivedAt:received/);
  assert.match(dashboard,/observedAt:observed/);
  assert.match(dashboard,/usingCache:!!cache/);
  for(const id of ["space-kp","space-wind","space-imf","space-flux"])
    assert.ok(dashboard.includes('availability("'+id+'"'));
  assert.match(dashboard,/SPACE WEATHER \/\/ LATEST/);
  assert.match(dashboard,/if \(!ready \|\| value===null \|\| value===undefined/);
  assert.match(dashboard,/return "--"/);
  assert.equal((dashboard.match(/StationSky\s*\{/g)||[]).length,1);
  assert.equal((dashboard.match(/StationCosmosVisualInstruments\s*\{/g)||[]).length,1);
  assert.equal((pane.match(/StationSpace\s*\{/g)||[]).length,1);
});

test("C3 QML ids never shadow JavaScript built-ins", () => {
  assert.match(solarWind, /id: windConsole/);
  assert.doesNotMatch(solarWind,
    /\bid:\s*(?:console|Math|JSON|Date|Array|Object|Number|String|Qt)\b/);
});

test("C3 Solar Wind is a fixed, interactive, source-backed instrument", () => {
  assert.match(pane,/cosmosPane\.subjectRoute === "cosmos\/space-weather\/solar-wind"/);
  assert.match(pane,/id: solarWindComponent[\s\S]*StationCosmosSolarWindPane\s*\{/);
  assert.match(pane,/liveHistoryStore: cosmosPane\.liveHistoryStore/);
  assert.match(pane,/onRouteRequested: function\(path\)/);
  assert.match(solarWind,/StationInteractiveHistoryChart\s*\{/);
  assert.match(solarWind,/height: 258/);
  assert.match(solarWind,/leftField: "solarWindSpeed"/);
  assert.match(solarWind,/rightField: "bz"/);
  assert.match(solarWind,/historyRevision/);
  assert.match(solarWind,/liveHistoryStore\.samples\("space-wind", "global", runtimeNowMs\)/);
  assert.match(solarWind,/liveHistoryStore\.samples\("space-imf", "global", runtimeNowMs\)/);
  assert.match(solarWind,/RuntimePolicy\.displayRow\(id/);
  assert.match(solarWind,/KP IS GEOMAGNETIC CONTEXT/);
  assert.match(solarWind,/NOAA SWPC/);
  for (const field of ["solarWindReady", "magneticFieldReady", "kpReady",
                       "magneticFieldBz", "magneticFieldBt"]) {
    assert.ok(solarWind.includes(field), field);
  }
  for (const route of ["cosmos/space-weather/geomagnetic",
                       "cosmos/space-weather/full"]) {
    assert.ok(nav.findRoute(route), route);
    assert.ok(solarWind.includes('"'+route+'"'), route);
  }
  assert.doesNotMatch(solarWind,/Flickable\s*\{|ScrollView\s*\{|StationSpace\s*\{/);
  for (const forbidden of ["WeatherServices.", "FileView {", "Process {",
                           "Timer {", "XMLHttpRequest", "Qt.callLater"]) {
    assert.ok(!solarWind.includes(forbidden), forbidden);
  }
});

test("COSMOS SUN, MOON and EVENTS bottom landings own their subject data", () => {
  const tabs = workspace.GROUPS.cosmos;
  const tab = key => tabs.find(row => row.key === key);
  assert.equal(tab("sun").path, "cosmos/sun/position");
  assert.equal(tab("moon").path, "cosmos/moon/ephemeris");
  assert.equal(tab("sky").path, "cosmos/planets-stars/celestial-fix");
  assert.equal(tab("events").path, "cosmos/events/overview");
  assert.equal(workspace.selectedGroup("cosmos/planets-stars/planet-clock"),"sky");
  assert.equal(workspace.selectedGroup("cosmos/events/meteors"),"events");
  assert.ok(nav.findRoute("cosmos/events/overview"));
  assert.ok(nav.findRoute("cosmos/sky/full")); // Complete historical reference
  assert.equal(cosmos.visibleFor("sky","cosmos/sun/position","astronomy"),true);
  assert.equal(cosmos.visibleFor("sky","cosmos/sun/position","twilight"),true);
  assert.equal(cosmos.visibleFor("sky","cosmos/sun/position","moon"),false);
  assert.equal(cosmos.needsSource("cosmos/sun/position","moon"),false);
  assert.equal(cosmos.visibleFor("sky","cosmos/moon/ephemeris","moon"),true);
  assert.equal(cosmos.visibleFor("sky","cosmos/moon/ephemeris","moon-position"),true);
  assert.equal(cosmos.visibleFor("sky","cosmos/moon/ephemeris","celestial-fix"),false);
  assert.equal(cosmos.needsSource("cosmos/moon/ephemeris","moon"),true);
  assert.equal(cosmos.needsSource("cosmos/moon/ephemeris","celnav"),true);
  for (const source of ["planets","iss","meteor","eclipses"]) {
    assert.equal(cosmos.needsSource("cosmos/moon/ephemeris",source),false,source);
  }
  assert.equal(cosmos.visibleFor("sky","cosmos/moon/position","moon-position"),true);
  assert.equal(cosmos.needsSource("cosmos/moon/position","celnav"),true);
  for (const section of ["celestial-fix","planet-clock"]) {
    assert.equal(cosmos.visibleFor("sky","cosmos/planets-stars/celestial-fix",section),true);
  }
  for (const section of ["moon","meteor","eclipses","iss"]) {
    assert.equal(cosmos.visibleFor("sky","cosmos/planets-stars/celestial-fix",section),false);
  }
  for (const section of ["iss","eclipses","meteor"]) {
    assert.equal(cosmos.visibleFor("sky","cosmos/events/overview",section),true);
  }
  for (const source of ["iss","eclipses","meteor"]) {
    assert.equal(cosmos.needsSource("cosmos/events/overview",source),true);
  }
  for (const source of ["moon","celnav","planets"]) {
    assert.equal(cosmos.needsSource("cosmos/events/overview",source),false);
  }
  // The original comprehensive route remains intact under INDEX.
  for (const section of ["moon","iss","eclipses","meteor","planet-clock"]) {
    assert.equal(cosmos.visibleFor("sky","cosmos/sky/full",section),true);
  }
  assert.match(sky,/title: "MOON \\/\\/ CURRENT POSITION"/);
  assert.match(sky,/visible: sky\\.subjectRoute !== "cosmos\\/sun\\/position"/);
  assert.match(sky,/id: eventsJumpRow/);
  assert.match(sky,/id: meteorEventSection/);
  assert.match(sky,/id: eclipseEventSection/);
  assert.match(sky,/id: issEventSection/);
  assert.match(sky,/label:"METEOR SHOWERS"/);
  assert.match(sky,/skyScroll\\.contentY = Math\\.max/);
});
