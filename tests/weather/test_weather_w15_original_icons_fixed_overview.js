"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=p=>fs.readFileSync("widgets/weather/"+p,"utf8");
const home=read("StationHome.qml");
const card=read("StationHomeMetricCard.qml");
const summary=read("StationWeatherTerminalSummary.qml");
const terminal=read("StationWeatherInstrumentTerminal.qml");
const old=read("StationWeatherCombinedPane.qml");

test("W15 keeps original SKY condition and WeatherCelestialGlyph from pre-W14",()=>{
 assert.match(old,/sky\.conditionState\.icon/);
 assert.match(old,/WeatherCelestialGlyph\s*\{/);
 assert.match(terminal,/terminal\.sky\.conditionState\.icon/);
 assert.match(terminal,/hour\.forecastState\.icon/);
 assert.match(terminal,/day\.dayState\.icon/);
 assert.match(terminal,/WeatherCelestialGlyph\s*\{/);
 assert.match(terminal,/terminal\.sky\.skyCycle\.moonPhase/);
 assert.doesNotMatch(terminal,/StationWeatherLineGlyph\s*\{/);
 assert.match(summary,/function glyph\(weatherCode, condition\)/);
 assert.match(summary,/terminal\.glyph\(sample\.weatherCode,sample\.condition\)/);
 assert.doesNotMatch(summary,/StationWeatherLineGlyph\s*\{/);
});

test("W15 timestamp stays top while the original icon, temperature, rain value and bar center together",()=>{
 assert.match(terminal,/id: forecastTime/);
 assert.match(terminal,/anchors\.top: parent\.top/);
 assert.match(terminal,/id: hourInstrumentRegion/);
 assert.match(terminal,/anchors\.top: forecastTime\.bottom/);
 assert.match(terminal,/id: hourInstrumentStack/);
 assert.match(terminal,/anchors\.centerIn: parent/);
 for(const id of ["hourGlyph","hourTemperature","hourChance","hourRain"])
   assert.match(terminal,new RegExp("id: "+id));
 assert.match(terminal,/instrumentRegion: hourInstrumentRegion/);
 assert.match(terminal,/readingStack: hourInstrumentStack/);
 assert.match(terminal,/inspectedHourIndex=index/);
 assert.match(terminal,/terminal\.fraction\(hour\.entry\.chanceRain\)/);
});

test("W15 removes weather OVERVIEW vertical pan without clipping or deleting its sources",()=>{
 assert.match(home,/subjectRoute === "weather\/overview"/);
 assert.match(home,/interactive: !home\.compactHistory && !home\.fixedWeatherOverview/);
 assert.match(home,/contentHeight: home\.fixedWeatherOverview \? height : Math\.max/);
 assert.match(home,/visible: scrollable && !home\.compactHistory\s+&& !home\.fixedWeatherOverview/);
 assert.match(home,/spacing: home\.fixedWeatherOverview \? 0/);
 assert.match(home,/weatherSnapshotRow/);
 assert.match(home,/weatherRelevantRow/);
 assert.match(home,/overviewPage==="alerts"/);
 assert.match(home,/overviewPage==="snapshot"/);
 assert.match(home,/overviewPage==="relevant"/);
 assert.match(home,/onOverviewSelectionRequested/);
 assert.match(summary,/objectName: "weather-w15-overview-header-selector"/);
 assert.match(summary,/modelData\.key!=="alerts" \|\|/);
 assert.match(summary,/overviewSelectionRequested/);
 assert.match(summary,/height: compact \? 158 : 164/);
});

test("W15 changes no shared card internals, meters or data collectors",()=>{
 assert.match(card,/property bool compact: false/);
 assert.match(card,/property real meterValue: 0/);
 assert.match(card,/height: 7/);
 assert.match(card,/font\.pixelSize: card\.compact \? 15 : 20/);
 assert.match(home,/StationHomeMetricCard\s*\{/);
 assert.match(summary,/objectName: "weather-w8-current-air-metrics"/);
 assert.match(summary,/objectName: "weather-w8-hourly-strip"/);
 assert.match(summary,/objectName: "weather-w8-daily-strip"/);
 assert.doesNotMatch(terminal,/FileView\s*\{|Process\s*\{|XMLHttpRequest|Qt\.openUrlExternally/);
});
