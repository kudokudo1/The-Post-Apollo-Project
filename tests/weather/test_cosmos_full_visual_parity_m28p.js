"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy=read("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const tree=read("widgets/weather/StationSubjectNavigationPolicy.js");
const workspace=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const terrestrialSource=read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const pane=read("widgets/weather/StationCosmosSubjectPane.qml");
const sky=read("widgets/weather/StationSky.qml");
const space=read("widgets/weather/StationSpace.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const navigator=read("widgets/weather/StationSubjectNavigator.qml");
const rootStation=read("widgets/weather/WeatherStationW.qml");
const contexts=[policy,tree,workspace].map(x=>{
  const c=vm.createContext({});
  vm.runInContext(x.replace(/^\.pragma library\s*$/m,""),c);
  return c;
});
const [cosmos,nav,tabs]=contexts;
const terrestrial=vm.createContext({});
vm.runInContext(terrestrialSource.replace(/^\.pragma library\s*$/m,""),terrestrial);
const plain=x=>JSON.parse(JSON.stringify(x));
const SKY="cosmos/sky/full",SPACE="cosmos/space-weather/full";
const sectionNames=src=>[...new Set([...src.matchAll(/sectionVisible\("([^"]+)"\)/g)]
  .map(x=>x[1]))].sort();

test("COSMOS offers an astronomy-only SKY and complete SPACE as native bottom modes",()=>{
  assert.equal(cosmos.kindForRoute(SKY),"sky");
  assert.equal(cosmos.kindForRoute(SPACE),"space");
  for(const route of [SKY,SPACE]){
    const node=nav.findRoute(route);
    assert.ok(node && !node.group && node.subject==="cosmos");
    assert.deepEqual(plain(nav.breadcrumbs(route).map(x=>x.path)),
      route===SKY?["cosmos","cosmos/sky",SKY]:
        ["cosmos","cosmos/space-weather",SPACE]);
  }
  assert.equal(nav.findRoute("cosmos/sky").group,true);
  assert.equal(tabs.GROUPS.cosmos.length,6,"no extra cramped 8-column mode bar");
  const main=plain(tabs.tabsFor("cosmos/overview"));
  assert.ok(main.some(x=>x.label==="ASTRONOMY"&&x.path===SKY&&x.key==="sky"));
  assert.ok(main.some(x=>x.label==="SPACE // ALL"&&x.path===SPACE&&x.key==="space-weather"));
  assert.equal(tabs.selectedGroup(SKY),"sky");
  assert.equal(tabs.selectedGroup(SPACE),"space-weather");
  assert.equal(tabs.selectedGroup("cosmos/planets-stars/planet-clock"),"sky");
  assert.equal(tabs.selectedGroup("cosmos/events/iss"),"events");
  assert.equal(nav.findRoute("cosmos/planets-stars/celestial-fix").group,false,true);
  assert.match(surface,/model: surface\.activeTabs/);
  assert.match(surface,/onTriggered: surface\.routeRequested\(modelData\.path\)/);
  assert.match(navigator,/browser\.chooseRoute\(path\)/);
});

test("the mixed CLASSIC SKY sections are partitioned across COSMOS astronomy and WEATHER",()=>{
  const sections=sectionNames(sky);
  assert.deepEqual(sections,[
    "astronomy","atmosphere","celestial-fix","current","daily","eclipses",
    "header","hourly","iss","meteor","moon","planet-clock","runtime","twilight"
  ]);
  const astronomy=new Set([
    "header","astronomy","iss","moon","eclipses",
    "celestial-fix","planet-clock","meteor"
  ]);
  const weatherRoutes={
    current:"weather/conditions/current",
    atmosphere:"weather/conditions/current",
    hourly:"weather/forecasts/hourly",
    daily:"weather/forecasts/hourly",
    twilight:"weather/forecasts/hourly"
  };
  for(const section of sections){
    assert.equal(cosmos.visibleFor("sky",SKY,section),astronomy.has(section),
      "COSMOS must not display terrestrial "+section);
    assert.equal(cosmos.visibleFor("space",SKY,section),false,section);
  }
  for(const [section,route] of Object.entries(weatherRoutes))
    assert.ok(terrestrial.visibleFor("sky",route,section),route+" "+section);
  assert.equal(cosmos.visibleFor("sky",SKY,"current"),false);
  assert.equal(cosmos.visibleFor("sky",SKY,"hourly"),false);
  assert.equal(cosmos.visibleFor("sky",SKY,"daily"),false);
  assert.equal(cosmos.visibleFor("sky",SKY,"atmosphere"),false);
  for(const s of ["moon","eclipses","celnav","iss","planets","meteor"])
    assert.equal(cosmos.needsSource(SKY,s),true,s);
  assert.equal(cosmos.needsSource(SKY,"xray"),false);
  assert.equal(cosmos.needsSource("weather/conditions/current","meteor"),false);
  assert.ok(sky.includes('title: "METEOR SHOWERS // IAU MDC"'));
  assert.ok(sky.includes('title: "ECLIPSES // NASA GSFC"'));
  assert.ok(sky.includes('title: "PLANET CLOCK // USNO RISE + TRANSIT + SET"'));
  assert.ok(sky.includes('title: "FORECAST // NEXT HOURS"'));
  assert.ok(sky.includes('title: "FORECAST // DAILY"'));
  assert.ok(sky.includes("StationCosmosVisualInstruments {"),
    "sun/moon visuals remain part of the full original SKY component");
  assert.match(sky,/visible: sky\.subjectRoute\.indexOf\("cosmos\/"\) === 0/);
  assert.match(sky,/LOCAL REFERENCE READY/);
  assert.equal(terrestrial.needsSource("weather/forecasts/hourly","astronomy"),false);
});

test("the original SPACE's NOAA solar image, model curves, history and bulletins all display",()=>{
  const sections=sectionNames(space);
  assert.deepEqual(sections,[
    "aurora","bulletins","cycle","field","flares","footer","header",
    "kp-forecast","kp-history","relation","runtime","scales","solar",
    "suvi","warnings","watch","xray"
  ]);
  for(const section of sections){
    assert.equal(cosmos.visibleFor("space",SPACE,section),true,section);
    assert.equal(cosmos.visibleFor("sky",SPACE,section),false,section);
  }
  for(const s of ["aurora","flares","xray","alerts","cycle","scales","kpForecast"])
    assert.equal(cosmos.needsSource(SPACE,s),true,s);
  assert.equal(cosmos.needsSource(SPACE,"iss"),false);
  for(const label of [
    "SOLAR // GEOMAGNETIC",
    "LIVE HISTORY // SOLAR CONTEXT",
    "NOAA SCALES // CURRENT SNAPSHOT",
    "SOLAR CYCLE // NOAA MONTHLY PREDICTION",
    "GEOMAGNETIC // KP 72-HOUR HISTORY",
    "GEOMAGNETIC // NOAA KP FORECAST",
    "FIELD // SOURCE TIMES",
    "SOLAR IMAGER // NOAA SWPC SUVI",
    "AURORA // 30-90 MIN FORECAST",
    "SOLAR // LIVE X-RAY FLUX",
    "SOLAR // GOES X-RAY FLARES",
    "GEOMAGNETIC // WATCH-DAY OUTLOOK",
    "NOAA // WARNING VALIDITY REVIEW",
    "SPACE WEATHER // NOAA BULLETINS"
  ]) assert.ok(space.includes(label),label+" original instrument");
  assert.match(space,/source: space\.solarImageUrl/);
  assert.match(space,/Image\s*\{/);
});

test("full native routes still render through single original panel loader with real scrolling",()=>{
  assert.match(pane,/sourceComponent: cosmosPane\.kind === "overview"/);
  assert.match(pane,/cosmosPane\.kind === "sky"/);
  assert.match(pane,/\? skyComponent/);
  assert.match(pane,/: spaceComponent/);
  assert.equal((pane.match(/id: cosmosLoader/g)||[]).length,1);
  assert.match(pane,/active: cosmosPane\.visible && cosmosPane\.kind !== ""/);
  assert.match(pane,/subjectRoute: cosmosPane\.subjectRoute/);
  assert.match(pane,/StationSky\s*\{/);
  assert.match(pane,/StationSpace\s*\{/);
  assert.match(sky,/Flickable\s*\{\s*id: skyScroll/);
  assert.match(space,/Flickable\s*\{\s*id: spaceScroll/);
  assert.match(sky,/contentHeight: Math\.max\(height, skyContent\.y \+ skyContent\.implicitHeight \+ 12\)/);
  assert.match(space,/contentHeight: Math\.max\(height, spaceContent\.y \+ spaceContent\.implicitHeight \+ 12\)/);
  assert.match(surface,/StationCosmosSubjectPane\s*\{/);
  assert.ok(!rootStation.includes("weatherContentLoader"));
  assert.match(rootStation,/StationSubjectNavigator\s*\{/);
});

test("partial details retain the original fine-grained source gates, no unrecognized route opens a provider",()=>{
  assert.equal(cosmos.visibleFor("sky","cosmos/overview","meteor"),false);
  assert.equal(cosmos.visibleFor("space","cosmos/space-weather/overview","cycle"),false);
  assert.equal(cosmos.visibleFor("space","cosmos/space-weather/solar-activity","suvi"),true);
  assert.equal(cosmos.needsSource("cosmos/events/iss","meteor"),false);
  for(const route of [
    "cosmos/sky/unknown","cosmos/space-weather/malformed",
    "weather/forecasts/hourly","cosmos/sky-full",null,{},[]
  ]){
    assert.equal(cosmos.kindForRoute(route),"");
    assert.equal(cosmos.needsSource(route,"moon"),false);
    assert.equal(cosmos.needsSource(route,"cycle"),false);
  }
  assert.equal(Object.keys(nav.PANELS).length,103);
  assert.equal(nav.PANELS["space-suvi-imager"],"cosmos/space-weather/solar-activity",
    "M0 source provenance is unchanged");
  for(const p of [policy,tree,workspace]){
    for(const bad of ["Process {","FileView {","Qt.callLater","XMLHttpRequest","swaymsg"])
      assert.ok(!p.includes(bad),"unexpected new source/process in route policy: "+bad);
  }
});
