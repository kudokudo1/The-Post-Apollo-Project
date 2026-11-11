"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=p=>fs.readFileSync("widgets/weather/"+p,"utf8");
const summary=read("StationWeatherTerminalSummary.qml");
const compact=read("StationWeatherOverviewCompactInstrument.qml");
const full=read("StationWeatherInstrumentTerminal.qml");
const home=read("StationHome.qml");
const cards=read("StationHomeMetricCard.qml");

test("W17 compact OVERVIEW mirrors full WEATHER three-band instrument",()=>{
 assert.match(summary,/StationWeatherOverviewCompactInstrument\s*\{/);
 assert.match(summary,/visible: terminal\.compact/);
 assert.match(summary,/visible: !terminal\.compact/);
 for(const name of ["current-instrument","six-hour-timeline","three-day-strip"])
   assert.ok(compact.includes("weather-w17-"+name));
 assert.match(compact,/model: Math\.min\(6,panel\.hourlySamples\.length\)/);
 assert.match(compact,/model: Math\.min\(3,panel\.dailySamples\.length\)/);
 assert.match(compact,/model: panel\.telemetry/);
 assert.match(compact,/height: 164/);
 assert.match(home,/height: visible \? home\.overviewInstrumentHeight : 0/);
 assert.match(home,/runtimeNowMs: home\.runtimeNowMs/);
 assert.match(full,/objectName: "weather-w14-current-focus"/);
});

test("W17 reuses exact StationSky icon classification and celestial artwork",()=>{
 assert.match(compact,/WeatherDockPolicy\.classify\(/);
 assert.match(compact,/WeatherCyclePolicy\.atObservation\(/);
 assert.match(compact,/WeatherCyclePolicy\.forecast\(/);
 assert.match(compact,/WeatherCyclePolicy\.atLocal\(/);
 assert.match(compact,/WeatherCyclePolicy\.artworkFor\(/);
 assert.match(compact,/WeatherCelestialGlyph\s*\{/);
 assert.match(compact,/WeatherCyclePolicy\.nightKind\(/);
 assert.match(compact,/THUNDERSTORM/);
 assert.match(compact,/["']⚡︎["']/);
 assert.doesNotMatch(compact,/StationWeatherLineGlyph\s*\{|Canvas\s*\{/);
});

test("W17 carries same visible icon and meter relationships",()=>{
 assert.match(compact,/objectName: "weather-w17-original-main-glyph"/);
 assert.match(compact,/objectName: "weather-w17-original-hourly-glyph"/);
 assert.match(compact,/id: metricsRepeater/);
 assert.match(compact,/id: hourRepeater/);
 assert.match(compact,/id: dayRepeater/);
 assert.match(compact,/id: telemetryMeter/);
 assert.match(compact,/id: hourMeter/);
 assert.match(compact,/objectName: "weather-w17-hourly-rain-meter"/);
 assert.match(compact,/modelData\.key!=="pressure"/);
 assert.match(compact,/text: "↑"/);
 assert.match(compact,/chanceRain/);
 assert.match(compact,/PEAK RAIN CHANCE/);
});

test("W17 slightly shrinks the lower cards but keeps their original data and no normal scrolling",()=>{
 assert.match(home,/weatherOverviewSummary\.height/);
 assert.match(home,/weatherSnapshotRow\.height/);
 assert.match(home,/compact: home\.fixedWeatherOverview/);
 assert.match(home,/overviewDense: home\.fixedWeatherOverview/);
 assert.match(home,/id: weatherSnapshotRow/);
 assert.match(home,/id: weatherRelevantRow/);
 assert.match(home,/!home\.overviewRequiresScroll/);
 assert.match(cards,/property real meterValue: 0/);
 assert.match(cards,/height: 7/);
 assert.match(cards,/onClicked: card\.pinRequested\(\)/);
 assert.doesNotMatch(compact,/Process\s*\{|FileView\s*\{|XMLHttpRequest|Timer\s*\{|fetch\s*\(/);
});
