"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=path=>fs.readFileSync(path,"utf8");
const overview=read("widgets/weather/StationWeatherOverviewCompactInstrument.qml");
const weather=read("widgets/weather/StationWeatherInstrumentTerminal.qml");
const home=read("widgets/weather/StationHome.qml");
const cards=read("widgets/weather/StationHomeMetricCard.qml");
const nativeOverview=read("tests/weather/fixtures/W15FixedWeatherOverviewNative.qml");
const nativeWeather=read("tests/weather/fixtures/W9FixedWeatherTerminalNative.qml");

function assertOrder(source,temperature,meter,chance,label) {
 const first=source.indexOf("id: "+temperature);
 const second=source.indexOf("id: "+meter);
 const third=source.indexOf("id: "+chance);
 assert.ok(first>=0 && second>first && third>second,label+" temperature/bar/% order");
}
test("W19 forecast bars connect temperature with matching percentage on both screens",()=>{
 assertOrder(overview,"hourTemperature","hourMeter","hourChance","overview hourly");
 assertOrder(weather,"hourTemperature","hourRain","hourChance","weather hourly");
 assertOrder(overview,"dayTemperature","dayRainMeter","dayChance","overview daily");
 assertOrder(weather,"dayTemperature","dayRainMeter","dayChance","weather daily");
 assert.match(weather,/height: 6\s+anchors.horizontalCenter: parent.horizontalCenter\s+color: Colors.black/);
 assert.match(overview,/height: hour.height>65 \? 6 : 5/);
 assert.match(overview,/height: dayStrip.height>36 \? 6 : 5/);
 assert.match(weather,/terminal.fraction\(hour.entry.chanceRain\)/);
 assert.match(weather,/terminal.fraction\(day.entry.chanceRain\)/);
 assert.match(overview,/panel.ratio\(hour.entry.chanceRain,100\)/);
 assert.match(overview,/panel.ratio\(day.entry.chanceRain,100\)/);
 assert.match(nativeOverview,/HOUR_\"\+i/);
 assert.match(nativeOverview,/DAY_\"\+i/);
 assert.match(nativeWeather,/DAILY_RAIN_BAR_MISSING/);
});
test("W19 current-condition meters are thicker and optically raised",()=>{
 assert.match(weather,/id: metricValueRow/);
 assert.match(weather,/y: Math.min\(metric.height-height-1,/);
 assert.match(weather,/height: visible \? \(metric.height<40 \? 6 : 7\) : 0/);
 assert.match(overview,/id: metricReadoutRow/);
 assert.match(overview,/y: metric.height < 35 \? metric.height - height/);
 assert.match(overview,/height: visible \? \(metric.height < 35 \? 4 : 6\) : 0/);
 assert.match(nativeOverview,/TOP_METERS_NOT_CENTERED/);
});
test("W19 emphasizes NOW without changing original glyph family or lower cards",()=>{
 assert.match(weather,/width: Math.max\(80,Math.min\(158,currentPanel.height\+4,/);
 assert.match(overview,/width: Math.min\(112,47 \+ panel.expansion \* 0.37,/);
 for(const f of [overview,weather]) {
   assert.match(f,/WeatherCelestialGlyph\s*\{/);
   assert.doesNotMatch(f,/Process\s*\{|FileView\s*\{|XMLHttpRequest|fetch\s*\(/);
 }
 assert.match(overview,/["']⚡︎["']/);
 assert.match(home,/readonly property real overviewCardRowHeight:/);
 assert.match(cards,/height: 7/);
 assert.match(cards,/property real meterValue: 0/);
});
