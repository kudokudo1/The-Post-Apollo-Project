"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=p=>fs.readFileSync("widgets/weather/"+p,"utf8");
const combined=read("StationWeatherCombinedPane.qml");
const host=read("StationWeatherSubjectPane.qml");
const grid=read("StationWeatherTwilightGrid.qml");
const solar=read("StationCosmosVisualInstruments.qml");

test("W12 balances current/hourly and a readable compact daily strip",()=>{
  for(const word of ["bandBudget","dailyHeight","currentHeight","hourlyHeight"])
    assert.match(combined,new RegExp("readonly property real "+word));
  assert.match(combined,/Math\.min\(70,bandBudget\*0\.28\)/);
  assert.match(combined,/height: panel\.currentHeight/);
  assert.match(combined,/height: panel\.hourlyHeight/);
  assert.match(combined,/height: panel\.dailyHeight/);
  assert.match(combined,/font\.pixelSize: 29/);
  assert.match(combined,/font\.pixelSize: Math\.max\(50,conditionArt\.width\)/);
  assert.match(combined,/font\.pixelSize: Math\.max\(34,Math\.min\(56,parent\.height-2\)\)/);
  assert.match(combined,/id: hourlyRainMeter/);
  assert.match(combined,/height: 8\s+color: Colors\.black/);
  assert.match(combined,/font\.pixelSize: 44/);
  assert.match(combined,/WeatherCelestialGlyph\s*\{/);
  assert.match(combined,/panel\.sky\.inspectedHourIndex=index/);
  assert.match(combined,/forecastReady && sky\.hourlyForecast/);
  assert.match(combined,/forecastReady && sky\.dailyForecast/);
});

test("W11 real twilight values form full-width upper grid",()=>{
  assert.match(host,/StationWeatherTwilightGrid\s*\{/);
  assert.match(host,/anchors\.fill: parent\s+visible: parent\.visible\s+sky: originalSky/);
  assert.match(host,/height: visible \? Math\.max\(104,/);
  assert.match(grid,/anchors\.fill: parent/);
  for(const field of ["astronomicalDawn","nauticalDawn","civilDawn","sunrise",
        "solarNoon","sunset","civilDusk","nauticalDusk","astronomicalDusk",
        "blueMorningStart","goldenMorningStart","goldenEveningStart","blueEveningStart",
        "altitudeDegrees","azimuthDegrees"])
    assert.ok(grid.includes(field),"missing real twilight value "+field);
  assert.doesNotMatch(grid,/Process\s*\{|Timer\s*\{|XMLHttpRequest|FileView\s*\{/);
});

test("W11 solar chart fills lower bay but prior COSMOS usage stays default",()=>{
  assert.match(solar,/property bool fullBleedSolar: false/);
  assert.match(solar,/visual\.fullBleedSolar/);
  assert.match(host,/fullBleedSolar: true/);
  assert.match(host,/width: solarGraphArea\.width/);
  assert.match(host,/height: solarGraphArea\.height/);
  assert.match(host,/anchors\.top: twilightTextArea\.bottom/);
  assert.match(host,/scale: 1/);
  assert.match(host,/showMoon: false/);
  assert.match(host,/showSun: true/);
  assert.match(host,/solarDate: originalSky\.astronomySummary\.date/);
  assert.match(host,/solarCivilOffsetMinutes: originalSky\.moonCivilOffsetMinutes/);
  assert.match(host,/providerLocalMinute: originalSky\.providerLocalMinute/);
  assert.match(solar,/VisualPolicy\.solarArc\(/);
  assert.match(solar,/id: solarCanvas/);
});
