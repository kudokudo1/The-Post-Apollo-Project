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

test("W16 supersedes W15 header split with one fixed OVERVIEW",()=>{
 assert.match(home,/subjectRoute === "weather\/overview"/);
 assert.match(home,/readonly property bool overviewRequiresScroll:/);
 assert.match(home,/fixedWeatherOverview && officialAlertSummary\.available/);
 assert.match(home,/interactive: !home\.compactHistory/);
 assert.match(home,/!home\.overviewRequiresScroll/);
 assert.match(home,/spacing: home\.fixedWeatherOverview \? 0/);
 assert.match(home,/id: weatherSnapshotRow/);
 assert.match(home,/id: weatherRelevantRow/);
 assert.match(home,/visible: home\.sectionVisible\("snapshot"\)/);
 assert.match(home,/visible: home\.sectionVisible\("relevant"\)/);
 assert.match(home,/overviewDense: home\.fixedWeatherOverview/);
 assert.match(summary,/height: 164/);
 assert.doesNotMatch(home,/overviewPage===|onOverviewSelectionRequested/);
 assert.doesNotMatch(summary,/overviewHeaderPages|overviewSelectionRequested/);
});


test("W15 changes no shared card internals, meters or data collectors",()=>{
 assert.match(card,/property bool compact: false/);
 assert.match(card,/property real meterValue: 0/);
 assert.match(card,/height: 7/);
 assert.match(card,/font\.pixelSize: card\.overviewDense \? \(card.height<50 \? 9 : 13/);
 assert.match(home,/StationHomeMetricCard\s*\{/);
 assert.match(summary,/objectName: "weather-w8-current-air-metrics"/);
 assert.match(summary,/objectName: "weather-w8-hourly-strip"/);
 assert.match(summary,/objectName: "weather-w8-daily-strip"/);
 assert.doesNotMatch(terminal,/FileView\s*\{|Process\s*\{|XMLHttpRequest|Qt\.openUrlExternally/);
});
