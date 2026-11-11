"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const read=p=>fs.readFileSync(p,"utf8");
const root="widgets/weather/";
const pane=read(root+"StationWeatherSubjectPane.qml");
const combined=read(root+"StationWeatherCombinedPane.qml");
const sky=read(root+"StationSky.qml");
const solar=read(root+"StationCosmosVisualInstruments.qml");
const policy={};
vm.runInNewContext(read(root+"StationWeatherSubjectPanelPolicy.js")
  .replace(/^\.pragma library\s*/m,""),policy);

test("W10 has exactly one StationSky source and only two internal screens",()=>{
 assert.equal((pane.match(/StationSky\s*\{/g)||[]).length,1);
 assert.match(pane,/readonly property var runtimeRows: originalSky\.runtimeRows/);
 assert.match(pane,/weatherService: weatherPane\.weatherService/);
 assert.match(pane,/StationWeatherInstrumentTerminal\s*\{/);
 assert.match(pane,/sky: originalSky/);
 assert.match(pane,/property string activeInstrument: "weather"/);
 assert.match(pane,/weatherFocus: skyHost\.combined/);
 for(const value of ['label:"WEATHER // CURRENT + FORECAST",focus:"weather"',
                     'label:"TWILIGHT // SOLAR",focus:"twilight"'])
   assert.ok(pane.includes(value));
 assert.doesNotMatch(pane,/label:"NOW \+ AIR"|label:"HOURLY"|label:"DAILY"/);
});

test("W10 current + air, all six hour samples, three days and inspector fit one non-scrolling panel",()=>{
 for(const name of [
   '"weather-w10-current-air-band"',
   '"weather-w10-hourly-band"',
   '"weather-w10-daily-band"',
   '"weather-w10-six-hour-icons"'
 ])assert.ok(combined.includes(name),name);
 assert.match(combined,/model: Math\.min\(6,panel\.hourlyRows\.length\)/);
 assert.match(combined,/model: Math\.min\(3,panel\.dailyRows\.length\)/);
 assert.match(combined,/sky\.conditionState\.icon/);
 assert.match(combined,/panel\.sky\.windValue/);
 assert.match(combined,/Boolean\(sky && sky\.aqiReady\)/);
 assert.match(combined,/WeatherCyclePolicy\.forecast\(/);
 assert.match(combined,/WeatherCyclePolicy\.atLocal\(/);
 assert.match(combined,/WeatherCyclePolicy\.artworkFor\(/);
 assert.match(combined,/WeatherCelestialGlyph\s*\{/);
 assert.match(combined,/panel\.sky\.inspectedHourIndex=index/);
 assert.match(combined,/panel\.sky\.inspectedHourMetrics/);
 assert.match(combined,/forecastReady && sky\.hourlyForecast/);
 assert.match(combined,/forecastReady && sky\.dailyForecast/);
 assert.match(pane,/clip: true/);
 assert.match(sky,/interactive: sky\.weatherFocus === ""/);
 assert.doesNotMatch(combined,/Process\s*\{|FileView\s*\{|XMLHttpRequest|Timer\s*\{/);
});

test("W10 TWILIGHT leads at the top and reuses existing calibrated solar graph",()=>{
 assert.match(pane,/StationCosmosVisualInstruments\s*\{/);
 assert.match(pane,/showMoon: false/);
 assert.match(pane,/showSun: true/);
 assert.match(pane,/compactMode: true/);
 assert.match(pane,/astronomySummary: originalSky\.astronomySummary/);
 assert.match(pane,/twilightSummary: originalSky\.twilightSummary/);
 assert.match(pane,/currentSolarPosition: originalSky\.currentSolarPosition/);
 assert.match(pane,/solarDate: originalSky\.astronomySummary\.date/);
 assert.match(pane,/solarCivilOffsetMinutes: originalSky\.moonCivilOffsetMinutes/);
 assert.match(pane,/latitude: weatherPane\.weatherService/);
 assert.match(pane,/longitude: weatherPane\.weatherService/);
 assert.match(pane,/id: twilightTextArea/);
 assert.match(pane,/anchors\.top: twilightTextArea\.bottom/);
 assert.match(pane,/\/\/ TWILIGHT stays at the TOP/);
 assert.match(solar,/SUN \/\/ 24H ALTITUDE MODEL/);
 assert.match(solar,/VisualPolicy\.solarArc\(/);
 assert.match(solar,/id: solarCanvas/);
 assert.match(solar,/solarData\.rows/);
 assert.doesNotMatch(pane,/StationMoon\s*\{|StationSky\s*\{[\s\S]*StationSky\s*\{/);
});

test("W10 preserves existing WEATHER OVERVIEW and deep links",()=>{
 const routes=["weather/conditions/current","weather/forecasts/hourly",
  "weather/forecasts/daily","weather/conditions/atmosphere"];
 for(const route of routes)assert.equal(policy.kindForRoute(route),"sky");
 assert.equal(policy.kindForRoute("weather/overview"),"home");
 assert.equal(policy.kindForRoute("weather/services/health"),"services");
 assert.match(sky,/return SubjectPanelPolicy\.visibleFor\("sky",subjectRoute,section\)/);
 assert.match(sky,/CosmosPanelPolicy\.visibleFor\("sky",subjectRoute,section\)/);
});
