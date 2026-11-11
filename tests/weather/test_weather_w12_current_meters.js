"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const src=fs.readFileSync("widgets/weather/StationWeatherCombinedPane.qml","utf8");
const sky=fs.readFileSync("widgets/weather/StationSky.qml","utf8");

test("W12 daily expands at the expense of oversized hourly cards",()=>{
  assert.match(src,/dailyHeight: Math\.max\(56,Math\.min\(70,bandBudget\*0\.28\)\)/);
  assert.match(src,/currentHeight: Math\.max\(69,Math\.round\(\(bandBudget-dailyHeight\)\*0\.47\)\)/);
  assert.match(src,/hourlyHeight: Math\.max\(1,bandBudget-dailyHeight-currentHeight\)/);
  assert.match(src,/height: panel\.dailyHeight/);
  assert.match(src,/height: panel\.hourlyHeight/);
  assert.match(src,/id: statusFooter/);
});

test("W12 current glyph uses original current day/night classification",()=>{
  assert.match(src,/objectName: "weather-w12-current-condition-icon"/);
  assert.match(src,/font\.pixelSize: Math\.max\(50,conditionArt\.width\)/);
  assert.match(src,/sky\.currentCelestialMode/);
  assert.match(src,/WeatherCelestialGlyph\s*\{/);
  assert.match(src,/sky\.skyCycle\.solar/);
  assert.match(src,/sky\.skyCycle\.moonPhase/);
  assert.match(src,/sky\.conditionState\.icon/);
});

test("W12 four telemetry bars use original SKY normalized reading ratios",()=>{
  assert.match(src,/objectName: "weather-w12-temperature-meter"/);
  assert.match(src,/sky\.temperatureMeter/);
  assert.match(src,/sky\.aqiMeter/);
  assert.match(src,/sky\.humidityMeter/);
  assert.match(src,/sky\.windMeter/);
  assert.match(src,/meterRatio/);
  assert.match(src,/modelData\.key!=="pressure"/);
  assert.match(src,/height: visible \? 8 : 0/);
  assert.match(sky,/readonly property real temperatureMeter:/);
  assert.match(sky,/readonly property real aqiMeter:/);
  assert.match(sky,/readonly property real humidityMeter:/);
  assert.match(sky,/readonly property real windMeter:/);
});

test("W12 wind direction compass uses existing sixteen-direction policy",()=>{
  assert.match(src,/objectName: "weather-w12-wind-arrow"/);
  assert.match(src,/text: "↑"/);
  assert.match(src,/rotation: panel\.currentReady && panel\.sky/);
  assert.match(src,/panel\.sky\.windAngle\(/);
  assert.match(src,/panel\.sky\.weatherService\.windDirection/);
  assert.match(sky,/function windAngle\(direction\)/);
  assert.match(sky,/at \* 22\.5/);
  assert.doesNotMatch(src,/Process\s*\{|Timer\s*\{|FileView\s*\{|XMLHttpRequest|fetch\(/);
});

test("W12 centers compact daily labels but keeps all three weather icons and rain bars",()=>{
  assert.match(src,/model: Math\.min\(3,panel\.dailyRows\.length\)/);
  assert.match(src,/font\.pixelSize: 44/);
  assert.match(src,/horizontalAlignment: Text\.AlignHCenter/);
  assert.match(src,/anchors\.verticalCenter: parent\.verticalCenter/);
  assert.match(src,/WeatherCyclePolicy\.artworkFor\(/);
  assert.match(src,/panel\.chanceRatio\(dayCell\.entry\.chanceRain\)/);
  assert.match(src,/forecastReady && sky\.dailyForecast/);
});
