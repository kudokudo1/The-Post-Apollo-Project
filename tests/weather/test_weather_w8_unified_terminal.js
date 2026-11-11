"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const read=p=>fs.readFileSync(p,"utf8");
const nav={};
const policy={};
vm.runInNewContext(read("widgets/weather/StationWorkspaceNavigationPolicy.js")
  .replace(/^\.pragma library\s*/m,""),nav);
vm.runInNewContext(read("widgets/weather/StationWeatherSubjectPanelPolicy.js")
  .replace(/^\.pragma library\s*/m,""),policy);
const summary=read("widgets/weather/StationWeatherTerminalSummary.qml");
const sky=read("widgets/weather/StationSky.qml");
const home=read("widgets/weather/StationHome.qml");
const surface=read("widgets/weather/StationWeatherSubjectPane.qml");

test("W8 has one combined WEATHER button and retains original deep-link routes",()=>{
 const modes=nav.GROUPS.weather;
 assert.deepEqual(modes.map(x=>x.label),
   ["OVERVIEW","WEATHER","HAZARDS","HISTORY","SERVICES"]);
 assert.equal(modes[1].key,"conditions");
 assert.equal(modes[1].path,"weather/conditions/current");
 assert.equal(nav.selectedGroup("weather/forecasts/hourly"),"conditions");
 assert.equal(nav.selectedGroup("weather/forecasts/daily"),"conditions");
 for(const p of ["weather/conditions/current","weather/forecasts/hourly",
                 "weather/forecasts/daily","weather/conditions/atmosphere",
                 "weather/conditions/air","weather/forecasts/air"])
   assert.ok(policy.kindForRoute(p),"retired deep link "+p);
 for(const section of ["header","current","atmosphere","hourly","daily","twilight"])
   assert.equal(policy.visibleFor("sky","weather/conditions/current",section),true,section);
 assert.equal(policy.visibleFor("sky","weather/conditions/current","astronomy"),false);
 assert.equal(policy.visibleFor("sky","weather/conditions/current","moon"),false);
 for(const actor of ["river","lightning","marine","coastal","seismic","astronomy"])
   assert.equal(policy.needsSource("weather/conditions/current",actor),false);
});

test("W8 reuses original source owner and both original forecast instruments",()=>{
 assert.equal((surface.match(/StationSky\s*\{/g)||[]).length,1);
 assert.match(surface,/weatherService: weatherPane\.weatherService/);
 assert.match(sky,/visible: sky\.sectionVisible\("current"\)/);
 assert.match(sky,/visible: sky\.sectionVisible\("atmosphere"\)/);
 assert.match(sky,/visible: sky\.sectionVisible\("hourly"\)/);
 assert.match(sky,/visible: sky\.sectionVisible\("daily"\)/);
 assert.match(sky,/visible: sky\.sectionVisible\("twilight"\)/);
 assert.match(sky,/StationWeatherTerminalSummary\s*\{/);
 assert.match(sky,/objectName: "weather-w8-full-terminal-summary"/);
 assert.match(sky,/visible: sky\.subjectRoute === "weather\/conditions\/current"/);
 assert.match(sky,/weatherService: sky\.weatherService/);
});

test("W8 overview starts with the same compact weather terminal, keeps alert/relevance",()=>{
 assert.match(home,/StationWeatherTerminalSummary\s*\{/);
 assert.match(home,/objectName: "weather-w8-overview-terminal-summary"/);
 assert.match(home,/visible: home\.subjectRoute === "weather\/overview"/);
 assert.match(home,/compact: true/);
 assert.match(home,/weatherService: home\.weatherService/);
 assert.ok(home.indexOf('objectName: "weather-w8-overview-terminal-summary"')
   <home.indexOf('title: "OFFICIAL ALERT \/\/ NWS"'),
   "combined weather instrument must lead overview");
 assert.equal(policy.kindForRoute("weather/overview"),"home");
 for(const section of ["header","alerts","snapshot","relevant"])
   assert.equal(policy.visibleFor("home","weather/overview",section),true);
});

test("W8 instrument uses real source fields and does not create refreshers",()=>{
 for(const name of ["conditionsReady","forecastReady","airReady","hourlySamples",
   "dailySamples","tempF","humidity","windMph","aqi","pm25","pressureHpa",
   "hourlyForecast","dailyForecast","chanceRain"])
   assert.ok(summary.includes(name),"missing actual source field "+name);
 assert.match(summary,/objectName: "weather-w8-current-air-metrics"/);
 assert.match(summary,/objectName: "weather-w8-hourly-strip"/);
 assert.match(summary,/objectName: "weather-w8-daily-strip"/);
 assert.match(summary,/height: compact \? 158 : 164/);
 assert.match(summary,/clip: true/);
 assert.doesNotMatch(summary,/WeatherServices\.|Process\s*\{|FileView\s*\{|XMLHttpRequest|Timer\s*\{|fetch\(/);
});
