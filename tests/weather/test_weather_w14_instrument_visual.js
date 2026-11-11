"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=path=>fs.readFileSync("widgets/weather/"+path,"utf8");
const terminal=read("StationWeatherInstrumentTerminal.qml");
const glyph=read("StationWeatherLineGlyph.qml");
const overview=read("StationWeatherTerminalSummary.qml");
const host=read("StationWeatherSubjectPane.qml");
const sky=read("StationSky.qml");

test("W14 WEATHER uses three differentiated instruments rather than the W13 tile grid",()=>{
 assert.match(host,/StationWeatherInstrumentTerminal\s*\{/);
 assert.match(terminal,/objectName: "weather-w14-current-focus"/);
 assert.match(terminal,/objectName: "weather-w14-connected-six-hour-timeline"/);
 assert.match(terminal,/objectName: "weather-w14-three-day-outlook"/);
 assert.match(terminal,/color: Colors.orange/);
 assert.match(terminal,/color: Colors.magenta/);
 assert.match(terminal,/color: Colors.yellow/);
 assert.match(terminal,/color: Colors.cyan/);
 assert.match(terminal,/font.pixelSize: 37/);
 assert.match(terminal,/font.pixelSize: 16/);
 assert.match(terminal,/font.pixelSize: 11/);
 assert.match(terminal,/id: dailyRepeater/);
 assert.match(terminal,/id: hourlyRepeater/);
 assert.match(terminal,/Math.min\(6,terminal.hourlyRows.length\)/);
 assert.match(terminal,/Math.min\(3,terminal.dailyRows.length\)/);
 assert.equal((terminal.match(/delegate: Rectangle\s*\{/g)||[]).length,0,
   "no generic boxed cards for every forecast record");
});

test("W14 communicates real date, hourly probability and observed versus forecast",()=>{
 assert.match(terminal,/dateLabel\(hour.entry.date\)/);
 assert.match(terminal,/hour.entry.timeLabel/);
 assert.match(terminal,/RAIN CHANCE \/\/ EACH LISTED PERIOD/);
 assert.match(terminal,/terminal.rainChance\(hour.entry.chanceRain\)/);
 assert.match(terminal,/THREE-DAY OUTLOOK \/\/ PEAK RAIN CHANCE/);
 assert.match(terminal,/RAIN CHANCE/);
 assert.match(terminal,/CURRENT OBSERVATION \/\/ LISTED TIMES & DAYS ARE FORECASTS/);
 assert.match(terminal,/inspectedHourIndex=index/);
 assert.match(terminal,/inspectedHourMetrics/);
 assert.match(terminal,/forecastReady && sky.hourlyForecast/);
 assert.match(terminal,/forecastReady && sky.dailyForecast/);
 assert.match(overview,/RAIN CHANCE FOR EACH LISTED PERIOD/);
 assert.match(overview,/RAIN CHANCE/);
});

test("W14 icon system is single-ink line drawing, not emoji, filled or 3D decoration",()=>{
 assert.match(glyph,/Canvas\s*\{/);
 assert.match(glyph,/strokeSun/);
 assert.match(glyph,/strokeMoon/);
 assert.match(glyph,/strokeCloud/);
 assert.match(glyph,/strokeRain/);
 assert.match(glyph,/c.stroke\(\)/);
 assert.doesNotMatch(glyph,/c.fill\(\)/);
 assert.doesNotMatch(glyph,/LinearGradient|Image\s*\{|AnimatedImage|emoji\s*:\s*true/);
 assert.match(terminal,/StationWeatherLineGlyph\s*\{/);
 assert.match(overview,/StationWeatherLineGlyph\s*\{/);
 assert.doesNotMatch(overview,/function glyph\(/);
 assert.doesNotMatch(terminal,/WeatherCelestialGlyph\s*\{/);
});

test("W14 restores padded menu header without disturbing WEATHER/TWILIGHT selections",()=>{
 assert.match(host,/id: weatherModeHeader/);
 assert.match(host,/objectName: "weather-w14-padded-mode-header"/);
 assert.match(host,/anchors.top: weatherModeHeader.bottom/);
 assert.match(host,/anchors.topMargin: skyHost.combined \? 3 : 0/);
 assert.match(host,/anchors.leftMargin: skyHost.combined \? 8 : 0/);
 assert.match(host,/StationWeatherTwilightGrid\s*\{/);
 assert.match(host,/StationCosmosVisualInstruments\s*\{/);
 assert.match(host,/readonly property var runtimeRows: originalSky.runtimeRows/);
 assert.equal((host.match(/StationSky\s*\{/g)||[]).length,1);
});

test("W14 decorative view introduces no live fetcher or persistence",()=>{
 for(const file of [terminal,glyph,overview]) {
    assert.doesNotMatch(file,/Process\s*\{|FileView\s*\{|XMLHttpRequest|fetch\s*\(|Timer\s*\{|Qt\.openUrlExternally/);
 }
 assert.match(terminal,/WeatherCyclePolicy.forecast\(/);
 assert.match(terminal,/WeatherCyclePolicy.atLocal\(/);
 assert.match(terminal,/sky.iconState\(/);
 assert.match(terminal,/sky.iconColor\(/);
 assert.match(terminal,/sky.windAngle\(/);
 assert.match(sky,/readonly property bool weatherReady/);
});
