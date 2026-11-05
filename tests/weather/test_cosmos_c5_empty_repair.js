"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const run=p=>{
  const ctx=vm.createContext({});
  vm.runInContext(read(p).replace(/^\.pragma library\s*$/m,""),ctx);
  return ctx;
};
const calendar=run("widgets/weather/StationCosmosCivilCalendarPolicy.js");
const clock=run("widgets/weather/StationCosmosPlanetEventPolicy.js");
const modes=run("widgets/weather/StationCosmosModePolicy.js");
const cosmos=run("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const pane=read("widgets/weather/StationCosmosSubjectPane.qml");
const focus=read("widgets/weather/StationCosmosModesPane.qml");
const sky=read("widgets/weather/StationSky.qml");

test("C5 native workspace forwards instrument mode clicks into active navigation",()=>{
  assert.match(surface,/StationCosmosSubjectPane\s*\{[\s\S]*?onRouteRequested: function\(path\) \{ surface\.routeRequested\(path\); \}/);
  assert.match(pane,/StationCosmosModesPane\s*\{[\s\S]*?onRouteRequested: function\(path\) \{[\s\S]*?cosmosPane\.routeRequested\(path\)/);
  assert.match(focus,/onClicked: focus\.routeRequested\(modelData\.route\)/);
  const routes=[
    "cosmos/sun/position","cosmos/sun/twilight",
    "cosmos/sun/suvi","cosmos/sun/xray","cosmos/sun/flares",
    "cosmos/sun/cycle","cosmos/planets-stars/planet-clock",
    "cosmos/planets-stars/celestial-fix",
    "cosmos/planets-stars/constellations",
    "cosmos/events/meteors","cosmos/events/eclipses","cosmos/events/iss"
  ];
  for(const route of routes) {
    assert.ok(cosmos.routeInfo(route),route);
    assert.ok(modes.family(route)!=="",route);
  }
});

test("C5 civil date uses only existing verified timezone, not system timezone",()=>{
  const timestamp=Date.parse("2026-11-05T03:30:00Z");
  assert.equal(calendar.localCivilDate(timestamp,-300),"2026-11-04");
  assert.equal(calendar.localCivilDate(timestamp,540),"2026-11-05");
  assert.equal(calendar.localCivilDate(timestamp,null),"");
  assert.equal(calendar.localCivilDate(timestamp,""),"");
  assert.equal(calendar.localCivilDate(timestamp,1000),"");
  assert.equal(calendar.localCivilDate(timestamp,NaN),"");
  assert.equal(calendar.localCivilDate(0,-300),"");
  assert.equal(calendar.exactDay("2026-02-30"),"");
  assert.equal(calendar.exactDay("--"),"");
  assert.equal(calendar.focusedDate("--",timestamp,-300,true),"2026-11-04");
  assert.equal(calendar.focusedDate("2026-11-01",timestamp,null,true),"2026-11-01");
  assert.equal(calendar.focusedDate("--",timestamp,null,true),"");
  assert.equal(calendar.focusedDate("--",timestamp,-300,false),"--");
  assert.match(sky,/CosmosCalendar\.focusedDate\(/);
  assert.match(sky,/openMeteoCivilOffsetAvailable/);
  assert.match(sky,/date: sky\.sourceOnly \? sky\.focusedCivilDate : sky\.astronomySummary\.date/);
  assert.match(focus,/readonly property string civilDate:\s*skyFeed \? skyFeed\.focusedCivilDate : ""/);
  assert.match(focus,/ClockPolicy\.clockRows\([\s\S]*?civilDate\)/);
  assert.match(focus,/solarDate: focus\.civilDate/);
});

test("No-source UI retains five planet lanes and shows detailed provider errors",()=>{
  const blank=clock.clockRows([],"");
  assert.equal(blank.length,5);
  assert.equal(blank.every(r=>!r.available && r.events.length===0),true);
  assert.match(focus,/readonly property var displayedPlanetRows:/);
  assert.match(focus,/model: focus\.displayedPlanetRows/);
  for(const planet of ["MERCURY","VENUS","MARS","JUPITER","SATURN"])
    assert.ok(focus.includes('name:"'+planet+'"'),planet);
  for(const signal of [
    "USNO NEEDS VALID DATE, COORDINATES AND UTC OFFSET",
    "SOURCE REQUEST FAILED","SOURCE RECEIVING",
    "LOCATION COORDINATES UNAVAILABLE",
    "SOLAR MODEL NEEDS LOCAL DATE, LOCATION AND UTC OFFSET",
    "NO ACTIVE OR UPCOMING SHOWER IN THE SOURCE WINDOW"
  ])assert.ok(focus.includes(signal),signal);
  assert.match(focus,/visible: focus\.cards\.length === 0/);
  assert.match(focus,/id: meteorScroll/);
  assert.match(focus,/contentHeight: meteorCards\.implicitHeight/);
  assert.match(focus,/sourceOnly: true/);
  for(const src of [calendar,clock,modes]) assert.ok(src);
});
