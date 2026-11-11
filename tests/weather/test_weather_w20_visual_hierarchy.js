"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const home=fs.readFileSync("widgets/weather/StationHome.qml","utf8");
const overview=fs.readFileSync("widgets/weather/StationWeatherOverviewCompactInstrument.qml","utf8");
const weather=fs.readFileSync("widgets/weather/StationWeatherInstrumentTerminal.qml","utf8");
const cards=fs.readFileSync("widgets/weather/StationHomeMetricCard.qml","utf8");
const nativeOverview=fs.readFileSync("tests/weather/fixtures/W15FixedWeatherOverviewNative.qml","utf8");
const nativeWeather=fs.readFileSync("tests/weather/fixtures/W9FixedWeatherTerminalNative.qml","utf8");
function allocation(height) {
  const row=Math.max(55,Math.min(68,Math.floor(height*0.18),
                   Math.floor(Math.max(0,height-164)/2)));
  const instrument=height-2*row;
  const expansion=Math.max(0,instrument-164);
  const pinned=Math.min(160,expansion);
  return {row,instrument,now:52+pinned*.50,
          hour:45+expansion-pinned*.67,day:24+pinned*.17};
}
test("W20 gives the six-hour forecast new vertical space without shrinking three-day or NOW",()=>{
 assert.match(home,/overviewCardRowHeight: Math.max\(55, Math.min\(/);
 assert.match(home,/68, Math.floor\(homeScroll.height \* 0.18\)/);
 assert.match(overview,/anchoredExpansion: Math.min\(160, expansion\)/);
 assert.match(overview,/height: 52 \+ panel.anchoredExpansion \* 0.50/);
 assert.match(overview,/height: 45 \+ panel.expansion - panel.anchoredExpansion \* 0.67/);
 assert.match(overview,/height: 24 \+ panel.anchoredExpansion \* 0.17/);
 for(const h of [275,300,400,500,650]) {
   const a=allocation(h);
   assert.equal(a.instrument+2*a.row,h);
   assert.ok(a.row>=55 && a.row<=68);
   assert.ok(a.now>=52 && a.hour>=45 && a.day>=24);
   assert.ok(Math.abs(a.now+a.hour+a.day-(121+Math.max(0,a.instrument-164)))<.001);
 }
 const tall=allocation(500);
 assert.equal(tall.row,68);
 assert.ok(tall.hour>=130);
 assert.ok(Math.abs(tall.now-132)<.01);
 assert.ok(Math.abs(tall.day-51.2)<.01);
 assert.match(nativeOverview,/W20_SIX_PERIOD_FORECAST_TOO_SMALL/);
 assert.match(nativeOverview,/W20_LOWER_CARDS_NOT_REDUCED/);
 assert.match(nativeOverview,/W20_THREE_DAY_CHANGED/);
});
test("W20 makes original full-WEATHER icon a giant focus while preserving all measurements",()=>{
 assert.match(weather,/currentHeight: Math.max\(1,Math.min\(/);
 assert.match(weather,/Math.round\(budget\*0.57\)/);
 assert.match(weather,/hourlyHeight: Math.max\(84,Math.round\(budget\*0.33\)\)/);
 assert.match(weather,/largeCurrent.width\*0.72/);
 assert.match(weather,/Math.min\(180,currentPanel.height\+8/);
 assert.match(weather,/font.pixelSize: 43/);
 assert.match(weather,/mainWeatherIcon.width \* 1.13/);
 assert.match(weather,/terminal.sky.conditionState.icon/);
 assert.match(weather,/WeatherCelestialGlyph\s*\{/);
 assert.match(weather,/scale: 1.24/);
 assert.match(weather,/model: Math.min\(6,terminal.hourlyRows.length\)/);
 assert.match(weather,/model: Math.min\(3,terminal.dailyRows.length\)/);
 assert.match(nativeWeather,/W20_HERO_ICON_NOT_DRAMATIC/);
 assert.match(nativeWeather,/W20_HERO_OVERLAPS_TEMPERATURE/);
 assert.match(nativeWeather,/window.height=380/);
 assert.doesNotMatch(weather,/Process\s*\{|Timer\s*\{|FileView\s*\{|XMLHttpRequest|fetch\s*\(/);
});
test("W20 leaves the lower card module, colors, and forecast-meters intact",()=>{
 assert.match(cards,/height: 7/);
 assert.match(cards,/property real meterValue: 0/);
 assert.match(overview,/panel.ratio\(hour.entry.chanceRain,100\)/);
 assert.match(overview,/panel.ratio\(day.entry.chanceRain,100\)/);
 assert.match(weather,/terminal.fraction\(hour.entry.chanceRain\)/);
 assert.match(weather,/terminal.fraction\(day.entry.chanceRain\)/);
 assert.match(overview,/WeatherDockPolicy.classify/);
 assert.match(overview,/["']⚡︎["']/);
});
