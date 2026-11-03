"use strict";

const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const cosmosSource=read("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const weatherSource=read("widgets/weather/StationWeatherSubjectPanelPolicy.js");
const workspaceSource=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const routesSource=read("widgets/weather/StationSubjectNavigationPolicy.js");
const sky=read("widgets/weather/StationSky.qml");
const cosmosPane=read("widgets/weather/StationCosmosSubjectPane.qml");
const weatherPane=read("widgets/weather/StationWeatherSubjectPane.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const contexts=[cosmosSource,weatherSource,workspaceSource,routesSource].map(s=>{
  const o=vm.createContext({});
  vm.runInContext(s.replace(/^\.pragma library\s*$/m,""),o);
  return o;
});
const [cosmos,weather,workspace,nav]=contexts;
const sectionNames=src=>[...new Set([...src.matchAll(/sectionVisible\("([^"]+)"\)/g)].map(m=>m[1]))].sort();
const astronomy=["header","astronomy","moon","iss","eclipses","celestial-fix","planet-clock","meteor"];
const terrestrial={
  "runtime":"weather/conditions/current",
  "current":"weather/conditions/current",
  "atmosphere":"weather/conditions/current",
  "hourly":"weather/forecasts/hourly",
  "daily":"weather/forecasts/hourly",
  "twilight":"weather/forecasts/hourly"
};

test("all 14 original SKY sections are partitioned: observatory in COSMOS, terrestrial in WEATHER",()=>{
  const all=sectionNames(sky);
  assert.equal(all.length,14);
  assert.deepEqual([...new Set([...astronomy,...Object.keys(terrestrial)])].sort(),all);
  for(const section of all){
    assert.equal(cosmos.visibleFor("sky","cosmos/sky/full",section),
      astronomy.includes(section),"COSMOS astronomical ownership "+section);
    if(Object.prototype.hasOwnProperty.call(terrestrial,section))
      assert.equal(weather.visibleFor("sky",terrestrial[section],section),true,
        "WEATHER must render original "+section);
    else
      for(const p of ["weather/conditions/current","weather/forecasts/hourly"])
        assert.equal(weather.visibleFor("sky",p,section),false,
          "astronomy must not leak into "+p+": "+section);
  }
  for(const unwanted of ["current","atmosphere","runtime","hourly","daily","twilight"])
    assert.equal(cosmos.visibleFor("sky","cosmos/sky/full",unwanted),false,unwanted);
});

test("NOW + AIR shows Earth observations and atmosphere; FORECAST shows full hourly + daily + photo light",()=>{
  const weatherTabs=workspace.GROUPS.weather;
  const now=weatherTabs.find(x=>x.key==="conditions");
  const forecast=weatherTabs.find(x=>x.key==="forecasts");
  assert.equal(now.path,"weather/conditions/current");
  assert.equal(forecast.path,"weather/forecasts/hourly");
  assert.equal(nav.findRoute(now.path).subject,"weather");
  assert.equal(nav.findRoute(forecast.path).subject,"weather");
  assert.equal(weather.kindForRoute(now.path),"sky");
  assert.equal(weather.kindForRoute(forecast.path),"sky");
  for(const s of ["header","runtime","current","atmosphere"])
    assert.equal(weather.visibleFor("sky",now.path,s),true);
  for(const s of ["header","hourly","daily","twilight"])
    assert.equal(weather.visibleFor("sky",forecast.path,s),true);
  assert.equal(weather.visibleFor("sky",now.path,"hourly"),false);
  assert.equal(weather.visibleFor("sky",forecast.path,"current"),false);
  for(const route of ["weather/conditions/air","weather/conditions/pollen","weather/forecasts/air"]){
    assert.ok(nav.findRoute(route));
    assert.equal(weather.kindForRoute(route),"ground");
  }
  assert.equal(weather.kindForRoute("weather/overview"),"home");
  assert.equal(weather.visibleFor("home","weather/overview","snapshot"),true);
  for(const route of [now.path,forecast.path,"weather/overview"])
    assert.equal(weather.needsSource(route,"astronomy"),false);
});

test("COSMOS is for celestial and space weather, not conditions, air/atmosphere, or terrestrial forecasts",()=>{
  assert.equal(workspace.GROUPS.cosmos.length,6);
  const star=workspace.GROUPS.cosmos.find(x=>x.key==="sky");
  assert.equal(star.label,"ASTRONOMY");
  assert.equal(star.path,"cosmos/sky/full");
  assert.equal(nav.findRoute(star.path).subject,"cosmos");
  assert.equal(nav.findRoute(star.path).label,"ASTRONOMY // CELESTIAL INSTRUMENTS");
  assert.equal(cosmos.kindForRoute(star.path),"sky");
  for(const s of ["moon","eclipses","celnav","iss","planets","meteor"])
    assert.equal(cosmos.needsSource(star.path,s),true);
  for(const s of ["aurora","flares","xray","cycle","scales","kpForecast"])
    assert.equal(cosmos.needsSource(star.path,s),false);
  assert.equal(cosmos.kindForRoute("cosmos/space-weather/full"),"space");
  for(const s of ["aurora","flares","xray","cycle","scales","kpForecast"])
    assert.equal(cosmos.needsSource("cosmos/space-weather/full",s),true);
  assert.equal(cosmos.kindForRoute("weather/conditions/current"),"");
  assert.equal(cosmos.needsSource("weather/forecasts/hourly","meteor"),false);
});

test("one existing SKY loader per selected native subject and distinct header status",()=>{
  assert.match(cosmosPane,/active: cosmosPane\.visible && cosmosPane\.kind !== ""/);
  assert.match(weatherPane,/active: weatherPane\.visible && weatherPane\.kind !== ""/);
  assert.match(cosmosPane,/subjectRoute: cosmosPane\.subjectRoute/);
  assert.match(weatherPane,/subjectRoute: weatherPane\.subjectRoute/);
  assert.match(cosmosPane,/StationSky\s*\{/);
  assert.match(weatherPane,/StationSky\s*\{/);
  assert.match(sky,/Flickable\s*\{\s*id: skyScroll/);
  assert.match(sky,/contentHeight: Math\.max\(height, skyContent\.y \+ skyContent\.implicitHeight \+ 12\)/);
  assert.match(sky,/LOCAL REFERENCE READY/);
  assert.match(sky,/text: sky\.subjectRoute\.indexOf\("cosmos\/"\) === 0/);
  assert.match(sky,/text: "☁  WEATHER"/);
  assert.match(surface,/StationWeatherSubjectPane\s*\{/);
  assert.match(surface,/StationCosmosSubjectPane\s*\{/);
  assert.equal((surface.match(/StationCosmosSubjectPane\s*\{/g)||[]).length,1);
  assert.equal((surface.match(/StationWeatherSubjectPane\s*\{/g)||[]).length,1);
});

test("no original M0 source mapping, CLASSIC rendering or data-service ownership changed",()=>{
  assert.equal(Object.keys(nav.PANELS).length,103);
  assert.equal(nav.PANELS["sky-hourly-forecast"],"weather/forecasts/hourly");
  assert.equal(nav.PANELS["sky-sun-moon"],"cosmos/overview");
  assert.equal(weather.visibleFor("sky","","current"),true);
  assert.equal(weather.visibleFor("sky","","daily"),true);
  assert.equal(cosmos.visibleFor("sky","","moon"),true);
  assert.equal(cosmos.visibleFor("sky","","meteor"),true);
  assert.equal(cosmos.needsSource("","meteor"),true);
  assert.equal(weather.needsSource("","astronomy"),true);
  for(const source of [cosmosSource,weatherSource,workspaceSource,routesSource]){
    for(const forbidden of ["FileView {","Process {","XMLHttpRequest","swaymsg","Qt.callLater"])
      assert.equal(source.includes(forbidden),false,forbidden);
  }
});
