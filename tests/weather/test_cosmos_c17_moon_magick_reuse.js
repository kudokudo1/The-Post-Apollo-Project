"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy=p=>{
 const v=vm.createContext({});
 vm.runInContext(read(p).replace(/^\.pragma library\s*$/m,""),v);
 return v;
};
const nav=policy("widgets/weather/StationSubjectNavigationPolicy.js");
const panels=policy("widgets/weather/StationCosmosSubjectPanelPolicy.js");
const subject=read("widgets/weather/StationCosmosSubjectPane.qml");
const compact=read("widgets/weather/StationCosmosMoonCompactPane.qml");
const reused=read("widgets/weather/StationCosmosAnnualWheelPane.qml");
const annual=read("widgets/weather/StationMagickAnnualCalendarPane.qml");
const forecast=read("widgets/weather/StationMagickForecastCalendarPane.qml");
const forecastPolicy=policy("widgets/weather/StationMagickForecastCalendarPolicy.js");

test("C17 Moon INDEX exposes original phase, annual JPL wheel and weather forecast",()=>{
 for(const route of ["cosmos/moon/ephemeris","cosmos/moon/year","cosmos/moon/forecast"]){
   const entry=nav.findRoute(route);
   assert.ok(entry,route);
   assert.equal(entry.subject,"cosmos");
   assert.equal(panels.kindForRoute(route),"sky");
 }
 assert.equal(panels.needsSource("cosmos/moon/ephemeris","moon"),true);
 for(const route of ["cosmos/moon/year","cosmos/moon/forecast"]){
   for(const source of ["moon","celnav","planets","eclipses","iss","meteor"]){
      assert.equal(panels.needsSource(route,source),false,route+"/"+source);
   }
 }
 assert.match(subject,/cosmosPane\.subjectRoute === "cosmos\/moon\/forecast"\s*\? moonForecastComponent/);
 assert.match(subject,/id: moonForecastComponent\s*StationCosmosAnnualWheelPane\s*\{/);
 assert.match(compact,/objectName: "cosmos-c17-open-moon-forecast"/);
 assert.match(compact,/routeRequested\("cosmos\/moon\/forecast"\)/);
});

test("C17 routes both screenshots to one original MAGICK renderer without new JPL fetchers",()=>{
 assert.match(reused,/property string moonView: "year"/);
 assert.match(reused,/moonView === "forecast" \? "forecast" : "moon"/);
 assert.match(reused,/StationMagickAnnualCalendarPane\s*\{/);
 assert.match(reused,/view: annualFocus\.annualView/);
 assert.match(reused,/lockedView: annualFocus\.annualView/);
 assert.match(reused,/compactForecast: annualFocus\.isMoon && annualFocus\.moonView === "forecast"/);
 assert.match(reused,/objectName: "cosmos-c17-moon-forecast-tab"/);
 assert.match(reused,/objectName: "cosmos-c17-moon-wheel-tab"/);
 assert.match(reused,/onClicked: annualFocus\.routeRequested\("cosmos\/moon\/year"\)/);
 assert.match(reused,/onClicked: annualFocus\.routeRequested\("cosmos\/moon\/forecast"\)/);
 assert.match(annual,/active: annualPane\.visible && annualPane\.view!=="forecast"/);
 assert.match(annual,/compactLayout: annualPane\.compactForecast/);
 assert.match(annual,/readonly property var calendarSource: annualSource/);
 assert.match(annual,/annualPane\.zoomAt/);
 assert.match(annual,/annualPane\.panBy/);
 assert.match(annual,/annualPane\.fitWheel/);
 assert.doesNotMatch(subject,/CelestialAnnualCalendarService\s*\{|UsnoMoonService\s*\{|Process\s*\{/);
 assert.doesNotMatch(reused,/CelestialAnnualCalendarService\s*\{|Process\s*\{|Flickable\s*\{|ScrollView\s*\{/);
});

test("C17 compact forecast keeps the full MAGICK version untouched and never invents phases",()=>{
 assert.match(forecast,/property bool compactLayout: false/);
 assert.match(forecast,/objectName: "magick-m7-forecast-outlook"/);
 assert.match(forecast,/height: outlook\.compactLayout \? 23 : 32/);
 assert.match(forecast,/height: outlook\.compactLayout\s*\? Math\.max\(36,Math\.min\(178,outlook\.height-156\)\)/);
 assert.match(forecast,/Calendar\.build\(/);
 assert.match(forecast,/weatherService\.forecastReady/);
 assert.match(forecast,/DAILY FORECAST SNAPSHOTS \/\/ NOT PRECISE LUNAR EVENT UTC/);
 const m=forecastPolicy.build([
  {date:"2026-11-06",moonPhase:"waning crescent",moonIllumination:23,
   sunrise:"6:45 AM",sunset:"5:04 PM"},
  {date:"2026-11-07",moonPhase:"new moon",moonIllumination:3,
   sunrise:"6:46 AM",sunset:"5:03 PM"}
 ]);
 assert.equal(m.ready,true);
 assert.equal(m.rows.length,2);
 assert.equal(m.rows[0].illumination,23);
 assert.equal(m.rows[1].phase,"NEW");
 assert.equal(forecastPolicy.select(m,"2026-11-07").illumination,3);
 const bad=forecastPolicy.build([{date:"2026-11-06",moonPhase:"",
                                  moonIllumination:null,sunrise:"--",sunset:"--"}]);
 assert.equal(bad.ready,true);
 assert.equal(bad.rows[0].illumination,null);
 assert.equal(bad.rows[0].phase,"PHASE UNKNOWN");
});
